#!/bin/bash
# Build dependencies (must be installed on build machine):
#   apt install build-essential libjsoncpp-dev liblapacke-dev
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VERSION=$(git -C "$REPO_ROOT" describe --tags --always 2>/dev/null \
    | sed 's/^v//' \
    | sed 's/-\([0-9]*\)-g/+\1+g/')
echo "Building grfics-simulation version: $VERSION"

PKG_NAME="grfics-simulation_${VERSION}_amd64"
STAGING="$SCRIPT_DIR/dist/staging/$PKG_NAME"
DIST="$SCRIPT_DIR/dist"

# --- Compile C++ simulation binary ---
echo "Compiling simulation binary..."
BUILD_TMP="$SCRIPT_DIR/dist/simulation-build"
mkdir -p "$BUILD_TMP"
cp "$REPO_ROOT/simulation/simulation/main.cc" \
   "$REPO_ROOT/simulation/simulation/TE_process.cc" \
   "$REPO_ROOT/simulation/simulation/TE_process.h" \
   "$BUILD_TMP/"
g++ "$BUILD_TMP/main.cc" "$BUILD_TMP/TE_process.cc" \
    -ljsoncpp -llapacke -lpthread \
    -o "$BUILD_TMP/simulation"
echo "Compilation successful."

# --- Set up staging directory ---
rm -rf "$STAGING"
mkdir -p "$STAGING"

# --- DEBIAN control files ---
cp -r "$SCRIPT_DIR/simulation/DEBIAN" "$STAGING/DEBIAN"
sed -i "s/^Version:.*/Version: $VERSION/" "$STAGING/DEBIAN/control"
chmod 755 "$STAGING/DEBIAN/postinst" "$STAGING/DEBIAN/prerm"

# --- Web assets (excluding versions.php — Docker-specific) ---
mkdir -p "$STAGING/var/www/html"
cp -r "$REPO_ROOT/simulation/web_visualization/." "$STAGING/var/www/html/"
rm -f "$STAGING/var/www/html/versions.php"

# Inject VM overlay script before </body>
sed -i 's|</body>|<script src="/vm-overlay.js"></script></body>|' \
    "$STAGING/var/www/html/index.html"
cp "$SCRIPT_DIR/simulation/www/vm-overlay.js" "$STAGING/var/www/html/"

# --- Simulation binary ---
mkdir -p "$STAGING/app/simulation"
cp "$BUILD_TMP/simulation" "$STAGING/app/simulation/simulation"

# --- Modbus Python scripts ---
mkdir -p "$STAGING/app/modbus"
cp "$REPO_ROOT/simulation/simulation/remote_io/modbus/"* "$STAGING/app/modbus/"
chmod +x "$STAGING/app/modbus/run_all.sh"

# --- nginx config ---
mkdir -p "$STAGING/etc/nginx/sites-available"
cp "$SCRIPT_DIR/simulation/nginx/grfics-simulation" \
   "$STAGING/etc/nginx/sites-available/grfics-simulation"

# --- Systemd units ---
mkdir -p "$STAGING/lib/systemd/system"
cp "$SCRIPT_DIR/simulation/systemd/"*.service "$STAGING/lib/systemd/system/"

# --- Init script ---
mkdir -p "$STAGING/usr/lib/grfics"
cp "$SCRIPT_DIR/simulation/usr/lib/grfics/simulation-init.sh" \
   "$STAGING/usr/lib/grfics/"
chmod 755 "$STAGING/usr/lib/grfics/simulation-init.sh"

# --- Build ---
mkdir -p "$DIST"
dpkg-deb --build --root-owner-group "$STAGING" "$DIST/${PKG_NAME}.deb"

echo ""
echo "Package built: $DIST/${PKG_NAME}.deb"
dpkg-deb -I "$DIST/${PKG_NAME}.deb"
