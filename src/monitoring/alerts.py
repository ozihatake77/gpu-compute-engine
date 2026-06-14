"""Alert management (Telegram, Discord, etc.)."""

import asyncio
import aiohttp
from typing import Optional


class AlertManager:
    """Send alerts via Telegram/Discord."""

    def __init__(self, config: dict):
        self.config = config
        self.telegram_enabled = config.get("telegram", {}).get("enabled", False)
        self.telegram_token = config.get("telegram", {}).get("bot_token", "")
        self.telegram_chat_id = config.get("telegram", {}).get("chat_id", "")
        self._last_alert = 0
        self._alert_cooldown = 60  # seconds

    async def send(self, message: str):
        """Send alert message."""
        import time
        now = time.time()
        if now - self._last_alert < self._alert_cooldown:
            return
        self._last_alert = now

        if self.telegram_enabled:
            await self._send_telegram(message)

    async def _send_telegram(self, message: str):
        """Send Telegram alert."""
        if not self.telegram_token or not self.telegram_chat_id:
            return

        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        data = {"chat_id": self.telegram_chat_id, "text": message, "parse_mode": "HTML"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as resp:
                    if resp.status != 200:
                        print(f"[Alert] Telegram send failed: {resp.status}")
        except Exception as e:
            print(f"[Alert] Telegram error: {e}")

    async def start(self, engine):
        """Start monitoring for alert conditions."""
        while True:
            try:
                # Check GPU temperature
                for gpu in engine.gpu_manager.devices:
                    if gpu.temperature > engine.gpu_manager._temp_limit:
                        await self.send(f"🔥 GPU {gpu.device_id} HIGH TEMP: {gpu.temperature}°C!")

                # Check hashrate drop
                if engine.hashrate < 1.0 and engine.running:
                    await self.send("⚠️ Hashrate dropped below 1 H/s!")

                await asyncio.sleep(30)
            except Exception:
                await asyncio.sleep(30)
