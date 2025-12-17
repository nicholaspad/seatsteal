"""Minimal FastAPI app for terminal WebSocket endpoint (Render deployment)."""

import asyncio
import fcntl
import os
import pty
import select
import struct
import termios
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic_settings import BaseSettings
import psycopg2
from psycopg2.extras import RealDictCursor


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    DATABASE_URL: str
    ALLOWED_ORIGINS: str = "*"

    class Config:
        env_file = ".env"


settings = Settings()

app = FastAPI(title="SeatSteal Terminal Server")

# Configure CORS
origins = (
    settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS != "*" else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase client for token verification
supabase: Client = create_client(
    settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
)


def get_db_connection():
    """Get a database connection."""
    return psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)


async def verify_admin_token(token: str) -> Optional[dict]:
    """Verify the token and return the admin profile if valid."""
    try:
        # Verify JWT token with Supabase
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            return None

        user_id = UUID(user_response.user.id)

        # Get user profile from database
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, role FROM profiles WHERE id = %s", (str(user_id),)
                )
                profile = cur.fetchone()

                if not profile or profile["role"] != "admin":
                    return None

                return profile
        finally:
            conn.close()

    except Exception as e:
        print(f"Auth error: {e}")
        return None


def set_winsize(fd: int, rows: int, cols: int) -> None:
    """Set the window size of a PTY."""
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


@app.get("/health")
async def health_check():
    """Health check endpoint for Render."""
    return {"status": "healthy"}


@app.websocket("/api/admin/terminal")
async def terminal_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token"),
):
    """
    WebSocket endpoint for interactive terminal access.

    Admin-only endpoint that spawns a PTY and provides bidirectional
    communication between the WebSocket and the shell.
    """
    # Verify admin authentication
    profile = await verify_admin_token(token)
    if not profile:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()

    # Create PTY
    master_fd, slave_fd = pty.openpty()

    # Set initial terminal size
    set_winsize(master_fd, 24, 80)

    # Fork a child process
    pid = os.fork()

    if pid == 0:
        # Child process
        os.close(master_fd)
        os.setsid()

        # Set up slave as controlling terminal
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)

        if slave_fd > 2:
            os.close(slave_fd)

        # Change to home directory
        os.chdir(os.path.expanduser("~"))

        # Execute bash
        os.execvp("/bin/bash", ["/bin/bash", "--login"])

    # Parent process
    os.close(slave_fd)

    # Make master_fd non-blocking
    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    async def read_from_pty():
        """Read output from PTY and send to WebSocket."""
        loop = asyncio.get_event_loop()
        try:
            while True:
                # Use select to wait for data
                readable, _, _ = await loop.run_in_executor(
                    None, lambda: select.select([master_fd], [], [], 0.1)
                )

                if readable:
                    try:
                        data = os.read(master_fd, 4096)
                        if data:
                            await websocket.send_bytes(data)
                    except OSError:
                        break
                else:
                    # Small delay to prevent busy waiting
                    await asyncio.sleep(0.01)
        except Exception:
            pass

    async def write_to_pty():
        """Read input from WebSocket and write to PTY."""
        try:
            while True:
                message = await websocket.receive()

                if message["type"] == "websocket.disconnect":
                    break

                if "text" in message:
                    text = message["text"]
                    # Check for resize message
                    if text.startswith('{"type":"resize"'):
                        import json

                        try:
                            data = json.loads(text)
                            if data.get("type") == "resize":
                                rows = data.get("rows", 24)
                                cols = data.get("cols", 80)
                                set_winsize(master_fd, rows, cols)
                        except json.JSONDecodeError:
                            pass
                    else:
                        os.write(master_fd, text.encode())
                elif "bytes" in message:
                    os.write(master_fd, message["bytes"])

        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    # Run both tasks concurrently
    read_task = asyncio.create_task(read_from_pty())
    write_task = asyncio.create_task(write_to_pty())

    try:
        await asyncio.gather(read_task, write_task, return_exceptions=True)
    finally:
        # Cleanup
        read_task.cancel()
        write_task.cancel()

        try:
            os.close(master_fd)
        except OSError:
            pass

        try:
            os.kill(pid, 9)
            os.waitpid(pid, 0)
        except OSError:
            pass

        try:
            await websocket.close()
        except Exception:
            pass
