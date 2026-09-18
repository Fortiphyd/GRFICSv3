FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# Fake systemctl so dpkg postinstall scripts don't fail trying to start services
RUN printf '#!/bin/bash\necho "[fake-systemctl] $@"\nexit 0\n' \
    > /usr/local/bin/systemctl && chmod +x /usr/local/bin/systemctl

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg lsb-release sudo iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Add Wazuh apt repository
RUN curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH \
    | gpg --no-default-keyring \
      --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import \
    && chmod 644 /usr/share/keyrings/wazuh.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] \
       https://packages.wazuh.com/4.x/apt/ stable main" \
    > /etc/apt/sources.list.d/wazuh.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    wazuh-indexer wazuh-manager wazuh-dashboard \
    && rm -rf /var/lib/apt/lists/*

# Generate SSL certs using wazuh-certs-tool — pure openssl, no running services needed
# The tool looks for config.yml in its working directory
COPY config.yml /root/config.yml
RUN cd /root \
    && curl -sO https://packages.wazuh.com/4.14/wazuh-certs-tool.sh \
    && bash ./wazuh-certs-tool.sh -A \
    && rm wazuh-certs-tool.sh

# Distribute certs to each component's config directory
RUN mkdir -p /etc/wazuh-indexer/certs /etc/wazuh-dashboard/certs \
    && cp /root/wazuh-certificates/root-ca.pem          /etc/wazuh-indexer/certs/ \
    && cp /root/wazuh-certificates/wazuh.pem             /etc/wazuh-indexer/certs/indexer.pem \
    && cp /root/wazuh-certificates/wazuh-key.pem        /etc/wazuh-indexer/certs/indexer-key.pem \
    && cp /root/wazuh-certificates/admin.pem            /etc/wazuh-indexer/certs/ \
    && cp /root/wazuh-certificates/admin-key.pem        /etc/wazuh-indexer/certs/ \
    && cp /root/wazuh-certificates/root-ca.pem          /etc/wazuh-dashboard/certs/ \
    && cp /root/wazuh-certificates/wazuh-dashboard.pem      /etc/wazuh-dashboard/certs/ \
    && cp /root/wazuh-certificates/wazuh-dashboard-key.pem  /etc/wazuh-dashboard/certs/ \
    && chown -R wazuh-indexer:wazuh-indexer     /etc/wazuh-indexer/certs \
    && chown -R wazuh-dashboard:wazuh-dashboard /etc/wazuh-dashboard/certs \
    && chmod +x /etc/init.d/wazuh-indexer

COPY opensearch.yml            /etc/wazuh-indexer/opensearch.yml
COPY opensearch_dashboards.yml /etc/wazuh-dashboard/opensearch_dashboards.yml

# Bake in the alerts index template (normally pushed by filebeat in a standard install)
RUN curl -s https://raw.githubusercontent.com/wazuh/wazuh/v4.14.4/extensions/elasticsearch/7.x/wazuh-template.json \
    -o /etc/wazuh-indexer/wazuh-template.json

# Agent containers in this lab (router, scadalts, EWS, zeek, ...) have no
# persistent volume of their own, so every `docker compose up`/recreate
# loses their client.keys and forces a fresh enrollment - but
# wazuh_manager_data *is* a persistent volume, so the manager still
# remembers the old registration under the same name and rejects the new
# one as a duplicate by default. Two changes needed together to make
# re-enrollment actually work automatically instead of requiring a manual
# `manage_agents -r`:
#   - authd's <force> block allows replacing a same-named agent instead of
#     rejecting it, but only once the manager considers the old one
#     disconnected.
#   - agents_disconnection_time (default 15m) is how long that takes -
#     15m is reasonable for a real always-on deployment, but far too slow
#     for how often containers get recreated in this lab during normal
#     development/testing. agents_disconnection_alert_time is already 0
#     (disabled) in the package default, so shortening this doesn't add
#     alert noise, just updates agent status bookkeeping faster.
# Verified live against the real stack: without both changes, a recreated
# agent container gets stuck retrying "Duplicate agent name" forever.
RUN sed -i 's|</auth>|<force>\n      <enabled>yes</enabled>\n      <key_mismatch>yes</key_mismatch>\n      <disconnected_time enabled="yes">0s</disconnected_time>\n      <after_registration_time>0s</after_registration_time>\n    </force>\n  </auth>|' \
    /var/ossec/etc/ossec.conf \
    && sed -i 's|<agents_disconnection_time>15m</agents_disconnection_time>|<agents_disconnection_time>30s</agents_disconnection_time>|' \
    /var/ossec/etc/ossec.conf

# Rules to turn collected Zeek/Modbus events into visible alerts - without
# these, notice.log/modbus_detailed.log get received and silently dropped
# (see docs/zeek-network-mirroring-design.md).
COPY local_rules.xml /var/ossec/etc/rules/local_rules.xml

COPY entrypoint.sh /entrypoint.sh
COPY alerts-indexer.py /usr/local/bin/alerts-indexer.py
RUN chmod +x /entrypoint.sh

# 1514/1515: agent comms, 514/udp: syslog, 55000: REST API, 5601: dashboard
EXPOSE 1514 1515 514/udp 55000 5601
ARG BUILD_VERSION=unknown
ARG BUILD_CREATED=unknown
LABEL org.opencontainers.image.version="$BUILD_VERSION" \
      org.opencontainers.image.revision="$BUILD_VERSION" \
      org.opencontainers.image.created="$BUILD_CREATED" \
      com.grfics.service="wazuh"
ENTRYPOINT ["/entrypoint.sh"]
