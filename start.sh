#!/bin/bash
set -Eeuo pipefail

PORT="${PORT:-10000}"
CONSOLE_TOKEN="${CONSOLE_TOKEN:-}"
SESSION_NAME="${KC_SESSION_NAME:-AZMAL}"

if [ -z "$CONSOLE_TOKEN" ] || [ "$CONSOLE_TOKEN" = "change-me" ]; then
  echo "ERROR: Set a strong CONSOLE_TOKEN."
  exit 1
fi

mkdir -p /run/sshd /run/dbus /var/log/AZMAL

# Render and similar platforms normally do not run systemd as PID 1.
# We detect that and use tmux for persistent terminal state instead.
if [ "$(ps -p 1 -o comm= 2>/dev/null || true)" = "systemd" ] && command -v systemctl >/dev/null 2>&1; then
  echo "[AZMAL] systemd detected."
  exec /app/systemd-entrypoint.sh
fi

echo "[AZMAL] systemd is not PID 1; using persistent tmux session."
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  tmux new-session -d -s "$SESSION_NAME" /bin/bash
fi

exec /opt/venv/bin/uvicorn server:app --host 0.0.0.0 --port "$PORT"
