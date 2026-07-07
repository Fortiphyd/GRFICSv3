#!/bin/bash
set -e


# Ensure dnsmasq config files exist before supervisord starts dnsmasq
mkdir -p /etc/firewall /var/log/dnsmasq /var/log/arpmon /var/lib/arpmon /run/grfics
touch /etc/firewall/dns_hosts
[ -f /etc/firewall/dns_blocked.conf ] || touch /etc/firewall/dns_blocked.conf

# Default-deny forwarding, add .1 gateway aliases on every zone interface
# (containers use .1 as their Docker-IPAM-assigned default gateway — Docker
# reserves .200 for this container's own static IP), rebuild NAT, and write
# the list of interfaces Suricata should capture on. Same script app.py's
# _apply_network() re-runs on every zone/VPN change, so Docker and the
# VM/bare-metal package share one implementation instead of drifting.
python3 /usr/lib/grfics/network-init.py

# Show interfaces (for troubleshooting)
ip -c addr
ip route show

if getent hosts wazuh >/dev/null 2>&1; then
    /var/ossec/bin/wazuh-control start || true
else
    echo "[router] Wazuh not in DNS, skipping agent start"
fi

# Keep container running and provide a shell via exec
exec "$@"
