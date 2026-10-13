#!/bin/bash
set -e

# Mirroring is opt-in (see enable-mirror.sh) - the "mirror0" interface only
# exists once an instructor has run that script on the host. Wait for it
# rather than erroring out, and go back to waiting if it disappears
# (disable-mirror.sh deletes the veth pair, which removes mirror0 from
# inside this container too). supervisord's autorestart handles actually
# restarting this script when zeek exits; this loop just avoids a hard
# failure while nothing has been enabled yet.
while ! ip link show mirror0 >/dev/null 2>&1; do
    sleep 5
done

echo "grfics: mirror0 is up, starting zeek"
cd /usr/local/zeek/logs
# -C: mirror0 is a veth (virtual device), which - like loopback - typically
# has checksum offloading, so packets arrive with checksums the kernel
# never bothered to (re)compute. Zeek's default checksum validation reads
# that as corruption and silently discards every packet (confirmed live:
# zero protocol-level logs of any kind, e.g. no modbus.log against real
# PLC traffic, until this flag was added). This isn't specific to the mock
# testing that first surfaced it - it's inherent to how any veth-based
# mirror looks to Zeek, so it belongs here permanently, not as a one-off
# workaround.
exec /usr/local/zeek/bin/zeek -C -i mirror0 local
