#!/usr/bin/env python3
"""Runtime control daemon for the cyber fault-injection tooling on Kali.

See docs/cyber-vs-physical-fault-injection-design.md §7, which calls for
"some new control surface on Kali the dashboard can reach to start/stop/
configure the relay/injection scripts" - this is that surface. Listens on
a-grfics-admin (the same out-of-band bridge network every container is
already on, for health checks and now this - not one of the simulated
ICS/DMZ networks Suricata watches), so the simulation container's
dashboard (simulation/web_visualization/data/index.php) can reach it by
container name ("kali") the same way a human running `docker exec` into
Kali to edit the C2 state file currently would. This doesn't open any new
path across the simulated network boundary, and this process never talks
to the PLC itself - it only starts/stops the already-validated
modbus_relay.py subprocess and writes to the already-validated C2
pending-command file, so the actual attack mechanisms are exactly what's
already been validated end-to-end (see §4.1-4.4).

Protocol: one JSON object per line, newline-terminated (matches
simulation's own control socket and the beacon/C2 protocol already used
elsewhere in this project).

  {"request": "read"}
    -> {"relay": {"sensor": str|null, "mode": int, "severity": float},
        "stuck_valve": {"enabled": bool, "valve": str|null,
                         "percent": float, "pending": bool}}
       "pending" is true while a queued stuck-valve command still sits in
       the C2 state file, i.e. the beacon hasn't checked in since it was
       queued yet.

  {"request": "configure_relay", "sensor": "<key>", "mode": 0|1|3|4, "severity": <float>}
    -> starts/reconfigures attacker/cyber_injects/modbus_relay.py against
       the real PLC's input registers for the given sensor (§4.1-4.3).
       mode 0 (none) or omitting "sensor" stops the relay entirely -
       nothing listens or intercepts until a real mode is requested.
       "severity" is already in the relay's own raw-register units (an
       amplitude out of 0-65535 for noise, a 0-1 duty fraction for
       dropout) - the dashboard converts from %FS before sending, since
       every sensor's register already scales its engineering value
       linearly onto 0-65535 (confirmed against
       simulation/simulation/remote_io/modbus/*.py), so a %FS fraction is
       the same fraction of raw register range regardless of sensor.
    -> {"ok": true, "relay": {...}}

  {"request": "set_stuck_valve", "enabled": true, "valve": "<key>", "percent": 0-100}
    -> queues a two-step command list for the compromised-HMI beacon
       (scadalts/cyber_injects/beacon_client.py) to execute on its next
       check-in: write the chosen valve's manual setpoint register, then
       set the manual_mode coil - the same OpenPLC "manual mode"
       mechanism setpoint_inject.py already uses directly, just delivered
       through the beacon/C2 channel for the compromised-HMI model
       (§4.4). manual_mode is a single global coil, so the other three
       valves will snap to whatever's already in *their* manual setpoint
       registers (their %QW defaults, or whatever a previous session left
       there) - a real property of the underlying ladder logic, not
       something this control plane tries to paper over.
  {"request": "set_stuck_valve", "enabled": false}
    -> queues just the manual_mode-off coil write; doesn't touch any
       setpoint register.
    -> {"ok": true, "stuck_valve": {...}}

State lives in memory only, reset to "everything off" on every daemon
(re)start - this process has no other reader/writer to coordinate with
(unlike the noise-floor state file, which the scheduler and the dashboard
both read/write), and treating a restart as a clean slate is safer than
silently re-arming a relay or beacon command nobody asked for again.
"""
import asyncio
import json
import os
import signal
import subprocess

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 5600

RELAY_SCRIPT = "/opt/cyber_injects/modbus_relay.py"
RELAY_LOG = "/var/log/cyber-injects-relay.out"
C2_PENDING_FILE = "/tmp/c2_pending_command.json"

PLC_HOST = "192.168.95.2"
PLC_PORT = 502
RELAY_LISTEN_PORT = 5502

# address/count of the PLC input registers (%IW, see plc/st_files/326339.st)
# backing each sensor's read-path value - the targets available to the
# relay-based cyber injects (freeze/noise/dropout, §4.1-4.3).
SENSOR_REGISTERS = {
    "tank_pressure": (108, 1),
    "tank_level":    (109, 1),
    "f1_flow":       (101, 1),
    "f2_flow":       (103, 1),
    "purge_flow":    (105, 1),
    "product_flow":  (107, 1),
    "analyzer":      (110, 3),
}

# manual setpoint holding register (%QW) per valve, and the manual_mode
# coil - the same registers setpoint_inject.py already uses directly (§4.4).
VALVE_MANUAL_SP = {"f1": 10, "f2": 11, "purge": 12, "product": 13}
MANUAL_MODE_COIL = 0

FAULT_MODE_NONE = 0

state = {
    "relay": {"sensor": None, "mode": FAULT_MODE_NONE, "severity": 0.0},
    "stuck_valve": {"enabled": False, "valve": None, "percent": 0.0},
}

relay_process = None
# Serializes configure_relay() calls, which now run on a thread-pool
# executor (see handle_client) rather than directly on the event loop -
# without this, two near-simultaneous reconfigure requests could interleave
# their stop_relay()/start_relay() calls and orphan a subprocess.
relay_lock = asyncio.Lock()


def stop_relay():
    # Synchronous and blocking (subprocess.wait) - callers in the asyncio
    # handler run this via run_in_executor so a slow-to-exit relay process
    # doesn't stall the event loop (and every other in-flight request) for
    # up to 3s.
    global relay_process
    if relay_process is not None and relay_process.poll() is None:
        relay_process.send_signal(signal.SIGTERM)
        try:
            relay_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            relay_process.kill()
    relay_process = None


def start_relay(sensor, mode, severity):
    global relay_process
    stop_relay()
    address, count = SENSOR_REGISTERS[sensor]
    argv = [
        "python3", RELAY_SCRIPT,
        "--target-host", PLC_HOST,
        "--target-port", str(PLC_PORT),
        "--listen-port", str(RELAY_LISTEN_PORT),
        "--register-type", "input",
        "--address", str(address),
        "--count", str(count),
        "--mode", str(mode),
        "--severity", str(severity),
    ]
    log = open(RELAY_LOG, "a")
    relay_process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT)


def configure_relay(payload):
    sensor = payload.get("sensor")
    mode = int(payload.get("mode", FAULT_MODE_NONE))
    severity = float(payload.get("severity", 0.0))

    if mode == FAULT_MODE_NONE or sensor is None:
        stop_relay()
        state["relay"] = {"sensor": None, "mode": FAULT_MODE_NONE, "severity": 0.0}
        return {"ok": True, "relay": state["relay"]}

    if sensor not in SENSOR_REGISTERS:
        return {"ok": False, "error": f"unknown sensor {sensor!r}"}

    try:
        start_relay(sensor, mode, severity)
    except Exception as exc:
        # start_relay()'s internal stop_relay() already killed whatever was
        # running - state must reflect that nothing is active now, not the
        # requested-but-failed config, or the dashboard would show a
        # "relaying X" that isn't actually running.
        state["relay"] = {"sensor": None, "mode": FAULT_MODE_NONE, "severity": 0.0}
        return {"ok": False, "error": f"failed to start relay: {exc}"}

    state["relay"] = {"sensor": sensor, "mode": mode, "severity": severity}
    return {"ok": True, "relay": state["relay"]}


def queue_c2(commands):
    with open(C2_PENDING_FILE, "w") as f:
        json.dump(commands, f)


def set_stuck_valve(payload):
    enabled = bool(payload.get("enabled"))
    if enabled:
        valve = payload.get("valve")
        if valve not in VALVE_MANUAL_SP:
            return {"ok": False, "error": f"unknown valve {valve!r}"}
        percent = max(0.0, min(100.0, float(payload.get("percent", 0.0))))
        register_value = round((percent / 100.0) * 65535)
        queue_c2([
            {"action": "write_register", "address": VALVE_MANUAL_SP[valve], "value": register_value},
            {"action": "write_coil", "address": MANUAL_MODE_COIL, "value": True},
        ])
        state["stuck_valve"] = {"enabled": True, "valve": valve, "percent": percent}
    else:
        queue_c2([{"action": "write_coil", "address": MANUAL_MODE_COIL, "value": False}])
        state["stuck_valve"]["enabled"] = False

    return {"ok": True, "stuck_valve": state["stuck_valve"]}


def current_status():
    return {
        "relay": dict(state["relay"]),
        "stuck_valve": dict(state["stuck_valve"], pending=os.path.exists(C2_PENDING_FILE)),
    }


async def handle_client(reader, writer):
    try:
        line = await asyncio.wait_for(reader.readline(), timeout=5)
        if not line:
            return
        req = json.loads(line.decode())
        request = req.get("request")
        if request == "read":
            response = current_status()
        elif request == "configure_relay":
            # configure_relay() can block on subprocess.wait() (stop_relay())
            # for up to 3s - run it off the event loop so a slow relay
            # shutdown doesn't stall every other connection, including a
            # concurrent status poll.
            async with relay_lock:
                response = await asyncio.get_event_loop().run_in_executor(None, configure_relay, req)
        elif request == "set_stuck_valve":
            response = set_stuck_valve(req)
        else:
            response = {"ok": False, "error": f"unknown request {request!r}"}
        writer.write((json.dumps(response) + "\n").encode())
        await writer.drain()
    except Exception as exc:
        try:
            writer.write((json.dumps({"ok": False, "error": str(exc)}) + "\n").encode())
            await writer.drain()
        except Exception:
            pass
    finally:
        writer.close()


def kill_stray_relays():
    # subprocess.Popen children aren't tied to this process's lifetime - if
    # this daemon restarts (a crash, a manual restart, supervisord's
    # autorestart) while a relay was active, the in-memory relay_process
    # handle is gone but the actual child keeps running, orphaned, still
    # bound to RELAY_LISTEN_PORT and still relaying - and the fresh
    # daemon's own state starts at "off" with no way to find or stop it.
    # Found exactly this way: restarting cyber-injects-control for a code
    # reload left a stray relay running alongside the new one, both
    # answering on the same port. Belt-and-suspenders cleanup at startup,
    # since this state reset is meant to mean "everything off."
    try:
        subprocess.run(["pkill", "-f", RELAY_SCRIPT])
    except Exception as exc:
        print(f"[control_daemon] stray-relay cleanup failed: {exc}", flush=True)


async def main():
    kill_stray_relays()
    server = await asyncio.start_server(handle_client, LISTEN_HOST, LISTEN_PORT)
    print(f"[control_daemon] listening on {LISTEN_HOST}:{LISTEN_PORT}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
