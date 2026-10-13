# ---- Stage 1: Build stage ----
FROM python:3.11-slim@sha256:7a3ed1226224bcc1fe5443262363d42f48cf832a540c1836ba8ccbeaadf8637c as build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjsoncpp-dev \
    liblapacke-dev \ 
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY ./simulation ./simulation
WORKDIR /build/simulation
RUN make


# ---- Stage 2: Runtime image ----
FROM python:3.11-slim@sha256:7a3ed1226224bcc1fe5443262363d42f48cf832a540c1836ba8ccbeaadf8637c
# Install runtime libraries and network tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjsoncpp25 \
    liblapacke \
    iproute2 \
    net-tools \
    procps \
    nginx \
    php \
    php-fpm \
    php-cgi \
    tcpdump \
    nano \
    curl \
    ncat \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY ./web_visualization /var/www/html/
COPY ./nginx_config /etc/nginx/sites-enabled/default
RUN chown -R www-data:www-data /var/www/
#RUN chmod +x /var/www/html/data/index.php

RUN set -e; \
    echo "Checking for Git LFS pointer files..."; \
    if grep -R --binary-files=without-match -n "version https://git-lfs.github.com/spec/v1" /var/www/html/Build 2>/dev/null; then \
      echo ""; \
      echo "ERROR: Git LFS files not present (pointer files detected)."; \
      echo "Install git-lfs, then run: git lfs pull"; \
      echo "Then try building again"; \
      exit 1; \
    fi


# Set working directory
WORKDIR /app

# Copy compiled binary from build stage
COPY --from=build /build/simulation/simulation ./simulation/simulation

# Copy the Modbus scripts
COPY ./simulation/remote_io/modbus ./modbus

# Ambient noise-floor scheduler (see noise_floor/scheduler.py). The
# scheduler itself runs as root (supervisord), but its shared state file
# also needs to be writable by php-fpm's www-data worker processes
# (index.php writes noise_floor_* fields there) - world-writable on this
# one small directory is simplest and fine for a lab environment.
COPY ./noise_floor /app/noise_floor
RUN chmod 777 /app/noise_floor

# Copy your custom interfaces file and entrypoint script
COPY interfaces /etc/network/interfaces
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Optional: install Python requirements
RUN pip install --upgrade pip && pip install --no-cache-dir pymodbus==3.9.2

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN find . -type f -name "*.sh" -exec chmod +x {} \;

# Use custom entrypoint to bring up interfaces before running services
ARG BUILD_VERSION=unknown
ARG BUILD_CREATED=unknown
LABEL org.opencontainers.image.version="$BUILD_VERSION" \
      org.opencontainers.image.revision="$BUILD_VERSION" \
      org.opencontainers.image.created="$BUILD_CREATED" \
      com.grfics.service="simulation"
RUN printf '{"version":"%s","created":"%s"}\n' "$BUILD_VERSION" "$BUILD_CREATED" \
    > /etc/grfics-release
ENTRYPOINT ["/entrypoint.sh"]

CMD ["/usr/bin/supervisord", "-n"]
