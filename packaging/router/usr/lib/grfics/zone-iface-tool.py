#!/usr/bin/env python3
"""Report/bind which interface plays the LAN/DMZ role — used by postinst
before app.py (and the web UI) is up, so this duplicates the minimal
detection logic from network-init.py rather than importing the Flask app.

Usage:
  zone-iface-tool.py status              print LAN=/DMZ=/AVAILABLE= lines
  zone-iface-tool.py bind LAN|DMZ IFACE  record an explicit interface binding
"""
import ipaddress
import json
import os
import re
import subprocess
import sys

CONFIG_PATH = "/etc/firewall/config.json"
WG_CONFIG_PATH = "/etc/firewall/wg_config.json"
BUILTIN_ZONES = {
    "LAN": ipaddress.ip_network("192.168.95.0/24"),
    "DMZ": ipaddress.ip_network("192.168.90.0/24"),
}


def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def tunnel_ifaces():
    """Interface names claimed by a WireGuard tunnel, new or old config schema
    — each tunnel is a real network interface (see app.py's multi-tunnel
    support), so none of them are "available" NICs a zone can bind to.
    """
    try:
        with open(WG_CONFIG_PATH) as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}
    names = {t["name"] for t in config.get("tunnels", []) if t.get("name")}
    names.add("wg0")  # old single-tunnel schema always used this name, and
                       # app.py hasn't run yet to migrate it to "tunnels" the
                       # first time this tool runs post-upgrade (postinst).
    return names


def link_ifaces():
    tunnels = tunnel_ifaces()
    out = subprocess.run(["ip", "-o", "link", "show"], capture_output=True, text=True, check=True).stdout
    ifaces = []
    for line in out.splitlines():
        m = re.match(r"^\d+:\s+(\S+):", line)
        if m:
            iface = m.group(1).split("@")[0]
            if iface != "lo" and iface not in tunnels:
                ifaces.append(iface)
    return ifaces


def scan_addrs():
    """Return (set of interfaces with any IPv4 address, {zone_label: iface})."""
    out = subprocess.run(["ip", "-o", "-4", "addr", "show"], capture_output=True, text=True, check=True).stdout
    has_ip = set()
    zone_iface = {}
    for line in out.splitlines():
        m = re.match(r"^\d+:\s+(\S+)\s+inet (\d+\.\d+\.\d+\.\d+)/\d+", line)
        if not m:
            continue
        iface = m.group(1).split("@")[0]
        has_ip.add(iface)
        addr = ipaddress.ip_address(m.group(2))
        for label, network in BUILTIN_ZONES.items():
            if addr in network:
                zone_iface[label] = iface
    return has_ip, zone_iface


def cmd_status():
    config = load_config()
    has_ip, zone_iface = scan_addrs()
    overrides = config.get("zone_iface_overrides", {})

    claimed = set(overrides.values())
    claimed |= {z.get("iface") for z in config.get("zones", []) if z.get("iface")}
    available = [i for i in link_ifaces() if i not in has_ip and i not in claimed]

    for label in BUILTIN_ZONES:
        print(f"{label}={zone_iface.get(label) or overrides.get(label) or ''}")
    print(f"AVAILABLE={' '.join(available)}")


def cmd_bind(label, iface):
    if label not in BUILTIN_ZONES:
        print(f"zone-iface-tool: unknown zone '{label}'", file=sys.stderr)
        sys.exit(1)
    config = load_config()
    config.setdefault("zone_iface_overrides", {})[label] = iface
    save_config(config)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "status":
        cmd_status()
    elif len(sys.argv) == 4 and sys.argv[1] == "bind":
        cmd_bind(sys.argv[2], sys.argv[3])
    else:
        print("usage: zone-iface-tool.py status | bind <LAN|DMZ> <iface>", file=sys.stderr)
        sys.exit(2)
