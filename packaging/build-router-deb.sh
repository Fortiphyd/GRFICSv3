#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Derive version from git tags; replace leading v and convert git describe separators
# to deb-safe characters (e.g. v1.3-17-gabcdef -> 1.3+17+gabcdef)
VERSION=$(git -C "$REPO_ROOT" describe --tags --always 2>/dev/null \
    | sed 's/^v//' \
    | sed 's/-\([0-9]*\)-g/+\1+g/')
echo "Building grfics-router version: $VERSION"

PKG_NAME="grfics-router_${VERSION}_amd64"
STAGING="$SCRIPT_DIR/dist/staging/$PKG_NAME"
DIST="$SCRIPT_DIR/dist"

# Clean and create staging directory
rm -rf "$STAGING"
mkdir -p "$STAGING"

# --- DEBIAN control files ---
cp -r "$SCRIPT_DIR/router/DEBIAN" "$STAGING/DEBIAN"
sed -i "s/^Version:.*/Version: $VERSION/" "$STAGING/DEBIAN/control"
chmod 755 "$STAGING/DEBIAN/postinst" "$STAGING/DEBIAN/prerm"

# --- Application files ---
# Flask's default loader (app.py sets no template_folder) expects templates/
# under the app root, same layout the Docker build uses.
mkdir -p "$STAGING/opt/fwui/templates" "$STAGING/opt/fwui/static"
cp "$REPO_ROOT/router/app.py" "$STAGING/opt/fwui/"
cp "$REPO_ROOT/router/arpmon.py" "$STAGING/opt/fwui/"
cp "$REPO_ROOT/router"/*.html "$STAGING/opt/fwui/templates/"
cp -r "$REPO_ROOT/router/static/"* "$STAGING/opt/fwui/static/"

# --- Configuration files ---
# suricata.yaml/dnsmasq.conf/ulogd.conf are NOT shipped at their live /etc
# paths — those paths are already owned by the suricata/dnsmasq/ulogd2
# packages we depend on, and dpkg refuses to let two packages own the same
# file. Ship them under /usr/lib/grfics/config/ instead; postinst copies
# them into place after the dependency packages have unpacked their own
# defaults there.
mkdir -p "$STAGING/etc/suricata/rules" "$STAGING/usr/lib/grfics/config"
cp "$REPO_ROOT/router/quickdraw.rules" "$STAGING/etc/suricata/rules/quickdraw.rules"
cp "$REPO_ROOT/router/suricata.yaml" "$STAGING/usr/lib/grfics/config/suricata.yaml"
cp "$REPO_ROOT/router/dnsmasq.conf" "$STAGING/usr/lib/grfics/config/dnsmasq.conf"
cp "$REPO_ROOT/router/ulogd.conf" "$STAGING/usr/lib/grfics/config/ulogd.conf"

# --- Systemd units ---
mkdir -p "$STAGING/lib/systemd/system"
cp "$SCRIPT_DIR/router/systemd/"*.service "$STAGING/lib/systemd/system/"

# --- Init scripts ---
mkdir -p "$STAGING/usr/lib/grfics"
cp "$SCRIPT_DIR/router/usr/lib/grfics/network-init.py" "$STAGING/usr/lib/grfics/"
cp "$SCRIPT_DIR/router/usr/lib/grfics/suricata-start.sh" "$STAGING/usr/lib/grfics/"
cp "$SCRIPT_DIR/router/usr/lib/grfics/zone-iface-tool.py" "$STAGING/usr/lib/grfics/"
chmod 755 "$STAGING/usr/lib/grfics/network-init.py" "$STAGING/usr/lib/grfics/suricata-start.sh" \
          "$STAGING/usr/lib/grfics/zone-iface-tool.py"

# --- Build ---
mkdir -p "$DIST"
dpkg-deb --build --root-owner-group "$STAGING" "$DIST/${PKG_NAME}.deb"

echo ""
echo "Package built: $DIST/${PKG_NAME}.deb"
dpkg-deb -I "$DIST/${PKG_NAME}.deb"
