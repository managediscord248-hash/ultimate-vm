#!/bin/bash
set -Eeuo pipefail

SERVICE_FILE="/etc/systemd/system/AZMAL-console.service"

if [ -f "$SERVICE_FILE" ]; then
  systemctl daemon-reload
  systemctl enable --now AZMAL-console.service
fi

exec /opt/venv/bin/uvicorn server:app --host 0.0.0.0 --port "${PORT:-10000}"
