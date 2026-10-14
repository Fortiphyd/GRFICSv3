#!/bin/bash
set -e

FIRST_RUN_FLAG="/var/lib/wazuh-indexer/.initialized"

echo "[wazuh] Adding route to ICS network..."
ip route add 192.168.95.0/24 via 192.168.90.200 2>/dev/null || true

echo "[wazuh] Starting wazuh-indexer..."
su -s /bin/bash wazuh-indexer \
    -c "OPENSEARCH_JAVA_OPTS='-Xms512m -Xmx512m' OPENSEARCH_PATH_CONF=/etc/wazuh-indexer /usr/share/wazuh-indexer/bin/opensearch" &

echo "[wazuh] Waiting for wazuh-indexer to be ready..."
until curl -sk https://localhost:9200 -u admin:admin --output /dev/null 2>/dev/null; do
    sleep 5
done
echo "[wazuh] wazuh-indexer is ready."

if [ ! -f "$FIRST_RUN_FLAG" ]; then
    echo "[wazuh] First run: initializing indexer security..."
    /usr/share/wazuh-indexer/bin/indexer-security-init.sh
    touch "$FIRST_RUN_FLAG"
fi

echo "[wazuh] Pushing wazuh-alerts index template..."
until curl -sk -X PUT "https://localhost:9200/_template/wazuh-alerts-4.x" \
    -u admin:admin \
    -H "Content-Type: application/json" \
    -d @/etc/wazuh-indexer/wazuh-template.json 2>/dev/null \
    | grep -q '"acknowledged":true'; do
    echo "[wazuh] Template push not acknowledged yet, retrying in 5s..."
    sleep 5
done
echo "[wazuh] Template pushed."

echo "[wazuh] Pushing index retention policy (7 days)..."
curl -sk -X PUT "https://localhost:9200/_plugins/_ism/policies/wazuh-alerts-retention" \
    -u admin:admin -H "Content-Type: application/json" -d '{
  "policy": {
    "description": "Delete wazuh-alerts indices older than 7 days",
    "default_state": "active",
    "states": [{
      "name": "active",
      "transitions": [{
        "state_name": "delete",
        "conditions": { "min_index_age": "7d" }
      }]
    }, {
      "name": "delete",
      "actions": [{ "delete": {} }],
      "transitions": []
    }],
    "ism_template": [{ "index_patterns": ["wazuh-alerts-*"], "priority": 100 }]
  }
}' 2>/dev/null | grep -q '"policy_id"' && echo "[wazuh] Retention policy set." || echo "[wazuh] Retention policy already exists or failed."

echo "[wazuh] Setting indexer credentials in keystore..."
echo 'admin' | /var/ossec/bin/wazuh-keystore -f indexer -k username
echo 'admin' | /var/ossec/bin/wazuh-keystore -f indexer -k password

echo "[wazuh] Patching ossec.conf indexer connection and syslog input..."
sed -i \
    -e 's|https://0\.0\.0\.0:9200|https://localhost:9200|g' \
    -e 's|/etc/filebeat/certs/root-ca\.pem|/etc/wazuh-indexer/certs/root-ca.pem|g' \
    -e 's|/etc/filebeat/certs/filebeat\.pem|/etc/wazuh-indexer/certs/admin.pem|g' \
    -e 's|/etc/filebeat/certs/filebeat-key\.pem|/etc/wazuh-indexer/certs/admin-key.pem|g' \
    /var/ossec/etc/ossec.conf

# Add syslog remote input — idempotent: remove any existing copies, then insert once
python3 - <<'PYEOF'
import re
conf = '/var/ossec/etc/ossec.conf'
with open(conf) as f:
    txt = f.read()
# Strip all existing syslog remote blocks
txt = re.sub(r'\s*<remote>\s*<connection>syslog</connection>.*?</remote>', '', txt, flags=re.DOTALL)
syslog_block = """
  <remote>
    <connection>syslog</connection>
    <port>514</port>
    <protocol>udp</protocol>
    <allowed-ips>0.0.0.0/0</allowed-ips>
  </remote>
</ossec_config>"""
# Replace the last </ossec_config> with the block
idx = txt.rfind('</ossec_config>')
if idx != -1:
    txt = txt[:idx] + syslog_block
with open(conf, 'w') as f:
    f.write(txt)
PYEOF

echo "[wazuh] Starting wazuh-manager..."
# /var/ossec is a persisted volume, so PID files from the previous container
# survive a `docker compose down`/`up`. Nothing from the old container can
# still be running in this fresh one, but wazuh-control only checks whether
# each recorded PID is alive - and PIDs restart low in a new container, so a
# stale file can match an unrelated new process. Seen live: a leftover
# wazuh-db-552.pid matched the new wazuh-apid (also PID 552), so wazuh-db was
# reported "running" and never started, every daemon failed on queue/db/wdb,
# all agents showed Unknown, and no alerts were processed.
rm -f /var/ossec/var/run/*.pid
# GRFICS rules/decoders ship outside the persisted volume (see Dockerfile) -
# install the image's current versions every start so rebuilds take effect.
install -o wazuh -g wazuh -m 660 /opt/grfics/wazuh/local_rules.xml /var/ossec/etc/rules/local_rules.xml
install -o wazuh -g wazuh -m 660 /opt/grfics/wazuh/local_decoder.xml /var/ossec/etc/decoders/local_decoder.xml
/var/ossec/bin/wazuh-control start

echo "[wazuh] Starting alerts indexer..."
python3 /usr/local/bin/alerts-indexer.py >> /var/log/alerts-indexer.log 2>&1 &

echo "[wazuh] Starting wazuh-dashboard..."
su -s /bin/bash wazuh-dashboard \
    -c "OSD_PATH_CONF=/etc/wazuh-dashboard /usr/share/wazuh-dashboard/bin/opensearch-dashboards" &

echo "[wazuh] All services started. Dashboard at http://localhost:5601"
exec tail -f /var/ossec/logs/ossec.log
