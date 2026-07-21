#!/bin/bash
# Build dependencies (must be installed on build machine):
#   apt install dpkg-dev
#
# This is a thin package — no compilation happens at build time. Heavy install
# steps (noVNC clone, OpenPLC Editor clone + install) run in postinst on the
# target machine. Build time is fast; first install takes several minutes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VERSION=$(git -C "$REPO_ROOT" describe --tags --always 2>/dev/null \
    | sed 's/^v//' \
    | sed 's/-\([0-9]*\)-g/+\1+g/')
echo "Building grfics-ews version: $VERSION"

PKG_NAME="grfics-ews_${VERSION}_amd64"
STAGING="$SCRIPT_DIR/dist/staging/$PKG_NAME"
DIST="$SCRIPT_DIR/dist"

# --- Set up staging directory ---
rm -rf "$STAGING"
mkdir -p "$STAGING"

# --- DEBIAN control files ---
cp -r "$SCRIPT_DIR/ews/DEBIAN" "$STAGING/DEBIAN"
sed -i "s/^Version:.*/Version: $VERSION/" "$STAGING/DEBIAN/control"
chmod 755 "$STAGING/DEBIAN/postinst" "$STAGING/DEBIAN/prerm"

# --- Dedicated supervisord config ---
mkdir -p "$STAGING/etc/grfics"
cp "$SCRIPT_DIR/ews/etc/grfics/ews-supervisord.conf" \
   "$STAGING/etc/grfics/ews-supervisord.conf"

# --- Systemd units ---
mkdir -p "$STAGING/lib/systemd/system"
cp "$SCRIPT_DIR/ews/systemd/"*.service "$STAGING/lib/systemd/system/"

# --- Init script ---
mkdir -p "$STAGING/usr/lib/grfics"
cp "$SCRIPT_DIR/ews/usr/lib/grfics/ews-init.sh" "$STAGING/usr/lib/grfics/"
chmod 755 "$STAGING/usr/lib/grfics/ews-init.sh"

# --- GRFICS workstation assets (shipped into /opt/grfics/ews) ---
# noVNC branding
mkdir -p "$STAGING/opt/grfics/ews/novnc-assets"
cp "$REPO_ROOT/workstation/index.html" "$STAGING/opt/grfics/ews/novnc-assets/"
cp "$REPO_ROOT/workstation/shield.svg"  "$STAGING/opt/grfics/ews/novnc-assets/"

# Desktop project files
mkdir -p "$STAGING/opt/grfics/ews/desktop"
cp    "$REPO_ROOT/workstation/chemical.st" "$STAGING/opt/grfics/ews/desktop/"
cp -r "$REPO_ROOT/workstation/chemical"    "$STAGING/opt/grfics/ews/desktop/"

# Firefox bookmarks
mkdir -p "$STAGING/opt/grfics/ews/firefox"
cp "$REPO_ROOT/workstation/places.sqlite" "$STAGING/opt/grfics/ews/firefox/"

# --- Build ---
mkdir -p "$DIST"
dpkg-deb --build --root-owner-group "$STAGING" "$DIST/${PKG_NAME}.deb"

echo ""
echo "Package built: $DIST/${PKG_NAME}.deb"
dpkg-deb -I "$DIST/${PKG_NAME}.deb"
