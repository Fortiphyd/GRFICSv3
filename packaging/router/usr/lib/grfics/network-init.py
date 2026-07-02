#!/usr/bin/env python3
"""GRFICSv3 router network initialization.

Assigns the gateway address on every zone interface, rebuilds the NAT
POSTROUTING chain, and writes the list of interfaces Suricata should
capture on. Zones = the auto-detected LAN/DMZ subnets plus whatever the
admin configured in /etc/firewall/config.json's "zones" list, so this
scales to any number of interfaces without assuming fixed names.

Safe to re-run at any time (systemd boot, or on demand from the web UI
after the admin adds/removes a zone) — every step is idempotent.
"""
import ipaddress
import json
import os
import re
import subprocess
import sys

CONFIG_PATH = "/etc/firewall/config.json"
RUN_DIR = "/run/grfics"

BUILTIN_ZONES = {
    "LAN": ipaddress.ip_network("192.168.95.0/24"),
    "DMZ": ipaddress.ip_network("192.168.90.0/24"),
}
DEFAULT_IDS_MONITOR = {"LAN": False, "DMZ": True}


def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def detect_ifaces():
    """Return {iface: [ipaddress.IPv4Address, ...]} for non-loopback interfaces."""
    out = subprocess.run(
        ["ip", "-o", "-4", "addr"], capture_output=True, text=True, check=True
    ).stdout
    ifaces = {}
    for line in out.splitlines():
        m = re.match(r"^\d+:\s+(\S+)\s+inet (\d+\.\d+\.\d+\.\d+)/\d+", line)
        if not m:
            continue
        iface = m.group(1).split("@")[0]
        if iface == "lo":
            continue
        ifaces.setdefault(iface, []).append(ipaddress.ip_address(m.group(2)))
    return ifaces


def find_iface_for_subnet(ifaces, network):
    for iface, addrs in ifaces.items():
        if any(addr in network for addr in addrs):
            return iface
    return None


def collect_zones(config, ifaces):
    """Return a list of (label, network, iface_or_None, ids_monitor) tuples."""
    ids_monitor = {**DEFAULT_IDS_MONITOR, **config.get("ids_monitor", {})}
    overrides = config.get("zone_iface_overrides", {})

    zones = []
    for label, network in BUILTIN_ZONES.items():
        # Auto-detect (an interface already carrying an address in this
        # subnet — the old Docker/macvlan behavior) first; if nothing
        # matches, fall back to the admin's explicit binding for a blank
        # interface, e.g. on a fresh bare-metal/VM install where nothing
        # pre-assigns the router's own address on each zone's NIC.
        iface = find_iface_for_subnet(ifaces, network) or overrides.get(label)
        zones.append((label, network, iface, ids_monitor.get(label, False)))

    for z in config.get("zones", []):
        try:
            network = ipaddress.ip_network(z["subnet"], strict=False)
        except (KeyError, ValueError) as e:
            print(f"network-init: skipping invalid zone {z!r}: {e}", file=sys.stderr)
            continue
        iface = z.get("iface")
        if not iface:
            print(f"network-init: skipping zone with no interface: {z!r}", file=sys.stderr)
            continue
        zones.append((z.get("label", iface), network, iface, bool(z.get("ids_monitor", False))))

    return zones


def assign_gateways(zones):
    for label, network, iface, _monitor in zones:
        if not iface:
            continue
        # network.hosts() returns a generator normally but a plain list for
        # /31 and /32 — list(...)[0] works for both instead of next(...),
        # which raises TypeError on the list case.
        hosts = list(network.hosts())
        if not hosts:
            print(f"network-init: {label} subnet {network} has no usable host address", file=sys.stderr)
            continue
        gateway = hosts[0]
        subprocess.run(
            ["ip", "addr", "add", f"{gateway}/{network.prefixlen}", "dev", iface],
            check=False, stderr=subprocess.DEVNULL,
        )


def rebuild_nat(zones):
    subprocess.run(["iptables", "-t", "nat", "-F", "POSTROUTING"], check=True)
    networks = [network for _, network, iface, _monitor in zones if iface]
    for src in networks:
        for dst in networks:
            subprocess.run(
                ["iptables", "-t", "nat", "-A", "POSTROUTING",
                 "-s", str(src), "-d", str(dst), "-j", "RETURN"],
                check=True,
            )
        subprocess.run(
            ["iptables", "-t", "nat", "-A", "POSTROUTING", "-s", str(src), "-j", "MASQUERADE"],
            check=True,
        )


def write_ids_ifaces(zones):
    os.makedirs(RUN_DIR, exist_ok=True)
    monitored = [iface for _, _, iface, monitor in zones if iface and monitor]
    with open(os.path.join(RUN_DIR, "ids-ifaces"), "w") as f:
        for iface in monitored:
            f.write(iface + "\n")


def main():
    # Default-deny forwarding; stateful rules applied by app.py on startup.
    subprocess.run(["iptables", "-P", "FORWARD", "DROP"], check=True)

    config = load_config()
    ifaces = detect_ifaces()
    zones = collect_zones(config, ifaces)

    assign_gateways(zones)
    rebuild_nat(zones)
    write_ids_ifaces(zones)


if __name__ == "__main__":
    main()
