# GRFICSv3 Zeek sensor - see docs/zeek-network-mirroring-design.md.
#
# Gets its traffic via a "mirror0" interface that only exists once an
# instructor runs enable-mirror.sh on the host (see that script) - normal
# Docker networking (a-grfics-admin, for shipping logs to Wazuh) is
# otherwise unused for traffic capture. This container needs no special
# network privileges/host networking of its own.
FROM zeek/zeek:9.0.0

RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor curl gnupg iproute2 git ca-certificates \
    && mkdir -p /var/log/supervisor \
    && rm -rf /var/lib/apt/lists/*

# OT protocol parsers - Zeek's own base analyzers only cover general IT
# protocols, so without these, Modbus (the lab's primary protocol) would
# only ever show up as plain TCP connections with no function
# codes/addresses/values. CISA's ICSNPP (github.com/cisagov/ICSNPP)
# is the standard set of Zeek OT protocol parsers; installing just the
# Modbus one for now since that's the only ICS protocol actually in use
# in this lab today - add more (dnp3, s7comm, enip, ...) if/when the lab
# does. --force skips zkg's interactive confirmation prompt (fine here,
# same trust model as any other apt/pip package this project already
# installs unattended at build time).
RUN zkg install --force zeek/cisagov/icsnpp-modbus

# Fake systemctl so wazuh-agent postinstall doesn't fail (matches the same
# trick in router/Dockerfile and scadalts/Dockerfile).
RUN printf '#!/bin/bash\necho "[fake-systemctl] $@"\nexit 0\n' \
    > /usr/local/bin/systemctl && chmod +x /usr/local/bin/systemctl

# Install Wazuh agent (matches router/Dockerfile's pattern).
RUN curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH \
    | gpg --no-default-keyring \
      --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import \
    && chmod 644 /usr/share/keyrings/wazuh.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] \
       https://packages.wazuh.com/4.x/apt/ stable main" \
       > /etc/apt/sources.list.d/wazuh.list \
    && apt-get update \
    && WAZUH_MANAGER=192.168.90.20 WAZUH_AGENT_NAME=zeek apt-get install -y wazuh-agent \
    && rm -rf /var/lib/apt/lists/*

# Ship Zeek's notice.log (the closest equivalent to Suricata's alerts.json)
# to Wazuh, same pipeline as the existing Suricata -> Wazuh integration.
# Agent-package ossec.conf has more than one </ossec_config> block (one per
# top-level config section) - "0,/re/{s/re/.../}" limits the substitution
# to just the first, avoiding a duplicated <localfile> entry.
RUN sed -i '0,/<\/ossec_config>/{s|</ossec_config>|<localfile>\n    <log_format>json</log_format>\n    <location>/usr/local/zeek/logs/notice.log</location>\n  </localfile>\n</ossec_config>|}' \
    /var/ossec/etc/ossec.conf

# rootcheck's "trojaned binary" signature check (check_trojans) is a
# generic, decades-old string-matching heuristic that false-positives on
# this image's coreutils/glibc build (Debian trixie) - confirmed genuinely
# false (fresh official image, zero chance of real compromise) and
# confirmed specific to this base (router/EWS/scadalts, on older bases,
# don't trip it). Other rootcheck checks (files/dev/sys/pids/ports/
# interfaces) stay on - just this one signature-based check is noise here.
RUN sed -i 's|<check_trojans>yes</check_trojans>|<check_trojans>no</check_trojans>|' \
    /var/ossec/etc/ossec.conf

COPY local.zeek /usr/local/zeek/share/zeek/site/local.zeek
COPY zeek-start.sh /usr/lib/grfics/zeek-start.sh
RUN chmod +x /usr/lib/grfics/zeek-start.sh
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

ARG BUILD_VERSION=unknown
ARG BUILD_CREATED=unknown
LABEL org.opencontainers.image.version="$BUILD_VERSION" \
      org.opencontainers.image.revision="$BUILD_VERSION" \
      org.opencontainers.image.created="$BUILD_CREATED" \
      com.grfics.service="zeek"

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
