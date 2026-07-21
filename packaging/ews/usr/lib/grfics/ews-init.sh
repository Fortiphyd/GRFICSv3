#!/bin/bash
set -e

ip route add 192.168.90.0/24 via 192.168.95.200 2>/dev/null || true

if getent hosts wazuh >/dev/null 2>&1; then
    /var/ossec/bin/wazuh-control start || true
else
    echo "[EWS] Wazuh not in DNS, skipping agent start"
fi
