#!/bin/bash
# Turns on traffic mirroring into the "zeek" container - see
# docs/zeek-network-mirroring-design.md for the design and how this was
# validated. Deliberately separate from `docker compose up`: this is an
# opt-in advanced feature, not part of the default install.
#
# Requires: a native Linux Docker host (not Docker Desktop's VM), root,
# and the "zeek" and "siem" profile containers already up
# (`docker compose --profile siem up -d`).
set -euo pipefail

MIRROR_IF=mirror0
HOST_IF=mirror0-host

if [ "$(id -u)" -ne 0 ]; then
    echo "enable-mirror.sh must be run as root (sudo ./enable-mirror.sh)" >&2
    exit 1
fi

if ! command -v tc >/dev/null 2>&1; then
    echo "tc (iproute2) not found on this host - required for mirroring" >&2
    exit 1
fi

ZEEK_PID=$(docker inspect -f '{{.State.Pid}}' zeek 2>/dev/null || true)
if [ -z "$ZEEK_PID" ] || [ "$ZEEK_PID" = "0" ]; then
    echo "zeek container isn't running - start it first:" >&2
    echo "  docker compose --profile siem up -d zeek" >&2
    exit 1
fi

if ip link show "$HOST_IF" >/dev/null 2>&1; then
    echo "Mirroring already enabled ($HOST_IF exists). Run disable-mirror.sh first to reconfigure."
    exit 0
fi

PARENT_IF=$(docker network inspect grficsv3_c-dmz-net -f '{{index .Options "parent"}}')
DMZ_SUBNET=$(docker network inspect grficsv3_c-dmz-net -f '{{range .IPAM.Config}}{{.Subnet}}{{end}}')
ICS_SUBNET=$(docker network inspect grficsv3_b-ics-net -f '{{range .IPAM.Config}}{{.Subnet}}{{end}}')

if [ -z "$PARENT_IF" ] || [ -z "$DMZ_SUBNET" ] || [ -z "$ICS_SUBNET" ]; then
    echo "Couldn't read parent interface/subnets from the grficsv3_b-ics-net" >&2
    echo "and grficsv3_c-dmz-net Docker networks - has 'docker compose up'" >&2
    echo "been run at least once?" >&2
    exit 1
fi

echo "Mirroring $PARENT_IF ($DMZ_SUBNET, $ICS_SUBNET) into the zeek container..."

# Recreating the zeek container (e.g. a rebuild) destroys its netns, which
# silently deletes mirror0/mirror0-host - removing one end of a veth pair
# removes both - but does NOT clean up the clsact qdisc left on the host's
# parent interface. That leaves a stale qdisc that the $HOST_IF check above
# won't catch (mirror0-host is legitimately gone), and "tc qdisc add" fails
# with "Exclusivity flag on, cannot modify" on the leftover one. Confirmed
# live - this exact sequence happened during testing. Clear it
# unconditionally before setting up fresh state, since we're about to
# create authoritative state anyway.
tc qdisc del dev "$PARENT_IF" clsact 2>/dev/null || true

ip link add "$HOST_IF" type veth peer name "$MIRROR_IF"
ip link set "$MIRROR_IF" netns "$ZEEK_PID"
ip link set "$HOST_IF" up
nsenter -t "$ZEEK_PID" -n ip link set "$MIRROR_IF" up

# clsact supports both ingress and egress tc filters on one qdisc. Matching
# on dst_ip alone (in either direction) is enough to see full two-way
# exchanges - validated live: a full request/reply exchange between two
# macvlan siblings showed up complete and duplicate-free with exactly this
# filter set.
tc qdisc add dev "$PARENT_IF" clsact
for subnet in "$DMZ_SUBNET" "$ICS_SUBNET"; do
    tc filter add dev "$PARENT_IF" ingress protocol ip flower dst_ip "$subnet" \
        action mirred egress mirror dev "$HOST_IF"
    tc filter add dev "$PARENT_IF" egress protocol ip flower dst_ip "$subnet" \
        action mirred egress mirror dev "$HOST_IF"
done

echo "Mirroring enabled. Disable with: sudo ./disable-mirror.sh"
