#!/bin/bash
# Build dependencies (must be installed on build machine):
#   apt install dpkg-dev
#
# This is a thin package — no downloads or compilation at build time.
# postinst clones Caldera + submodules, builds the magma UI, compiles sandcat
# agents, and installs Python deps. Expect 20-30 minutes on first install.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VERSION=$(git -C "$REPO_ROOT" describe --tags --always 2>/dev/null \
    | sed 's/^v//' \
    | sed 's/-\([0-9]*\)-g/+\1+g/')
echo "Building grfics-caldera version: $VERSION"

PKG_NAME="grfics-caldera_${VERSION}_amd64"
STAGING="$SCRIPT_DIR/dist/staging/$PKG_NAME"
DIST="$SCRIPT_DIR/dist"

# --- Set up staging directory ---
rm -rf "$STAGING"
mkdir -p "$STAGING"

# --- DEBIAN control files ---
cp -r "$SCRIPT_DIR/caldera/DEBIAN" "$STAGING/DEBIAN"
sed -i "s/^Version:.*/Version: $VERSION/" "$STAGING/DEBIAN/control"
chmod 755 "$STAGING/DEBIAN/postinst" "$STAGING/DEBIAN/prerm"

# --- Systemd units ---
mkdir -p "$STAGING/lib/systemd/system"
cp "$SCRIPT_DIR/caldera/systemd/"*.service "$STAGING/lib/systemd/system/"

# --- Init script ---
mkdir -p "$STAGING/usr/lib/grfics"
cp "$SCRIPT_DIR/caldera/usr/lib/grfics/caldera-init.sh" "$STAGING/usr/lib/grfics/"
chmod 755 "$STAGING/usr/lib/grfics/caldera-init.sh"

# --- GRFICS-specific Caldera assets ---
ASSETS="$STAGING/opt/grfics/caldera"
mkdir -p "$ASSETS"

# Caldera local config (API keys, enabled plugins, credentials)
mkdir -p "$ASSETS/conf"
cp "$REPO_ROOT/caldera/local.yml" "$ASSETS/conf/local.yml"

# GRFICS adversary definition
mkdir -p "$ASSETS/adversaries"
cp "$REPO_ROOT/caldera/ff2effd0-6938-4705-801c-8e4dcbfbf452.yml" \
   "$ASSETS/adversaries/"

# Modbus discovery ability
mkdir -p "$ASSETS/abilities"
cp "$REPO_ROOT/caldera/9360ba0d-46a3-47a1-bbe6-e6c875790500.yml" \
   "$ASSETS/abilities/"

# Modbus sample facts source
mkdir -p "$ASSETS/sources"
cp "$REPO_ROOT/caldera/0033b644-a615-4eff-bcf3-178e9b17adc3.yml" \
   "$ASSETS/sources/"

# Modbus plugin customisations + pre-compiled payload binary
mkdir -p "$ASSETS/modbus"
cp "$REPO_ROOT/caldera/spec.py"         "$ASSETS/modbus/"
cp "$REPO_ROOT/caldera/modbus_cli.py"   "$ASSETS/modbus/"
cp "$REPO_ROOT/caldera/modbus_cli"      "$ASSETS/modbus/"
cp "$REPO_ROOT/caldera/modbus_cli.spec" "$ASSETS/modbus/"

# --- Build ---
mkdir -p "$DIST"
dpkg-deb --build --root-owner-group "$STAGING" "$DIST/${PKG_NAME}.deb"

echo ""
echo "Package built: $DIST/${PKG_NAME}.deb"
dpkg-deb -I "$DIST/${PKG_NAME}.deb"
