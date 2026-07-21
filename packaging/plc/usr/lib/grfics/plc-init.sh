#!/bin/bash
set -e
ldconfig
ip route add 192.168.90.0/24 via 192.168.95.200 2>/dev/null || true
