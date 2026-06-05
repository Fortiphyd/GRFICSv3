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
TABLE_COUNT=$(mariadb -uscada -pscada scadalts -N -B -e "SHOW TABLES;" | wc -l)

if [ "$TABLE_COUNT" -eq 0 ]; then
  echo "[*] Importing SCADA-LTS base schema..."
  mariadb -uscada -pscada scadalts < /usr/local/tomcat/webapps/ROOT/WEB-INF/db/createTables-mysql.sql
  echo "[*] Base schema import complete."
else
  echo "[*] Schema already present, skipping base import."
fi

echo "[*] Ensuring admin user is set up right..."
mariadb -uscada -pscada scadalts <<-EOSQL
  INSERT INTO users
    (id, username, password, email, phone, disabled, admin, receiveAlarmEmails, receiveOwnAuditEvents, homeURL)
  SELECT
    4, 'admin', '0DPiKuNIrrVmD8IUCuw1hQxNqZc=', 'admin@example.com', '', 'N', 'Y', 0, 0, '/views.shtm#'
  WHERE NOT EXISTS (SELECT 1 FROM users WHERE username='admin');
EOSQL

VIEW_COUNT=$(mariadb -uscada -pscada scadalts -N -B -e "SELECT COUNT(*) FROM mangoViews;" 2>/dev/null || echo 0)
if [ "$VIEW_COUNT" -eq 0 ] && [ -f /opt/grfics/hmi/seed_project_data.sql ]; then
  echo "[*] Seeding project data..."
  mariadb -uscada -pscada scadalts < /opt/grfics/hmi/seed_project_data.sql
  echo "[*] Project import complete."
else
  echo "[*] Skipping project seed (views table already has entries)."
fi

ip route add 192.168.95.0/24 via 192.168.90.200 2>/dev/null || true

exit 0
