#!/bin/bash
set -e

# The interface list is computed by network-init.py from the admin's IDS
# monitor settings (Settings > Network Zones), one -i per monitored zone —
# scales to however many zones/interfaces the host actually has.
IFACES=()
if [ -s /run/grfics/ids-ifaces ]; then
    while IFS= read -r iface; do
        [ -n "$iface" ] && IFACES+=(-i "$iface")
    done < /run/grfics/ids-ifaces
fi
if [ ${#IFACES[@]} -eq 0 ]; then
    echo "grfics: no interfaces configured for IDS monitoring, falling back to eth2" >&2
    IFACES=(-i eth2)
fi

exec /usr/bin/suricata "${IFACES[@]}" -c /etc/suricata/suricata.yaml
