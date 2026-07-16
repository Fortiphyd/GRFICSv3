FROM debian:12-slim

# Install required tools
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    iproute2 iputils-ping iptables nano procps tcpdump curl \
    python3 python3-flask ulogd2 ulogd2-json dnsmasq wireguard-tools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /var/log/flask /var/log/dnsmasq


RUN echo "deb http://deb.debian.org/debian bookworm-backports main" \
      > /etc/apt/sources.list.d/backports.list && \
    apt-get update && \
    apt-get install -y supervisor && \
    apt-get install -y -t bookworm-backports suricata && \
    mkdir -p /var/log/supervisor && \
    rm -rf /var/lib/apt/lists/*



# Enable IP forwarding
RUN echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf

# Fake systemctl so wazuh-agent postinstall doesn't fail
RUN printf '#!/bin/bash\necho "[fake-systemctl] $@"\nexit 0\n' \
    > /usr/local/bin/systemctl && chmod +x /usr/local/bin/systemctl

# Install Wazuh agent
RUN apt-get update && apt-get install -y --no-install-recommends gnupg \
    && curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH \
       | gpg --no-default-keyring \
         --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import \
    && chmod 644 /usr/share/keyrings/wazuh.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] \
       https://packages.wazuh.com/4.x/apt/ stable main" \
       > /etc/apt/sources.list.d/wazuh.list \
    && apt-get update \
    && WAZUH_MANAGER=192.168.90.20 WAZUH_AGENT_NAME=router apt-get install -y wazuh-agent \
    && rm -rf /var/lib/apt/lists/*

# Tell the agent to monitor Suricata alerts-only EVE log
RUN sed -i 's|</ossec_config>|<localfile>\n    <log_format>json</log_format>\n    <location>/var/log/suricata/alerts.json</location>\n  </localfile>\n</ossec_config>|' \
    /var/ossec/etc/ossec.conf

COPY entrypoint.sh /entrypoint.sh
COPY app.py /opt/fwui/app.py
COPY login.html /opt/fwui/templates/login.html
COPY firewall.html /opt/fwui/templates/firewall.html
COPY nat.html /opt/fwui/templates/nat.html
COPY firewall_logs.html /opt/fwui/templates/firewall_logs.html
COPY ids.html /opt/fwui/templates/ids.html
COPY dashboard.html /opt/fwui/templates/dashboard.html
COPY states.html /opt/fwui/templates/states.html
COPY dns.html /opt/fwui/templates/dns.html
COPY wireguard.html /opt/fwui/templates/wireguard.html
COPY vpn_tunnel.html /opt/fwui/templates/vpn_tunnel.html
COPY settings.html /opt/fwui/templates/settings.html
COPY interfaces.html /opt/fwui/templates/interfaces.html
COPY arp.html /opt/fwui/templates/arp.html
COPY diagnostics.html /opt/fwui/templates/diagnostics.html
COPY base.html /opt/fwui/templates/base.html
COPY arpmon.py /opt/fwui/arpmon.py
COPY static/ /opt/fwui/static/
COPY router.conf /etc/supervisor/conf.d/router.conf
COPY suricata.yaml /etc/suricata/suricata.yaml
COPY dnsmasq.conf /etc/dnsmasq.conf
COPY usr/lib/grfics/network-init.py /usr/lib/grfics/network-init.py
COPY usr/lib/grfics/suricata-start.sh /usr/lib/grfics/suricata-start.sh
RUN chmod +x /usr/lib/grfics/suricata-start.sh

COPY quickdraw.rules /etc/suricata/rules/quickdraw.rules
COPY ulogd.conf /etc/ulogd.conf


RUN chmod +x /entrypoint.sh

ARG BUILD_VERSION=unknown
ARG BUILD_CREATED=unknown
LABEL org.opencontainers.image.version="$BUILD_VERSION" \
      org.opencontainers.image.revision="$BUILD_VERSION" \
      org.opencontainers.image.created="$BUILD_CREATED" \
      com.grfics.service="router"
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]

ENTRYPOINT ["/entrypoint.sh"]
