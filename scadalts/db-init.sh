#!/bin/bash
set -e

echo "[*] Waiting for MariaDB..."
until mariadb -uroot -e "SELECT 1;" &> /dev/null; do
    sleep 2
done

echo "[*] Creating database and user..."
mariadb -uroot <<-EOSQL
    CREATE DATABASE IF NOT EXISTS scadalts;
    CREATE USER IF NOT EXISTS 'scada'@'%' IDENTIFIED BY 'scada';
    GRANT ALL PRIVILEGES ON scadalts.* TO 'scada'@'%';
    FLUSH PRIVILEGES;
EOSQL

echo "[*] Checking if schema exists..."
if [ "$(mariadb -uscada -pscada scadalts -N -B -e 'show tables;' | wc -l)" -eq 0 ]; then
    echo "[*] Importing SCADA-LTS schema..."
    mariadb -uscada -pscada scadalts < /usr/local/tomcat/webapps/ROOT/WEB-INF/db/createTables-mysql.sql

echo "[*] Inserting default admin user..."
mariadb -uscada -pscada scadalts <<-EOSQL
    INSERT INTO users
    (id, username, password, email, phone, disabled, admin, receiveAlarmEmails, receiveOwnAuditEvents)
    VALUES
    (4, 'admin', '0DPiKuNIrrVmD8IUCuw1hQxNqZc=', 'admin@example.com', '', 'N', 'Y', 0, 0);
EOSQL

    echo "[*] Schema and default user import complete."
else
    echo "[*] Schema already present, skipping import."
fi

# --- New bit for seeding project ---
VIEW_COUNT=$(mariadb -uscada -pscada scadalts -N -B -e "SELECT COUNT(*) FROM views;" 2>/dev/null || echo 0)

if [ "$VIEW_COUNT" -eq 0 ] && [ -f /seed_project.sql ]; then
    echo "[*] Seeding project data..."
    mariadb -uscada -pscada scadalts < /seed_project.sql
    echo "[*] Project import complete."
else
    echo "[*] Skipping project seed (views table already has entries)."
fi


exit 0
