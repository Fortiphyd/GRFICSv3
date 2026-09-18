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
exec /usr/local/zeek/bin/zeek -i mirror0 local
