#!/bin/bash
set -e

# Detect the interface with an IP in the 192.168.95.x range
IF=$(ip -o -4 addr show | awk '$4 ~ /^192\.168\.95\./ {print $2}' | head -n1)

if [ -z "$IF" ]; then
    echo "[simulation-init] No interface found with 192.168.95.x address — skipping alias setup"
    exit 1
fi

echo "[simulation-init] Adding Modbus IP aliases to $IF..."
ip addr add 192.168.95.10/24 dev "$IF" 2>/dev/null || true
ip addr add 192.168.95.11/24 dev "$IF" 2>/dev/null || true
ip addr add 192.168.95.12/24 dev "$IF" 2>/dev/null || true
ip addr add 192.168.95.13/24 dev "$IF" 2>/dev/null || true
ip addr add 192.168.95.14/24 dev "$IF" 2>/dev/null || true
ip addr add 192.168.95.15/24 dev "$IF" 2>/dev/null || true

# Route to DMZ/defender network via router
ip route add 192.168.90.0/24 via 192.168.95.200 2>/dev/null || true
