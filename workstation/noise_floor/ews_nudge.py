#!/usr/bin/env python3
"""EWS ambient "noise floor" setpoint nudges.

See docs/cyber-vs-physical-fault-injection-design.md §5 - one of the two
still-missing ambient event types (the other is benign ARP churn). Exists
specifically to undermine §4.4's stuck-valve distractor: a legitimate
engineer occasionally tuning a process setpoint is normal background
texture throughout the session, so participants can't shortcut on "a
setpoint write happened, must be the engineer" when the real attack
fires - they have to look at the *shape* of a burst (scattered across
different registers vs. rapid repeated writes to the same one) instead.

Runs continuously on the EWS (engineering workstation) container, which
sits directly on the ICS network (192.168.95.5) - same segment as the
PLC - so this writes with EWS's own real, expected IP, the same way a
real engineer's workstation would, not through any attacker-positioned
channel.

What it writes: NOT the valve position registers (%QW100-103) - those are
ladder-logic-*computed outputs*, overwritten by the PLC every scan cycle
(see plc/st_files/326339.st's control() calls), so writing there would be
silently clobbered with no lasting effect. The real externally-adjustable
targets are the *process* setpoints those control loops read from:
pressure_sp (%MW2) and level_sp (%MW4). OpenPLC's Modbus server maps %MW
to holding registers starting at 1024 (confirmed in
plc/webserver/core/modbus.cpp: int_memory[i - 1024] = &mb_holding_regs[i]),
so %MW2 = holding register 1026, %MW4 = holding register 1028. A third
setpoint (a_setpoint, driving the feed-2 valve's composition control) was
deliberately left out - its register appears to use a different raw-value
convention than its own measurement does, and that wasn't confirmed live
before this was built.

Respects the noise floor's single enabled/quiet-buffer state without any
new cross-container plumbing: just polls the dashboard's existing
`/data/index.php` endpoint (reachable over a-grfics-admin, the same
out-of-band network every container is already on), which already
returns `noise_floor.enabled` / `seed` / `mean_interval_s` /
`suppress_until` / `suppressed_tags` on every plain GET - no dashboard or
backend changes needed for this script to exist. Re-seeds (for the same
reproducible-per-seed guarantee the main scheduler gives) whenever noise
floor transitions off->on or the seed changes, and reuses the same
mean_interval_s rather than adding a second density knob to the
dashboard.
"""
import json
import random
import socket
import struct
import time
import urllib.request

DASHBOARD_URL = "http://simulation/data/index.php"
PLC_HOST = "192.168.95.2"
PLC_PORT = 502
POLL_INTERVAL_S = 2.0

# tag names match simulation/noise_floor/scheduler.py's SENSOR_TAGS / the
# dashboard's FAULT_SENSORS keys, so the *existing* suppressed_tags
# mechanism (index.php's derive_affected_tags()) already covers these -
# a real fault/attack on the pressure or level sensor suppresses the
# matching tag, and this script just has to honor it, not reimplement it.
SETPOINTS = {
    "tank_pressure": {"register": 1026},  # pressure_sp (%MW2) -> purge valve
    "tank_level":    {"register": 1028},  # level_sp (%MW4) -> product valve
}

# A %FS fraction is the same fraction of the raw 0-65535 register range
# regardless of a sensor's own engineering full-scale (register = value /
# full_scale * 65535 for every sensor in this project, confirmed against
# simulation/simulation/remote_io/modbus/*.py) - so the nudge magnitude
# doesn't need each setpoint's own full-scale value, just this fraction.
MAX_NUDGE_FRACTION = 0.02
MODBUS_UNIT_ID = 1


def log(msg):
    print(f"[ews_nudge] {msg}", flush=True)


def fetch_noise_floor_state():
    try:
        with urllib.request.urlopen(DASHBOARD_URL, timeout=3) as resp:
            data = json.loads(resp.read().decode())
        return data.get("noise_floor") or {}
    except Exception as exc:
        log(f"could not reach dashboard: {exc}")
        return {}


def is_suppressed(tag, nf_state):
    if time.time() >= float(nf_state.get("suppress_until", 0) or 0):
        return False
    return tag in (nf_state.get("suppressed_tags") or [])


def read_register(address):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect((PLC_HOST, PLC_PORT))
    pdu = struct.pack(">BHH", 3, address, 1)
    mbap = struct.pack(">HHHB", 1, 0, len(pdu) + 1, MODBUS_UNIT_ID)
    s.sendall(mbap + pdu)
    resp = s.recv(256)
    s.close()
    # MBAP (7 bytes) + function code (1) + byte count (1) + 1 register (2)
    return struct.unpack(">H", resp[9:11])[0]


def write_register(address, value):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect((PLC_HOST, PLC_PORT))
    pdu = struct.pack(">BHH", 6, address, value)
    mbap = struct.pack(">HHHB", 1, 0, len(pdu) + 1, MODBUS_UNIT_ID)
    s.sendall(mbap + pdu)
    resp = s.recv(256)
    s.close()
    return resp


def nudge(tag, rng):
    register = SETPOINTS[tag]["register"]
    try:
        current = read_register(register)
    except Exception as exc:
        log(f"{tag}: read failed, skipping this cycle ({exc})")
        return
    max_delta = round(MAX_NUDGE_FRACTION * 65535)
    delta = rng.randint(-max_delta, max_delta)
    new_value = max(0, min(65535, current + delta))
    try:
        resp = write_register(register, new_value)
        log(f"{tag}: nudged holding register {register}: {current} -> {new_value} "
            f"(response {resp.hex()})")
    except Exception as exc:
        log(f"{tag}: write failed ({exc})")


def main():
    rng = None
    last_seed = None
    was_enabled = False
    next_fire = None

    while True:
        try:
            nf_state = fetch_noise_floor_state()
            enabled = bool(nf_state.get("enabled"))
            seed = nf_state.get("seed", 0)
            mean_interval_s = max(1.0, float(nf_state.get("mean_interval_s", 30.0) or 30.0))

            if enabled and (not was_enabled or seed != last_seed):
                rng = random.Random(seed)
                last_seed = seed
                next_fire = time.time() + rng.expovariate(1.0 / mean_interval_s)
                log(f"(re)seeded with seed={seed}, mean_interval_s={mean_interval_s}")
            was_enabled = enabled

            if enabled and rng is not None and next_fire is not None and time.time() >= next_fire:
                tag = rng.choice(list(SETPOINTS))
                if is_suppressed(tag, nf_state):
                    log(f"{tag}: suppressed (real fault/attack just triggered), skipping")
                else:
                    nudge(tag, rng)
                next_fire = time.time() + rng.expovariate(1.0 / mean_interval_s)
        except Exception as exc:
            log(f"unexpected error, continuing: {exc}")

        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
