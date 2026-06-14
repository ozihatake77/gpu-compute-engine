#!/usr/bin/env python3
"""
GPU Compute Engine — Main Mining Engine
High-performance multi-algorithm GPU compute engine.
"""

import argparse
import asyncio
import signal
import sys
import time
from pathlib import Path

from .config import load_config
from .gpu_manager import GPUManager
from .pool_client import PoolClient
from .algorithms import get_algorithm
from .monitoring.dashboard import DashboardServer
from .monitoring.metrics import MetricsCollector
from .monitoring.alerts import AlertManager


class ComputeEngine:
    """Main compute engine orchestrator."""

    def __init__(self, config: dict):
        self.config = config
        self.running = False
        self.gpu_manager = GPUManager(config["gpu"])
        self.pool_client = PoolClient(config["pools"])
        self.metrics = MetricsCollector()
        self.alerts = AlertManager(config.get("monitoring", {}))
        self.dashboard = DashboardServer(
            self.metrics,
            port=config["monitoring"].get("dashboard_port", 8080),
        )
        self.current_algorithm = None
        self.hashrate = 0.0
        self.shares_accepted = 0
        self.shares_rejected = 0
        self.start_time = None

    async def start(self):
        """Start the compute engine."""
        self.running = True
        self.start_time = time.time()

        # Initialize GPU devices
        gpus = self.gpu_manager.detect_gpus()
        print(f"[Engine] Detected {len(gpus)} GPU(s)")
        for gpu in gpus:
            print(f"  [{gpu.device_id}] {gpu.name} — {gpu.memory_mb}MB VRAM")

        # Apply GPU settings
        self.gpu_manager.apply_settings()

        # Connect to pool
        pool_config = self.config["pools"]["primary"]
        await self.pool_client.connect(pool_config["url"])
        print(f"[Engine] Connected to pool: {pool_config['url']}")

        # Load algorithm
        algo_name = pool_config.get("algorithm", "kawpow")
        self.current_algorithm = get_algorithm(algo_name)
        print(f"[Engine] Algorithm: {algo_name}")

        # Start monitoring
        asyncio.create_task(self.dashboard.start())
        asyncio.create_task(self.metrics.start_collection(self.gpu_manager))
        asyncio.create_task(self.alerts.start(self))

        print("[Engine] All systems go. Mining started.")
        print(f"[Engine] Dashboard: http://localhost:{self.config['monitoring'].get('dashboard_port', 8080)}")

        # Main mining loop
        await self._mining_loop()

    async def _mining_loop(self):
        """Core mining loop."""
        while self.running:
            try:
                # Get work from pool
                work = await self.pool_client.get_work()
                if not work:
                    await asyncio.sleep(1)
                    continue

                # Process work on GPU
                result = await self.current_algorithm.compute(
                    work, self.gpu_manager
                )

                # Submit result
                if result:
                    accepted = await self.pool_client.submit(result)
                    if accepted:
                        self.shares_accepted += 1
                        self.metrics.record_share(accepted=True)
                    else:
                        self.shares_rejected += 1
                        self.metrics.record_share(accepted=False)

                # Update hashrate
                self.hashrate = self.current_algorithm.get_hashrate()
                self.metrics.update_hashrate(self.hashrate)

            except ConnectionError:
                print("[Engine] Pool connection lost. Switching to failover...")
                await self._handle_failover()
            except Exception as e:
                print(f"[Engine] Error: {e}")
                await asyncio.sleep(1)

    async def _handle_failover(self):
        """Handle pool failover."""
        failover_pools = self.config["pools"].get("failover", [])
        for pool in failover_pools:
            try:
                await self.pool_client.connect(pool["url"])
                print(f"[Engine] Failover connected: {pool['url']}")
                await self.alerts.send(f"⚠️ Failover activated: {pool['url']}")
                return
            except Exception:
                continue
        print("[Engine] All pools unavailable. Retrying in 30s...")
        await asyncio.sleep(30)

    async def stop(self):
        """Stop the compute engine gracefully."""
        print("[Engine] Shutting down...")
        self.running = False
        self.gpu_manager.reset_settings()
        await self.pool_client.disconnect()
        await self.dashboard.stop()
        print("[Engine] Shutdown complete.")

    def get_status(self) -> dict:
        """Get current engine status."""
        uptime = time.time() - self.start_time if self.start_time else 0
        return {
            "running": self.running,
            "algorithm": self.current_algorithm.name if self.current_algorithm else None,
            "hashrate": self.hashrate,
            "shares_accepted": self.shares_accepted,
            "shares_rejected": self.shares_rejected,
            "uptime_seconds": int(uptime),
            "gpus": self.gpu_manager.get_status(),
        }


async def run_benchmark(algorithm: str, gpu_id: int, duration: int = 60):
    """Run GPU benchmark for a specific algorithm."""
    print(f"[Benchmark] Running {algorithm} on GPU {gpu_id} for {duration}s...")

    gpu_manager = GPUManager({"devices": [gpu_id]})
    gpus = gpu_manager.detect_gpus()

    if not gpus:
        print("[Benchmark] No GPU detected!")
        return

    algo = get_algorithm(algorithm)
    start = time.time()
    total_hashes = 0

    while time.time() - start < duration:
        result = await algo.benchmark(gpu_manager, duration=5)
        total_hashes += result["hashes"]
        elapsed = time.time() - start
        hashrate = total_hashes / elapsed
        print(f"  [{elapsed:.0f}s] {hashrate:.2f} H/s")

    avg_hashrate = total_hashes / duration
    power = gpu_manager.get_power_draw(gpu_id)
    temp = gpu_manager.get_temperature(gpu_id)

    print(f"\n[Benchmark] Results:")
    print(f"  Algorithm:  {algorithm}")
    print(f"  GPU:        {gpus[0].name}")
    print(f"  Hashrate:   {avg_hashrate:.2f} H/s")
    print(f"  Power:      {power:.0f}W")
    print(f"  Temp:       {temp:.0f}°C")
    print(f"  Efficiency: {avg_hashrate / power:.4f} H/W")


def main():
    parser = argparse.ArgumentParser(description="GPU Compute Engine")
    parser.add_argument(
        "--config", type=str, default="config/default.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--benchmark", action="store_true",
        help="Run benchmark mode"
    )
    parser.add_argument(
        "--algorithm", type=str, default="kawpow",
        help="Algorithm for benchmark"
    )
    parser.add_argument(
        "--gpu", type=int, default=0,
        help="GPU device ID"
    )
    parser.add_argument(
        "--duration", type=int, default=60,
        help="Benchmark duration in seconds"
    )
    args = parser.parse_args()

    if args.benchmark:
        asyncio.run(run_benchmark(args.algorithm, args.gpu, args.duration))
        return

    config = load_config(args.config)
    engine = ComputeEngine(config)

    loop = asyncio.new_event_loop()

    def signal_handler(sig, frame):
        print("\n[Main] Interrupt received. Shutting down...")
        loop.create_task(engine.stop())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        loop.run_until_complete(engine.start())
    except KeyboardInterrupt:
        loop.run_until_complete(engine.stop())


if __name__ == "__main__":
    main()
