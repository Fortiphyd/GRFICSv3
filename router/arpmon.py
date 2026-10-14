#!/usr/bin/env python3
"""
arpmon.py — ARP monitoring daemon.
Polls /proc/net/arp every POLL_INTERVAL seconds, detects new stations
and MAC-address changes, and appends events to a newline-delimited JSON
log file. State (known IP→MAC mappings with timestamps) is persisted to
a JSON file so it survives daemon restarts.
"""
import json, os, time
from datetime import datetime, timezone

ARP_PROC      = "/proc/net/arp"
STATE_FILE    = "/var/lib/arpmon/state.json"
LOG_FILE      = "/var/log/arpmon/events.json"
POLL_INTERVAL = 10  # seconds


def read_arp_table():
    """Return {ip: {mac, iface}} for all complete entries in /proc/net/arp."""
    entries = {}
    try:
        with open(ARP_PROC) as f:
            for line in f.readlines()[1:]:   # skip header row
                parts = line.split()
                if len(parts) < 6:
                    continue
                ip, _hw_type, flags, mac, _mask, iface = parts[:6]
                if flags == "0x0":           # incomplete — ARP not yet resolved
                    continue
                entries[ip] = {"mac": mac, "iface": iface}
    except FileNotFoundError:
        pass
    return entries


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def append_event(event):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def other_ips_with_mac(state, ip, mac):
    """Other known IPs whose last-seen MAC is `mac`, as "a, b" ("" if none).

    An IP moving to a MAC that already answers for a different IP is the
    classic ARP-spoofing signature (the attacker's own MAC claiming the
    victim's IP) - unlike a recreated container, which gets a brand-new MAC
    nobody else has. Comma-joined so Wazuh's JSON decoder sees a plain string.
    """
    return ", ".join(sorted(
        other for other, rec in state.items() if other != ip and rec["mac"] == mac))


def poll(state):
    now = now_iso()
    current = read_arp_table()

    for ip, info in current.items():
        mac   = info["mac"]
        iface = info["iface"]
        if ip not in state:
            event = {
                "timestamp": now, "event": "new_station",
                "ip": ip, "mac": mac, "iface": iface,
            }
            claimed = other_ips_with_mac(state, ip, mac)
            if claimed:
                event["mac_also_claimed_by"] = claimed
            state[ip] = {
                "mac": mac, "iface": iface,
                "first_seen": now, "last_seen": now,
            }
            append_event(event)
            print(f"[arpmon] new_station  {ip}  {mac}  ({iface})", flush=True)
        elif state[ip]["mac"] != mac:
            old_mac = state[ip]["mac"]
            event = {
                "timestamp": now, "event": "changed_mac",
                "ip": ip, "mac": mac, "old_mac": old_mac, "iface": iface,
            }
            claimed = other_ips_with_mac(state, ip, mac)
            if claimed:
                event["mac_also_claimed_by"] = claimed
            state[ip]["mac"]       = mac
            state[ip]["last_seen"] = now
            append_event(event)
            print(f"[arpmon] changed_mac  {ip}  {old_mac} -> {mac}  ({iface})"
                  + (f"  [MAC also used by {claimed}]" if claimed else ""), flush=True)
        else:
            state[ip]["last_seen"] = now

    save_state(state)


if __name__ == "__main__":
    print("[arpmon] starting", flush=True)
    state = load_state()
    while True:
        try:
            poll(state)
        except Exception as exc:
            print(f"[arpmon] error: {exc}", flush=True)
        time.sleep(POLL_INTERVAL)
