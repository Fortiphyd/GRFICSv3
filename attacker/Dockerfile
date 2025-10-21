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
      net-tools procps pulseaudio-utils \
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
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
    kali-tools-top10 python3-pymodbus

# Supervisor config (to run xvfb, x11vnc, websockify)
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

COPY default.xml /etc/xdg/xfce4/panel/default.xml

# Entrypoint script that sets password and starts the desktop session
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

EXPOSE ${NOVNC_PORT} ${VNC_PORT}

USER root

ENTRYPOINT ["/usr/local/bin/start.sh"]
CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
