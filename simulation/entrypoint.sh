#!/bin/bash
set -e

# Detect interface by IP
IF=$(ip -o -4 addr show | awk '$4 ~ /^192\.168\.95\./ {print $2}' | head -n1)


echo "[entrypoint] Adding IP aliases to $IF manually..."

ip addr add 192.168.95.11/24 dev "$IF"
ip addr add 192.168.95.12/24 dev "$IF"
ip addr add 192.168.95.13/24 dev "$IF"
ip addr add 192.168.95.14/24 dev "$IF"
ip addr add 192.168.95.15/24 dev "$IF"

route add -net 192.168.90.0/24 gw 192.168.95.200

echo "[entrypoint] Starting nginx..."
php-fpm8.2 -D
nginx

echo "[entrypoint] Starting application..."
exec "$@"
