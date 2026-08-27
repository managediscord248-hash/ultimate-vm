# AZMAL VPS

Persistent Debian web terminal for AZMAL.

## Features

- Persistent `tmux` terminal session
- Browser/WebSocket reconnects to the same shell
- Running commands continue after browser disconnect
- Debian 13 base image
- systemd service definition for real VPS environments
- Automatic restart with systemd
- Render-compatible fallback when systemd is not PID 1
- Simple token authentication

## Render

Render normally starts the container without systemd as PID 1.

AZMAL detects this and uses:

```text
Browser
  ↓
WebSocket
  ↓
FastAPI
  ↓
tmux session: AZMAL
  ↓
Bash
```

Disconnecting the browser does not intentionally destroy the tmux session.

Set this Render environment variable:

```text
CONSOLE_TOKEN=<strong-random-secret>
```

Use Render's `PORT` environment variable.

### Important

A Render container is still controlled by Render. If Render destroys/replaces the entire instance, a process inside it cannot prevent that lifecycle event. Persistent storage must be configured separately if data must survive replacement.

## Real Debian/Ubuntu VPS with systemd

Copy the project to the VPS, install Python dependencies, then:

```bash
sudo cp AZMAL-console.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now AZMAL-console.service
```

Check:

```bash
systemctl status AZMAL-console.service
```

Logs:

```bash
journalctl -u AZMAL-console.service -f
```

## Local Docker

Build:

```bash
docker build -t AZMAL-free-vps .
```

Run:

```bash
docker run -d \
  --name AZMAL-free-vps \
  -p 10000:10000 \
  -e CONSOLE_TOKEN='replace-with-a-long-random-token' \
  AZMAL-free-vps
```

Open:

```text
http://SERVER_IP:10000
```

## Terminal persistence

The terminal uses:

```text
tmux session = AZMAL
```

From an interactive shell:

```bash
tmux attach -t AZMAL
```

List:

```bash
tmux ls
```

Detach:

```text
Ctrl+B, then D
```

## Security

Use a long random `CONSOLE_TOKEN`. Do not commit it to Git.

For public deployment, HTTPS and access restrictions are strongly recommended.


## Terminal rendering fix

The web terminal now strips raw ANSI/VT control sequences before displaying PTY output. This prevents escape codes such as `[K`, `[30m`, and `[42m` from appearing as visible text in mobile browsers.

`Ctrl+L` clears the browser terminal view without killing the persistent tmux session.
