FROM debian:bullseye-20240722 AS base

COPY install.sh /workdir/
COPY background_installer.sh /workdir/
COPY utils /workdir/utils/
COPY webserver /workdir/webserver/

WORKDIR /workdir

RUN find . -type f -name "*.sh" -exec chmod +x {} \;

# bullseye is EOL: deb.debian.org no longer serves a valid (non-expired)
# bullseye-security Release file. Point at the archive mirror instead, which
# freezes EOL releases with stable metadata; archive.debian.org doesn't
# publish security updates for archived releases at all, so drop that line
# rather than point it somewhere that will also go stale.
RUN sed -i 's|deb.debian.org|archive.debian.org|g; /security/d' /etc/apt/sources.list

# 1. Install dependencies (runs once, cached unless package list changes)

RUN apt-get update && apt-get install -y \
      python3 python3-venv python3-pip sqlite3 \
      build-essential git dos2unix autoconf automake libtool m4 gettext \
      && find utils/ -type f -exec dos2unix {} \; \
      && cd utils/matiec_src && rm -f config/missing \
      && autoreconf --install --force --verbose \
      && rm -rf /var/lib/apt/lists/*

RUN ./install.sh docker

# 2. Copy static configs and scripts that rarely change
COPY webserver/dnp3.cfg /workdir/webserver/dnp3_default.cfg

# 3. Set up volume and symlinks
RUN mkdir -p /docker_persistent \
    && touch /docker_persistent/persistent.file \
    && ln -sf /docker_persistent/mbconfig.cfg /workdir/webserver/mbconfig.cfg \
    && ln -sf /docker_persistent/persistent.file /workdir/webserver/persistent.file \
    && ln -sf /docker_persistent/openplc.db /workdir/webserver/openplc.db \
    && ln -sf /docker_persistent/dnp3.cfg /workdir/webserver/dnp3.cfg \
    && ln -sf /docker_persistent/st_files /workdir/webserver/st_files \
    && ln -sf /docker_persistent/active_program /workdir/webserver/active_program

VOLUME /docker_persistent


# ---- Second stage for your custom program/configs ----
FROM base AS openplc-custom

WORKDIR /workdir

# Copy only the files that change frequently
COPY mbconfig.cfg /workdir/webserver/mbconfig_default.cfg
COPY openplc.db /workdir/webserver/openplc_default.db
COPY active_program /workdir/webserver/active_program
COPY active_program /workdir/webserver/active_program_default
COPY st_files/ /workdir/webserver/st_files_default/
COPY st_files/ /workdir/webserver/st_files/

#RUN python3 /workdir/webserver/startup_fix.py


RUN apt-get update && apt-get install -y \
      net-tools \
      && rm -rf /var/lib/apt/lists/* \
    && ./install.sh docker

# ENTRYPOINT at the very end (fast to change)
ARG BUILD_VERSION=unknown
ARG BUILD_CREATED=unknown
LABEL org.opencontainers.image.version="$BUILD_VERSION" \
      org.opencontainers.image.revision="$BUILD_VERSION" \
      org.opencontainers.image.created="$BUILD_CREATED" \
      com.grfics.service="plc"
ENTRYPOINT ["/workdir/start_openplc.sh"]