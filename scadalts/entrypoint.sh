#!/bin/bash
set -e

echo "[*] Starting MariaDB temporarily..."
mysqld_safe --datadir=/var/lib/mysql --skip-networking &
pid="$!"

# Wait for DB to be ready
until mysqladmin ping --silent; do
    echo "Waiting for MariaDB..."
    sleep 2
done

# Run init scripts if DB empty
if [ ! -d "/var/lib/mysql/${MYSQL_DATABASE}" ]; then
    echo "[*] Initializing database..."
    mysql -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';"
    mysql -u root -p"${MYSQL_ROOT_PASSWORD}" < /docker-entrypoint-initdb.d/init.sql
    echo "[*] Database initialized."
fi

# Stop temporary mysqld
kill "$pid"
wait "$pid" || true

route add -net 192.168.95.0/24 gw 192.168.90.200

echo "[*] Handing over to supervisord..."
exec /usr/bin/supervisord -n
