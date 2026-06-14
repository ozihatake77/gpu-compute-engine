"""Web dashboard for real-time monitoring."""

import asyncio
import json
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn


class DashboardServer:
    """Real-time monitoring dashboard."""

    def __init__(self, metrics, port: int = 8080):
        self.metrics = metrics
        self.port = port
        self.app = FastAPI(title="GPU Compute Engine Dashboard")
        self._setup_routes()
        self._server = None
        self._websockets: list[WebSocket] = []

    def _setup_routes(self):
        """Setup API routes."""

        @self.app.get("/")
        async def index():
            return HTMLResponse(self._get_dashboard_html())

        @self.app.get("/api/status")
        async def status():
            return self.metrics.get_status()

        @self.app.get("/api/hashrate")
        async def hashrate():
            return {"hashrate": self.metrics.get_hashrate()}

        @self.app.get("/api/gpu")
        async def gpu_info():
            return self.metrics.get_gpu_info()

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self._websockets.append(websocket)
            try:
                while True:
                    data = self.metrics.get_status()
                    await websocket.send_json(data)
                    await asyncio.sleep(1)
            except WebSocketDisconnect:
                self._websockets.remove(websocket)

    async def start(self):
        """Start the dashboard server."""
        config = uvicorn.Config(self.app, host="0.0.0.0", port=self.port, log_level="warning")
        self._server = uvicorn.Server(config)
        await self._server.serve()

    async def stop(self):
        """Stop the dashboard server."""
        if self._server:
            self._server.should_exit = True
        for ws in self._websockets:
            await ws.close()
        self._websockets.clear()

    def _get_dashboard_html(self) -> str:
        """Get dashboard HTML page."""
        return """<!DOCTYPE html>
<html><head>
<title>GPU Compute Engine</title>
<style>
  body { font-family: monospace; background: #0a0a0a; color: #00ff41; padding: 20px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
  .card { background: #111; border: 1px solid #00ff4133; border-radius: 8px; padding: 16px; }
  .card h3 { color: #00ff41; margin: 0 0 12px; }
  .metric { font-size: 2em; font-weight: bold; }
  .label { color: #888; font-size: 0.9em; }
  .status { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
  .status.online { background: #00ff41; } .status.offline { background: #ff0040; }
  #log { height: 200px; overflow-y: auto; background: #000; padding: 10px; border-radius: 4px; font-size: 0.8em; }
</style>
</head><body>
<h1>⛏️ GPU Compute Engine</h1>
<div class="grid">
  <div class="card"><h3>Hashrate</h3><div class="metric" id="hashrate">0</div><div class="label">H/s</div></div>
  <div class="card"><h3>Shares</h3><div class="metric" id="shares">0 / 0</div><div class="label">Accepted / Rejected</div></div>
  <div class="card"><h3>GPU Temp</h3><div class="metric" id="temp">0°C</div><div class="label">Temperature</div></div>
  <div class="card"><h3>Power</h3><div class="metric" id="power">0W</div><div class="label">Power Draw</div></div>
</div>
<div class="card" style="margin-top:20px"><h3>Activity Log</h3><div id="log"></div></div>
<script>
const ws = new WebSocket(`ws://${location.host}/ws`);
ws.onmessage = (e) => {
  const d = JSON.parse(e.data);
  document.getElementById("hashrate").textContent = (d.hashrate||0).toFixed(2);
  document.getElementById("shares").textContent = `${d.shares_accepted||0} / ${d.shares_rejected||0}`;
  if(d.gpus && d.gpus[0]) {
    document.getElementById("temp").textContent = d.gpus[0].temperature + "°C";
    document.getElementById("power").textContent = d.gpus[0].power_draw + "W";
  }
  const log = document.getElementById("log");
  log.innerHTML += `[${new Date().toLocaleTimeString()}] ${(d.hashrate||0).toFixed(2)} H/s — ${d.algorithm||"idle"}<br>`;
  log.scrollTop = log.scrollHeight;
};
</script>
</body></html>"""
