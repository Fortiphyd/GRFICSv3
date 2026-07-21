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

echo "[*] Ensuring prc_alarms_notify exists..."
PROC_EXISTS=$(mariadb -uscada -pscada scadalts -N -B -e \
  "SELECT COUNT(*) FROM information_schema.ROUTINES
   WHERE ROUTINE_SCHEMA='scadalts' AND ROUTINE_TYPE='PROCEDURE'
     AND ROUTINE_NAME='prc_alarms_notify';" 2>/dev/null || echo 0)

echo "[*] Ensuring admin user is set up right"
mariadb -uscada -pscada scadalts <<-EOSQL
  INSERT INTO users
    (id, username, password, email, phone, disabled, admin, receiveAlarmEmails, receiveOwnAuditEvents, homeURL)
  SELECT
    4, 'admin', '0DPiKuNIrrVmD8IUCuw1hQxNqZc=', 'admin@example.com', '', 'N', 'Y', 0, 0, '/views.shtm#'
  WHERE NOT EXISTS (SELECT 1 FROM users WHERE username='admin');
EOSQL

ip route add 192.168.95.0/24 via 192.168.90.200 || true

# Wait for ScadaLTS/Tomcat to finish starting so Flyway migrations have run
# before we import seed data (migrations add columns the seed depends on).
echo "[*] Waiting for ScadaLTS to be ready..."
until curl -sf http://localhost:8080/ &>/dev/null; do
  sleep 5
done

# Seed project
VIEW_COUNT=$(mariadb -uscada -pscada scadalts -N -B -e "SELECT COUNT(*) FROM mangoViews;" 2>/dev/null || echo 0)
if [ "$VIEW_COUNT" -eq 0 ] && [ -f /seed_project_data.sql ]; then
  echo "[*] Seeding project data..."
  mariadb -uscada -pscada scadalts < /seed_project_data.sql
  echo "[*] Project import complete."
  echo "[*] Restarting Tomcat to load seeded data..."
  supervisorctl restart tomcat
else
  echo "[*] Skipping project seed (views table already has entries)."
fi

exit 0
