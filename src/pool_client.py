"""Stratum pool client for mining pools."""

import asyncio
import json
import socket
from typing import Optional
from urllib.parse import urlparse


class PoolClient:
    """Stratum protocol pool client."""

    def __init__(self, config: dict):
        self.config = config
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._current_job: Optional[dict] = None
        self._subscribed = False
        self._authorized = False
        self._message_id = 0

    async def connect(self, url: str):
        """Connect to mining pool via stratum protocol."""
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 3333

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=10
            )
            self._connected = True
            print(f"[Pool] Connected to {host}:{port}")

            # Subscribe to mining
            await self._send({
                "id": self._next_id(),
                "method": "mining.subscribe",
                "params": ["gpu-compute-engine/1.0.0"]
            })

            response = await self._recv()
            if response and "result" in response:
                self._subscribed = True
                print("[Pool] Subscribed to mining.notify")

        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
            raise ConnectionError(f"Failed to connect to {host}:{port}: {e}")

    async def disconnect(self):
        """Disconnect from pool."""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        self._connected = False
        self._subscribed = False
        self._authorized = False
        print("[Pool] Disconnected")

    async def authorize(self, wallet: str, worker: str, password: str = "x"):
        """Authorize with pool using wallet/worker."""
        await self._send({
            "id": self._next_id(),
            "method": "mining.authorize",
            "params": [f"{wallet}.{worker}", password]
        })

        response = await self._recv()
        if response and response.get("result") is True:
            self._authorized = True
            print(f"[Pool] Authorized as {wallet}.{worker}")
        else:
            raise ConnectionError("Authorization failed")

    async def get_work(self) -> Optional[dict]:
        """Get current work from pool."""
        if not self._connected:
            return None

        try:
            # Non-blocking check for new messages
            if self._reader and self._reader.at_eof():
                raise ConnectionError("Connection closed")

            # Check for pending messages
            try:
                data = await asyncio.wait_for(self._reader.readline(), timeout=0.1)
                if data:
                    message = json.loads(data.decode())
                    if message.get("method") == "mining.notify":
                        self._current_job = self._parse_job(message["params"])
                        return self._current_job
            except asyncio.TimeoutError:
                pass

            return self._current_job

        except (ConnectionError, json.JSONDecodeError) as e:
            raise ConnectionError(f"Pool communication error: {e}")

    async def submit(self, result: dict) -> bool:
        """Submit mining result to pool."""
        if not self._connected or not self._authorized:
            return False

        await self._send({
            "id": self._next_id(),
            "method": "mining.submit",
            "params": [
                result.get("worker", "rig-01"),
                result.get("job_id", ""),
                result.get("nonce", ""),
                result.get("hash", ""),
                result.get("mix_hash", ""),
            ]
        })

        response = await self._recv()
        if response:
            accepted = response.get("result", False)
            if accepted:
                print("[Pool] Share accepted ✓")
            else:
                error = response.get("error", ["Unknown error"])
                print(f"[Pool] Share rejected ✗ — {error}")
            return accepted

        return False

    async def _send(self, message: dict):
        """Send stratum message."""
        if self._writer:
            data = json.dumps(message) + "
"
            self._writer.write(data.encode())
            await self._writer.drain()

    async def _recv(self) -> Optional[dict]:
        """Receive stratum message."""
        if self._reader:
            try:
                data = await asyncio.wait_for(self._reader.readline(), timeout=5)
                if data:
                    return json.loads(data.decode())
            except (asyncio.TimeoutError, json.JSONDecodeError):
                pass
        return None

    def _parse_job(self, params: list) -> dict:
        """Parse mining.notify job parameters."""
        if len(params) >= 4:
            return {
                "job_id": params[0],
                "header_hash": params[1],
                "target": params[3] if len(params) > 3 else "00" * 32,
                "epoch": int(params[2], 16) if len(params) > 2 else 0,
            }
        return {}

    def _next_id(self) -> int:
        """Get next message ID."""
        self._message_id += 1
        return self._message_id

    @property
    def is_connected(self) -> bool:
        return self._connected
