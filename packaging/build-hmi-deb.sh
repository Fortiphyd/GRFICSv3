#!/bin/bash
# Build dependencies (must be installed on build machine):
#   apt install wget unzip openjdk-11-jdk
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TOMCAT_VERSION="9.0.109"
SCADALTS_VERSION="2.7.8.1"
MYSQL_CONNECTOR_VERSION="8.3.0"

VERSION=$(git -C "$REPO_ROOT" describe --tags --always 2>/dev/null \
    | sed 's/^v//' \
    | sed 's/-\([0-9]*\)-g/+\1+g/')
echo "Building grfics-hmi version: $VERSION"

PKG_NAME="grfics-hmi_${VERSION}_amd64"
STAGING="$SCRIPT_DIR/dist/staging/$PKG_NAME"
DIST="$SCRIPT_DIR/dist"
CACHE="$SCRIPT_DIR/dist/hmi-cache"

mkdir -p "$CACHE" "$DIST"

# --- Download / cache Tomcat ---
TOMCAT_TAR="$CACHE/apache-tomcat-${TOMCAT_VERSION}.tar.gz"
if [ ! -f "$TOMCAT_TAR" ]; then
    echo "Downloading Tomcat ${TOMCAT_VERSION}..."
    wget -q "https://archive.apache.org/dist/tomcat/tomcat-9/v${TOMCAT_VERSION}/bin/apache-tomcat-${TOMCAT_VERSION}.tar.gz" \
         -O "$TOMCAT_TAR"
fi

# --- Download / cache ScadaLTS WAR ---
SCADALTS_WAR="$CACHE/Scada-LTS-${SCADALTS_VERSION}.war"
if [ ! -f "$SCADALTS_WAR" ]; then
    echo "Downloading ScadaLTS ${SCADALTS_VERSION}..."
    wget -q "https://github.com/SCADA-LTS/Scada-LTS/releases/download/v${SCADALTS_VERSION}/Scada-LTS.war" \
         -O "$SCADALTS_WAR"
fi

# --- Download / cache MySQL JDBC driver ---
CONNECTOR_JAR="$CACHE/mysql-connector-j-${MYSQL_CONNECTOR_VERSION}.jar"
if [ ! -f "$CONNECTOR_JAR" ]; then
    echo "Downloading MySQL Connector/J ${MYSQL_CONNECTOR_VERSION}..."
    TMP_TAR="$CACHE/mysql-connector-j.tar.gz"
    wget -q "https://dev.mysql.com/get/Downloads/Connector-J/mysql-connector-j-${MYSQL_CONNECTOR_VERSION}.tar.gz" \
         -O "$TMP_TAR"
    tar xzf "$TMP_TAR" -C "$CACHE" \
        "mysql-connector-j-${MYSQL_CONNECTOR_VERSION}/mysql-connector-j-${MYSQL_CONNECTOR_VERSION}.jar" \
        --strip-components=1
    rm "$TMP_TAR"
fi

# --- Set up staging directory ---
rm -rf "$STAGING"
mkdir -p "$STAGING"

# --- DEBIAN control files ---
cp -r "$SCRIPT_DIR/hmi/DEBIAN" "$STAGING/DEBIAN"
sed -i "s/^Version:.*/Version: $VERSION/" "$STAGING/DEBIAN/control"
chmod 755 "$STAGING/DEBIAN/postinst" "$STAGING/DEBIAN/prerm"

# --- Extract and configure Tomcat ---
echo "Extracting Tomcat..."
TOMCAT_STAGING="$STAGING/usr/local/tomcat"
mkdir -p "$TOMCAT_STAGING"
tar xzf "$TOMCAT_TAR" -C "$TOMCAT_STAGING" --strip-components=1

# Apply pre-modified context.xml (adds JNDI DataSource for ScadaLTS)
cp "$SCRIPT_DIR/hmi/tomcat/conf/context.xml" "$TOMCAT_STAGING/conf/context.xml"

# Add MySQL JDBC driver
cp "$CONNECTOR_JAR" "$TOMCAT_STAGING/lib/"

# Extract ScadaLTS WAR as ROOT webapp
echo "Extracting ScadaLTS WAR..."
mkdir -p "$TOMCAT_STAGING/webapps/ROOT"
unzip -q "$SCADALTS_WAR" -d "$TOMCAT_STAGING/webapps/ROOT"

# Static uploads directory (for HMI image assets)
mkdir -p "$TOMCAT_STAGING/static/uploads"
cp "$REPO_ROOT/scadalts/1.png" "$TOMCAT_STAGING/static/uploads/1.png"

# --- Seed data and scripts ---
mkdir -p "$STAGING/opt/grfics/hmi"
cp "$REPO_ROOT/scadalts/seed_project_data.sql" "$STAGING/opt/grfics/hmi/seed_project_data.sql"

# --- Init script ---
mkdir -p "$STAGING/usr/lib/grfics"
cp "$SCRIPT_DIR/hmi/usr/lib/grfics/hmi-init.sh" "$STAGING/usr/lib/grfics/"
chmod 755 "$STAGING/usr/lib/grfics/hmi-init.sh"

# --- Systemd units ---
mkdir -p "$STAGING/lib/systemd/system"
cp "$SCRIPT_DIR/hmi/systemd/"*.service "$STAGING/lib/systemd/system/"

# --- MariaDB config ---
mkdir -p "$STAGING/etc/mysql/conf.d"
cp "$SCRIPT_DIR/hmi/etc/mysql/conf.d/grfics-hmi.cnf" "$STAGING/etc/mysql/conf.d/"

# --- Build ---
dpkg-deb --build --root-owner-group "$STAGING" "$DIST/${PKG_NAME}.deb"

echo ""
echo "Package built: $DIST/${PKG_NAME}.deb"
dpkg-deb -I "$DIST/${PKG_NAME}.deb"
