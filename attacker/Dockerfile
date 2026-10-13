FROM kalilinux/kali-rolling:latest

# Build args / defaults
ARG DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:1
ENV NOVNC_PORT=6080
ENV VNC_PORT=5900
ENV VNC_PASSWORD=changeme
ENV RESOLUTION=1280x720
ENV USERNAME=kali
ENV HOME=/home/$USERNAME

# Install essentials
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
      kali-desktop-xfce dbus-x11 \
      x11vnc xvfb xauth x11-utils \
      wget git nano python3 python3-pip python3-websockify \
      ca-certificates supervisor sudo \
      net-tools procps pulseaudio-utils dsniff \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


RUN useradd -m -s /bin/bash ${USERNAME} && \
    echo "${USERNAME}:kali" | chpasswd && \
    usermod -aG sudo ${USERNAME}

# Install noVNC (from GitHub) and websockify (pip installed websockify already available)
RUN git clone https://github.com/novnc/noVNC.git /opt/noVNC && \
    git clone https://github.com/novnc/websockify /opt/noVNC/utils/websockify || true && \
    chmod -R a+rx /opt/noVNC

# Create directories for runtime files
RUN mkdir -p /var/run/xvfb /var/run/x11vnc /opt/novnc/utils && chown -R ${USERNAME}:${USERNAME} ${HOME}


# Install tools
# pymodbus comes from pip, not apt: kali-rolling's python3-pymodbus (3.14+)
# has a substantially different, simulator-based datastore API than the
# pymodbus==3.9.2 already used by simulation/remote_io/modbus/*.py, and the
# lab network is intentionally isolated at runtime, so this must happen at
# build time.
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
    kali-tools-top10 iptables python3-pip \
    && pip install --break-system-packages --no-cache-dir pymodbus==3.9.2

# Supervisor config (to run xvfb, x11vnc, websockify)
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

COPY default.xml /etc/xdg/xfce4/panel/default.xml

COPY index.html /opt/noVNC/index.html

COPY sword.svg /opt/noVNC/sword.svg
RUN sed -i '/<link rel="icon"/d' /opt/noVNC/vnc.html && \
    sed -i 's|<title>[^<]*</title>|<title>Attacker Workstation</title>|' /opt/noVNC/vnc.html && \
    sed -i 's|</head>|<link rel="icon" type="image/svg+xml" href="sword.svg"></head>|' /opt/noVNC/vnc.html

# Entrypoint script that sets password and starts the desktop session
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

# allow passwordless sudo
RUN echo "kali ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/kali \
 && chmod 440 /etc/sudoers.d/kali

RUN sed -i 's/^#*autologin-user=.*/autologin-user=kali/' /etc/lightdm/lightdm.conf || true \
 && sed -i 's/^#*autologin-user-timeout=.*/autologin-user-timeout=0/' /etc/lightdm/lightdm.conf || true


# Disable XDG autostart entries that cause blank/lock in VNC/Xvfb
RUN for f in xfce4-screensaver.desktop xfce4-power-manager.desktop light-locker.desktop; do \
      if [ -f "/etc/xdg/autostart/$f" ]; then \
        sed -i '/^Hidden=/d' "/etc/xdg/autostart/$f" && \
        printf '\nHidden=true\n' >> "/etc/xdg/autostart/$f"; \
      fi; \
    done



RUN mv /usr/bin/xflock4 /usr/bin/xflock4.real && \
    printf '#!/bin/sh\nexit 0\n' > /usr/bin/xflock4 && \
    chmod +x /usr/bin/xflock4

RUN if [ -f /usr/bin/xfce4-screensaver-command ] && [ ! -f /usr/bin/xfce4-screensaver-command.real ]; then \
      mv /usr/bin/xfce4-screensaver-command /usr/bin/xfce4-screensaver-command.real; \
    fi && \
    printf '#!/bin/sh\nexit 0\n' > /usr/bin/xfce4-screensaver-command && \
    chmod +x /usr/bin/xfce4-screensaver-command

COPY xfce-no-lock.sh /usr/local/bin/xfce-no-lock.sh
RUN chmod +x /usr/local/bin/xfce-no-lock.sh

# Cyber fault-injection tooling (see docs/cyber-vs-physical-fault-injection-design.md)
COPY cyber_injects /opt/cyber_injects


EXPOSE ${NOVNC_PORT} ${VNC_PORT}

USER root

ARG BUILD_VERSION=unknown
ARG BUILD_CREATED=unknown
LABEL org.opencontainers.image.version="$BUILD_VERSION" \
      org.opencontainers.image.revision="$BUILD_VERSION" \
      org.opencontainers.image.created="$BUILD_CREATED" \
      com.grfics.service="kali"
ENTRYPOINT ["/usr/local/bin/start.sh"]
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]