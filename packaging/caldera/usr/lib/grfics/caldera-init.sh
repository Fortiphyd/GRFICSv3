#!/bin/bash
set -e

# Route to ICS/LAN so sandcat agents on 192.168.95.x can reach the C2 server
ip route add 192.168.95.0/24 via 192.168.90.200 2>/dev/null || true
