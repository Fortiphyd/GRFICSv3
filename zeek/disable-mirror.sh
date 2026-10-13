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

DMZ_PARENT=$(docker network inspect grficsv3_c-dmz-net -f '{{index .Options "parent"}}' 2>/dev/null || true)
ICS_PARENT=$(docker network inspect grficsv3_b-ics-net -f '{{index .Options "parent"}}' 2>/dev/null || true)
# Removing the clsact qdisc takes every filter on it with it in one step -
# no need to delete filters individually. Also clear the bare NIC, which
# older layouts (both zones on plain eth0) mirrored from.
for dev in "${DMZ_PARENT%%.*}" "$DMZ_PARENT" "$ICS_PARENT"; do
    [ -n "$dev" ] && tc qdisc del dev "$dev" clsact 2>/dev/null || true
done

# Deleting either end of a veth pair removes both - this also removes the
# "mirror0" end from inside the zeek container.
ip link del "$HOST_IF"

echo "Mirroring disabled."
