FROM debian:13

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000 \
    CONSOLE_TOKEN=change-me

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3 python3-venv python3-pip bash sudo ca-certificates curl wget git \
      openssh-client rsync nano vim less htop tree unzip zip tar gzip bzip2 xz-utils \
      jq file lsof procps psmisc iproute2 iputils-ping net-tools dnsutils traceroute \
      socat netcat-openbsd ncdu pciutils usbutils kmod locales tzdata cron logrotate \
      gnupg openssl dbus dbus-user-session systemd systemd-sysv tmux util-linux \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

COPY server.py /app/server.py
COPY start.sh /app/start.sh
COPY static /app/static
COPY kingcloud-console.service /app/kingcloud-console.service
COPY systemd-entrypoint.sh /app/systemd-entrypoint.sh

RUN chmod +x /app/start.sh /app/systemd-entrypoint.sh && \
    mkdir -p /etc/systemd/system && \
    cp /app/kingcloud-console.service /etc/systemd/system/kingcloud-console.service

EXPOSE 10000

CMD ["/app/start.sh"]
