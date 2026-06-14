"""Prometheus-compatible metrics collector."""

import asyncio
import time
from typing import Any


class MetricsCollector:
    """Collect and expose mining metrics."""

    def __init__(self):
        self.hashrate = 0.0
        self.shares_accepted = 0
        self.shares_rejected = 0
        self.gpu_info = []
        self._history: list[dict] = []
        self._start_time = time.time()

    def update_hashrate(self, hashrate: float):
        """Update current hashrate."""
        self.hashrate = hashrate
        self._history.append({
            "timestamp": time.time(),
            "hashrate": hashrate,
        })
        # Keep last 1000 entries
        if len(self._history) > 1000:
            self._history = self._history[-1000:]

    def record_share(self, accepted: bool):
        """Record a share submission."""
        if accepted:
            self.shares_accepted += 1
        else:
            self.shares_rejected += 1

    def get_hashrate(self) -> float:
        """Get current hashrate."""
        return self.hashrate

    def get_status(self) -> dict:
        """Get full status."""
        uptime = time.time() - self._start_time
        return {
            "hashrate": self.hashrate,
            "shares_accepted": self.shares_accepted,
            "shares_rejected": self.shares_rejected,
            "uptime_seconds": int(uptime),
            "gpu_info": self.gpu_info,
            "history": self._history[-60:],
        }

    def get_gpu_info(self) -> list:
        """Get GPU information."""
        return self.gpu_info

    async def start_collection(self, gpu_manager):
        """Start periodic GPU metrics collection."""
        while True:
            self.gpu_info = gpu_manager.get_status()
            await asyncio.sleep(2)
