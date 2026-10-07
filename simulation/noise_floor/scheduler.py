#!/usr/bin/env python3
"""Seeded ambient noise-floor scheduler for the Fault Injection exercise.

See docs/cyber-vs-physical-fault-injection-design.md §5 for the design
this implements. Default is OFF ("quiet") - deliberately: this only starts
generating ambient events once explicitly enabled via the shared state
file, which web_visualization/data/index.php writes to when the dashboard
POSTs noise_floor_* fields. A fresh install, or a fresh state file, never
generates noise on its own.

Runs as its own always-on supervisord program (see supervisord.conf),
connecting to the same TE_process control socket (127.0.0.1:55555) that
index.php and the Modbus remote-IO devices use, with the same
{"request": "write", "data": {"inputs": {...}}} protocol - see
simulation/remote_io/modbus/modbusdevice.py's writeData() for the
existing precedent this follows.

Three ambient event types, all reusing existing physical fault fields at
low severity/brief duration rather than anything new:
  - sensor noise (fault_mode=3) on a random sensor tag
  - sensor dropout (fault_mode=4) on a random sensor tag
  - valve stickiness (*_stuck) on a random valve

Two more ambient event types from the design (minor EWS setpoint nudges,
benign ARP churn) are NOT implemented here - they don't go through this
container's control socket at all (EWS's own control path; the DMZ/ICS
network layer respectively) and are a separate, later piece of work.
"""

import json
import os
import random
import socket
import time

STATE_FILE = "/app/noise_floor/state.json"
HOST, PORT = "127.0.0.1", 55555

SENSOR_TAGS = [
    "tank_pressure", "tank_level", "f1_flow", "f2_flow",
    "purge_flow", "product_flow", "analyzer",
]
STUCK_TAGS = ["f1_stuck", "f2_stuck", "purge_stuck", "product_stuck"]

# Ambient events are deliberately minor/brief - see the design doc's
# "transient vs. persistent as a distinguishing axis" - these should
# self-resolve in a few seconds, unlike a real triggered fault.
NOISE_AMPLITUDE = 1.0   # see TE_process.cc's uniform_noise() - +/- this value
DROPOUT_DUTY = 0.15     # fraction of each 10s period reporting dropout (TE_process.cc's in_dropout_phase())
HOLD_SECONDS = (2.0, 8.0)  # random hold duration before reverting

DEFAULT_STATE = {
    "enabled": False,
    "seed": 0,
    "mean_interval_s": 30.0,
    "suppress_until": 0.0,
}


def ensure_state_file():
    # This process runs as root (supervisord), but index.php writes to this
    # same file as www-data - file permissions (not just the directory's)
    # govern overwriting an existing file's content, so this needs to be
    # explicitly opened up regardless of which side creates it first.
    if not os.path.exists(STATE_FILE):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(DEFAULT_STATE, f)
    os.chmod(STATE_FILE, 0o666)


def load_state():
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        merged = dict(DEFAULT_STATE)
        merged.update(state)
        return merged
    except Exception:
        return dict(DEFAULT_STATE)


def connect():
    while True:
        try:
            s = socket.create_connection((HOST, PORT), timeout=5)
            print("[noise-floor] connected to simulation control socket", flush=True)
            return s
        except OSError as e:
            print(f"[noise-floor] waiting for simulation ({e}), retrying...", flush=True)
            time.sleep(2)


def send_write(sock, fields):
    request = json.dumps({"request": "write", "data": {"inputs": fields}}) + "\n"
    sock.sendall(request.encode())
    sock.recv(4096)  # drain the response; we don't need the echoed outputs


def pick_event(rng):
    kind = rng.choice(["noise", "dropout", "stuck"])
    tag = rng.choice(STUCK_TAGS) if kind == "stuck" else rng.choice(SENSOR_TAGS)
    return kind, tag


def apply_event(sock, kind, tag):
    if kind == "stuck":
        send_write(sock, {tag: True})
    elif kind == "noise":
        send_write(sock, {f"{tag}_fault_mode": 3, f"{tag}_fault_severity": NOISE_AMPLITUDE})
    elif kind == "dropout":
        send_write(sock, {f"{tag}_fault_mode": 4, f"{tag}_fault_severity": DROPOUT_DUTY})


def revert_event(sock, kind, tag):
    if kind == "stuck":
        send_write(sock, {tag: False})
    else:
        send_write(sock, {f"{tag}_fault_mode": 0, f"{tag}_fault_severity": 0.0})


def main():
    ensure_state_file()
    sock = connect()
    rng = None
    last_seed = None
    was_enabled = False

    while True:
        state = load_state()
        enabled = bool(state.get("enabled"))
        seed = state.get("seed", 0)
        mean_interval = max(1.0, float(state.get("mean_interval_s", 30.0)))

        # Re-seed on first enable and on any seed change while enabled, so
        # the ambient sequence is reproducible from the configured seed
        # (see design doc: "every participant experiences the identical
        # ambient pattern").
        if enabled and (rng is None or seed != last_seed or (enabled and not was_enabled)):
            rng = random.Random(seed)
            last_seed = seed
            print(f"[noise-floor] enabled, seed={seed}, mean_interval={mean_interval}s", flush=True)
        if was_enabled and not enabled:
            print("[noise-floor] disabled", flush=True)
        was_enabled = enabled

        if not enabled:
            time.sleep(1)
            continue

        # Poisson process: exponentially-distributed inter-arrival times.
        wait = rng.expovariate(1.0 / mean_interval)
        slept = 0.0
        while slept < wait:
            time.sleep(min(1.0, wait - slept))
            slept += 1.0
            if not load_state().get("enabled"):
                break
        if not load_state().get("enabled"):
            continue

        state = load_state()
        if time.time() < float(state.get("suppress_until", 0.0)):
            continue  # quiet buffer around a real triggered event

        kind, tag = pick_event(rng)
        hold = rng.uniform(*HOLD_SECONDS)
        try:
            print(f"[noise-floor] {kind} on {tag} for {hold:.1f}s", flush=True)
            apply_event(sock, kind, tag)
            time.sleep(hold)
            revert_event(sock, kind, tag)
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            print(f"[noise-floor] socket error ({e}), reconnecting", flush=True)
            sock = connect()


if __name__ == "__main__":
    main()
