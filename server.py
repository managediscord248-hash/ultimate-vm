import asyncio
import fcntl
import json
import os
import pty
import select
import signal
import struct
import termios
import shutil
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
CONSOLE_TOKEN = os.environ.get("CONSOLE_TOKEN", "")
SESSION_NAME = os.environ.get("KC_SESSION_NAME", "AZMAL")
app = FastAPI(title="AZMAL Persistent Console")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def safe_token(candidate: str) -> bool:
    return bool(CONSOLE_TOKEN) and candidate == CONSOLE_TOKEN


def set_winsize(fd: int, rows: int, cols: int) -> None:
    rows = max(1, min(int(rows), 200))
    cols = max(1, min(int(cols), 400))
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def ensure_tmux() -> None:
    if shutil.which("tmux") is None:
        raise RuntimeError("tmux is not installed")
    import subprocess
    result = subprocess.run(
        ["tmux", "has-session", "-t", SESSION_NAME],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if result.returncode != 0:
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", SESSION_NAME, "/bin/bash"],
            check=True
        )


def child_tmux() -> None:
    os.environ.setdefault("TERM", "xterm-256color")
    os.environ.setdefault("LANG", "C.UTF-8")
    os.environ["HOME"] = "/root"
    os.chdir("/root")
    os.execvp("tmux", ["tmux", "attach-session", "-t", SESSION_NAME])


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def status() -> JSONResponse:
    return JSONResponse({
        "online": True,
        "product": "AZMAL VPS",
        "debian": Path("/etc/debian_version").read_text().strip()
            if Path("/etc/debian_version").exists() else "unknown",
        "hostname": os.uname().nodename,
        "shell": "/bin/bash",
        "systemctl": shutil.which("systemctl") is not None,
        "systemd_pid1": os.path.basename(os.readlink("/proc/1/exe"))
            if Path("/proc/1/exe").exists() else "unknown",
        "persistent_session": SESSION_NAME,
    })


@app.websocket("/ws/terminal")
async def terminal(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        auth = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        data = json.loads(auth)
    except Exception:
        await websocket.close(code=1008, reason="Authentication timeout/invalid payload")
        return

    if not safe_token(str(data.get("token", ""))):
        await websocket.close(code=1008, reason="Invalid console token")
        return

    rows = int(data.get("rows", 30) or 30)
    cols = int(data.get("cols", 120) or 120)

    try:
        ensure_tmux()
        pid, fd = pty.fork()
        if pid == 0:
            child_tmux()
            return

        set_winsize(fd, rows, cols)

        async def browser_to_pty():
            while True:
                message = await websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    return
                raw = message.get("text")
                if raw is None:
                    continue
                try:
                    item = json.loads(raw)
                except json.JSONDecodeError:
                    item = {"type": "input", "data": raw}

                if item.get("type") == "input":
                    payload = str(item.get("data", "")).encode("utf-8", "ignore")
                    if payload:
                        os.write(fd, payload)
                elif item.get("type") == "resize":
                    try:
                        set_winsize(fd, int(item.get("rows", rows)),
                                    int(item.get("cols", cols)))
                    except (TypeError, ValueError, OSError):
                        pass

        async def pty_to_browser():
            loop = asyncio.get_running_loop()
            while True:
                try:
                    ready, _, _ = await loop.run_in_executor(
                        None, select.select, [fd], [], [], 0.5
                    )
                    if not ready:
                        try:
                            waited, _ = os.waitpid(pid, os.WNOHANG)
                        except ChildProcessError:
                            waited = pid
                        if waited == pid:
                            return
                        continue

                    data = os.read(fd, 65536)
                    if not data:
                        return
                    await websocket.send_text(json.dumps({
                        "type": "output",
                        "data": data.decode("utf-8", "replace")
                    }))
                except (OSError, WebSocketDisconnect):
                    return

        await websocket.send_text(json.dumps({
            "type": "ready",
            "message": "Connected to persistent AZMAL terminal session."
        }))

        sender = asyncio.create_task(browser_to_pty())
        receiver = asyncio.create_task(pty_to_browser())

        done, pending = await asyncio.wait(
            {sender, receiver},
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        for task in done:
            try:
                task.result()
            except (WebSocketDisconnect, asyncio.CancelledError):
                pass
            except Exception:
                pass

    finally:
        # IMPORTANT: do not kill the tmux session when the browser disconnects.
        # The shell and running commands remain alive for the next connection.
        try:
            await websocket.close()
        except Exception:
            pass
