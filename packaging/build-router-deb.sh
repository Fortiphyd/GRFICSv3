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
mkdir -p "$STAGING/opt/fwui/static"
cp "$REPO_ROOT/router/app.py" "$STAGING/opt/fwui/"
cp "$REPO_ROOT/router/arpmon.py" "$STAGING/opt/fwui/"
cp "$REPO_ROOT/router"/*.html "$STAGING/opt/fwui/"
cp -r "$REPO_ROOT/router/static/"* "$STAGING/opt/fwui/static/"

# --- Configuration files ---
mkdir -p "$STAGING/etc/suricata/rules"
cp "$REPO_ROOT/router/suricata.yaml" "$STAGING/etc/suricata/suricata.yaml"
cp "$REPO_ROOT/router/quickdraw.rules" "$STAGING/etc/suricata/rules/quickdraw.rules"
cp "$REPO_ROOT/router/dnsmasq.conf" "$STAGING/etc/dnsmasq.conf"
cp "$REPO_ROOT/router/ulogd.conf" "$STAGING/etc/ulogd.conf"

# --- Systemd units ---
mkdir -p "$STAGING/lib/systemd/system"
cp "$SCRIPT_DIR/router/systemd/"*.service "$STAGING/lib/systemd/system/"

# --- Init script ---
mkdir -p "$STAGING/usr/lib/grfics"
cp "$SCRIPT_DIR/router/usr/lib/grfics/router-init.sh" "$STAGING/usr/lib/grfics/"
chmod 755 "$STAGING/usr/lib/grfics/router-init.sh"

# --- Build ---
mkdir -p "$DIST"
dpkg-deb --build --root-owner-group "$STAGING" "$DIST/${PKG_NAME}.deb"

echo ""
echo "Package built: $DIST/${PKG_NAME}.deb"
dpkg-deb -I "$DIST/${PKG_NAME}.deb"
