FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:1
ENV NOVNC_PORT=6080
ENV VNC_PORT=5900
ENV VNC_PASSWORD=changeme
ENV RESOLUTION=1280x720
ENV USERNAME=engineer
ENV HOME=/home/$USERNAME

# Install essentials: desktop, vnc, novnc stack
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
      xfce4 dbus-x11 \
      x11vnc xvfb xauth x11-utils \
      wget git nano python3 python3-pip python3-websockify \
      ca-certificates supervisor sudo \
      net-tools procps pulseaudio-utils \
      git build-essential cmake qtbase5-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


# Add user
RUN useradd -m -s /bin/bash ${USERNAME} && \
    echo "${USERNAME}:plc123" | chpasswd && \
    usermod -aG sudo ${USERNAME}

# Install noVNC + websockify
RUN git clone https://github.com/novnc/noVNC.git /opt/noVNC && \
    git clone https://github.com/novnc/websockify /opt/noVNC/utils/websockify || true && \
    chmod -R a+rx /opt/noVNC

RUN git clone https://github.com/thiagoralves/OpenPLC_Editor.git /opt/OpenPLC_Editor \
 && cd /opt/OpenPLC_Editor \
 # Patch install.sh so wxPython installs from prebuilt wheel if possible
 && sed -i 's#-m pip install wxPython==4.2.0#-m pip install wxPython==4.2.0 --find-links https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-22.04/ --only-binary wxPython#g' install.sh \
 && ./install.sh

RUN chown -R ${USERNAME}:${USERNAME} /opt/OpenPLC_Editor

RUN apt-get update && \
    apt-get -y install --no-install-recommends \
    xfce4-terminal libgdk-pixbuf-2.0-0 librsvg2-2 dbus-x11 libsdl2-2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    adwaita-icon-theme \
    tango-icon-theme \
    hicolor-icon-theme \
    gnome-icon-theme \
    thunar-volman tumbler \
 && rm -rf /var/lib/apt/lists/*


RUN apt-get update && apt-get install -y software-properties-common && \
    add-apt-repository -y ppa:mozillateam/ppa && \
    echo 'Package: *\nPin: release o=LP-PPA-mozillateam\nPin-Priority: 1001' > /etc/apt/preferences.d/mozilla-firefox && \
    apt-get update && apt-get install -y firefox && \
    rm -rf /var/lib/apt/lists/*


# Supervisor config (xvfb, x11vnc, websockify)
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Entrypoint script
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

COPY chemical /home/engineer/Desktop/chemical/
COPY chemical.st /home/engineer/Desktop/

# Create Desktop shortcut for OpenPLC Editor
RUN mkdir -p /home/${USERNAME}/Desktop && \
    printf "[Desktop Entry]\n\
Version=1.0\n\
Type=Application\n\
Name=OpenPLC Editor\n\
Comment=OpenPLC Ladder Logic Editor\n\
Exec=/bin/bash -lc '/opt/OpenPLC_Editor/openplc_editor.sh'\n\
Icon=utilities-terminal\n\
Terminal=false\n\
Categories=Development;\n" \
    > /home/${USERNAME}/Desktop/OpenPLC.desktop && \
    chmod +x /home/${USERNAME}/Desktop/OpenPLC.desktop && \
    chown ${USERNAME}:${USERNAME} /home/${USERNAME}/Desktop/OpenPLC.desktop


COPY places.sqlite /home/engineer/.mozilla/firefox/ztc0wi0n.default-release/places.sqlite
RUN chown engineer /home/engineer/.mozilla/firefox/ztc0wi0n.default-release/places.sqlite
RUN chown -R engineer:engineer /home/engineer 

EXPOSE ${NOVNC_PORT} ${VNC_PORT}

USER root
ENTRYPOINT ["/usr/local/bin/start.sh"]
CMD ["supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
