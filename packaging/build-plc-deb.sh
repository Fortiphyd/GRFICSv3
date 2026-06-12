#!/bin/bash
# Build dependencies (must be installed on build machine):
#   apt install build-essential cmake bison flex autoconf automake libtool
#               make git sqlite3 curl python3 python3-venv
#
# IMPORTANT: This script compiles OpenPLC from source. It writes to /workdir/
# (a path hardcoded inside background_installer.sh) and installs shared
# libraries to /usr/local/lib/. Run as root or on a disposable machine
# (e.g. GitHub Actions). Compilation takes 5-10 minutes on first run.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root (OpenPLC installer requires it)."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VERSION=$(git -C "$REPO_ROOT" describe --tags --always 2>/dev/null \
    | sed 's/^v//' \
    | sed 's/-\([0-9]*\)-g/+\1+g/')
echo "Building grfics-plc version: $VERSION"

PKG_NAME="grfics-plc_${VERSION}_amd64"
STAGING="$SCRIPT_DIR/dist/staging/$PKG_NAME"
DIST="$SCRIPT_DIR/dist"

# /workdir is the path hardcoded in background_installer.sh's finalize_install().
# We must build there so the active_program_default path resolves correctly.
BUILD_DIR="/workdir"

# --- Prepare /workdir with OpenPLC source + GRFICS configs ---
echo "Setting up build directory at $BUILD_DIR..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

cp -r "$REPO_ROOT/plc/webserver"            "$BUILD_DIR/webserver"
cp -r "$REPO_ROOT/plc/utils"               "$BUILD_DIR/utils"
cp    "$REPO_ROOT/plc/install.sh"           "$BUILD_DIR/install.sh"
cp    "$REPO_ROOT/plc/background_installer.sh" "$BUILD_DIR/background_installer.sh"
find "$BUILD_DIR" -type f -name "*.sh" -exec chmod +x {} \;

# GRFICS-specific configs — copy as both live and *_default variants so the
# installer's finalize_install() compiles the right PLC program.
cp "$REPO_ROOT/plc/openplc.db"    "$BUILD_DIR/webserver/openplc.db"
cp "$REPO_ROOT/plc/openplc.db"    "$BUILD_DIR/webserver/openplc_default.db"
cp "$REPO_ROOT/plc/mbconfig.cfg"  "$BUILD_DIR/webserver/mbconfig.cfg"
cp "$REPO_ROOT/plc/mbconfig.cfg"  "$BUILD_DIR/webserver/mbconfig_default.cfg"
cp "$REPO_ROOT/plc/active_program" "$BUILD_DIR/webserver/active_program"
cp "$REPO_ROOT/plc/active_program" "$BUILD_DIR/webserver/active_program_default"
mkdir -p "$BUILD_DIR/webserver/st_files_default"
cp -r "$REPO_ROOT/plc/st_files/." "$BUILD_DIR/webserver/st_files_default/"
cp -r "$REPO_ROOT/plc/st_files"   "$BUILD_DIR/webserver/st_files"

# --- Run OpenPLC installer (docker mode: no systemd, no sudo wrapper) ---
echo "Running OpenPLC installer (this takes several minutes)..."
cd "$BUILD_DIR"
./install.sh docker
echo "OpenPLC installation complete."

# --- Set up staging directory ---
rm -rf "$STAGING"
mkdir -p "$STAGING"

# --- DEBIAN control files ---
cp -r "$SCRIPT_DIR/plc/DEBIAN" "$STAGING/DEBIAN"
sed -i "s/^Version:.*/Version: $VERSION/" "$STAGING/DEBIAN/control"
chmod 755 "$STAGING/DEBIAN/postinst" "$STAGING/DEBIAN/prerm"

# --- Copy compiled OpenPLC tree (excluding .venv and utils source) ---
echo "Copying compiled OpenPLC to staging..."
mkdir -p "$STAGING/opt/openplc"
rsync -a \
    --exclude='.venv' \
    --exclude='utils' \
    --exclude='swapfile' \
    "$BUILD_DIR/" "$STAGING/opt/openplc/"

# Replace the Docker-specific start script with the VM version
cat > "$STAGING/opt/openplc/start_openplc.sh" <<'EOF'
#!/bin/bash
cd /opt/openplc/webserver
exec /opt/openplc/.venv/bin/python3 webserver.py
EOF
chmod 755 "$STAGING/opt/openplc/start_openplc.sh"

# --- Bundle system libraries (not in Ubuntu 22.04 apt repos) ---
echo "Bundling shared libraries..."
mkdir -p "$STAGING/usr/local/lib"
cp /usr/local/lib/libmodbus.so*  "$STAGING/usr/local/lib/" 2>/dev/null || true
cp /usr/local/lib/libsnap7.so*   "$STAGING/usr/local/lib/" 2>/dev/null || true
find /usr/local/lib -maxdepth 1 -name 'libdnp3*.so*' \
    -exec cp {} "$STAGING/usr/local/lib/" \; 2>/dev/null || true

# --- ldconfig conf so the bundled libs are found at runtime ---
mkdir -p "$STAGING/etc/ld.so.conf.d"
cp "$SCRIPT_DIR/plc/etc/ld.so.conf.d/grfics-plc.conf" \
   "$STAGING/etc/ld.so.conf.d/grfics-plc.conf"

# --- Systemd units ---
mkdir -p "$STAGING/lib/systemd/system"
cp "$SCRIPT_DIR/plc/systemd/"*.service "$STAGING/lib/systemd/system/"

# --- Init script ---
mkdir -p "$STAGING/usr/lib/grfics"
cp "$SCRIPT_DIR/plc/usr/lib/grfics/plc-init.sh" "$STAGING/usr/lib/grfics/"
chmod 755 "$STAGING/usr/lib/grfics/plc-init.sh"

# --- Build ---
mkdir -p "$DIST"
dpkg-deb --build --root-owner-group "$STAGING" "$DIST/${PKG_NAME}.deb"

echo ""
echo "Package built: $DIST/${PKG_NAME}.deb"
dpkg-deb -I "$DIST/${PKG_NAME}.deb"
