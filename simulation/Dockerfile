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

# Set working directory
WORKDIR /app

# Copy compiled binary from build stage
COPY --from=build /build/simulation/simulation ./simulation/simulation

# Copy the Modbus scripts
COPY ./simulation/remote_io/modbus ./modbus

# Copy your custom interfaces file and entrypoint script
COPY interfaces /etc/network/interfaces
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Optional: install Python requirements
RUN pip install --upgrade pip && pip install --no-cache-dir pymodbus==3.9.2

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Use custom entrypoint to bring up interfaces before running services
ENTRYPOINT ["/entrypoint.sh"]

CMD ["/usr/bin/supervisord", "-n"]
