#!/bin/bash
# Turns off traffic mirroring enabled by enable-mirror.sh. See
# docs/zeek-network-mirroring-design.md.
set -euo pipefail

HOST_IF=mirror0-host

if [ "$(id -u)" -ne 0 ]; then
    echo "disable-mirror.sh must be run as root (sudo ./disable-mirror.sh)" >&2
    exit 1
fi

if ! ip link show "$HOST_IF" >/dev/null 2>&1; then
    echo "Mirroring isn't enabled - nothing to do."
    exit 0
fi

PARENT_IF=$(docker network inspect grficsv3_c-dmz-net -f '{{index .Options "parent"}}' 2>/dev/null || true)
if [ -n "$PARENT_IF" ]; then
    # Removing the clsact qdisc takes every filter on it with it in one
    # step - no need to delete filters individually.
    tc qdisc del dev "$PARENT_IF" clsact 2>/dev/null || true
fi

# Deleting either end of a veth pair removes both - this also removes the
# "mirror0" end from inside the zeek container.
ip link del "$HOST_IF"

echo "Mirroring disabled."
