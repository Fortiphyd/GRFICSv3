#!/bin/bash
set -e

VNC_PASS="${VNC_PASSWORD:-changeme}"
VNC_PASS_FILE="/etc/x11vnc.pass"

# Always overwrite with the proper format
x11vnc -storepasswd "${VNC_PASS}" "${VNC_PASS_FILE}" >/dev/null 2>&1
chmod 600 "${VNC_PASS_FILE}"
# ensure /opt/noVNC/utils/novnc_proxy exists; otherwise use websockify
if [ ! -x /opt/noVNC/utils/novnc_proxy ]; then
  # try to install websockify script entry point
  if [ -f /opt/noVNC/utils/websockify/run ]; then
    ln -s /opt/noVNC/utils/websockify/run /opt/noVNC/utils/novnc_proxy || true
  fi
fi

# Export display and resolution (allow override)
export DISPLAY=${DISPLAY:-:1}
export RESOLUTION=${RESOLUTION:-1280x720}

route add -net 192.168.95.0/24 gw 192.168.90.200

# Start supervisord (the default CMD will run supervisord, but start.sh can exec it)
exec "$@"
