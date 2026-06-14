"""GPU detection, management, and monitoring."""

import subprocess
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class GPUDevice:
    """GPU device information."""
    device_id: int
    name: str
    memory_mb: int
    driver_version: str
    cuda_version: str
    temperature: float = 0.0
    power_draw: float = 0.0
    fan_speed: int = 0
    utilization: int = 0


class GPUManager:
    """Manage GPU devices for mining."""

    def __init__(self, config: dict):
        self.config = config
        self.devices: list[GPUDevice] = []
        self._device_ids = config.get("devices", [0])
        self._power_limit = config.get("power_limit", 250)
        self._temp_limit = config.get("temp_limit", 85)
        self._fan_curve = config.get("fan_curve", "auto")
        self._auto_tune = config.get("auto_tune", True)

    def detect_gpus(self) -> list[GPUDevice]:
        """Detect available GPUs."""
        self.devices = []

        # Try NVIDIA first
        nvidia_gpus = self._detect_nvidia()
        if nvidia_gpus:
            self.devices.extend(nvidia_gpus)
        else:
            # Try AMD
            amd_gpus = self._detect_amd()
            if amd_gpus:
                self.devices.extend(amd_gpus)

        # Filter by configured device IDs
        if self._device_ids and self._device_ids != [-1]:
            self.devices = [d for d in self.devices if d.device_id in self._device_ids]

        return self.devices

    def _detect_nvidia(self) -> list[GPUDevice]:
        """Detect NVIDIA GPUs via nvidia-smi."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,name,memory.total,driver_version,temperature.gpu,power.draw,utilization.gpu,fan.speed",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return []

            gpus = []
            for line in result.stdout.strip().split("
"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 8:
                    gpu = GPUDevice(
                        device_id=int(parts[0]),
                        name=parts[1],
                        memory_mb=int(parts[2]),
                        driver_version=parts[3],
                        cuda_version="12.0",
                        temperature=float(parts[4]),
                        power_draw=float(parts[5]),
                        utilization=int(parts[6]),
                        fan_speed=int(parts[7]),
                    )
                    gpus.append(gpu)
            return gpus
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

    def _detect_amd(self) -> list[GPUDevice]:
        """Detect AMD GPUs via rocm-smi."""
        try:
            result = subprocess.run(
                ["rocm-smi", "--showtemp", "--showpower", "--showmeminfo", "vram", "--json"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return []

            data = json.loads(result.stdout)
            gpus = []
            for i, (key, val) in enumerate(data.items()):
                if "card" in key.lower():
                    gpu = GPUDevice(
                        device_id=i,
                        name=f"AMD GPU {i}",
                        memory_mb=int(val.get("VRAM Total Memory (B)", 0)) // (1024 * 1024),
                        driver_version="ROCm",
                        cuda_version="ROCm 5.7",
                        temperature=float(val.get("Temperature (Sensor edge) (C)", 0)),
                        power_draw=float(val.get("Average Graphics Package Power (W)", 0)),
                    )
                    gpus.append(gpu)
            return gpus
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return []

    def apply_settings(self):
        """Apply GPU settings (power limit, fan curve, clocks)."""
        for gpu in self.devices:
            try:
                # Set power limit
                subprocess.run(
                    ["nvidia-smi", "-i", str(gpu.device_id), "-pl", str(self._power_limit)],
                    capture_output=True, timeout=5
                )

                # Set fan speed if manual
                if self._fan_curve == "manual":
                    subprocess.run(
                        ["nvidia-smi", "-i", str(gpu.device_id), "-ac", "5001,1200"],
                        capture_output=True, timeout=5
                    )

                print(f"[GPU {gpu.device_id}] Settings applied: {self._power_limit}W, fan={self._fan_curve}")
            except Exception as e:
                print(f"[GPU {gpu.device_id}] Settings error: {e}")

    def reset_settings(self):
        """Reset GPU settings to defaults."""
        for gpu in self.devices:
            try:
                subprocess.run(
                    ["nvidia-smi", "-i", str(gpu.device_id), "-rac"],
                    capture_output=True, timeout=5
                )
                print(f"[GPU {gpu.device_id}] Settings reset to defaults")
            except Exception:
                pass

    def get_optimal_batch_size(self, algorithm: str) -> int:
        """Get optimal batch size for the algorithm."""
        if not self.devices:
            return 1024
        gpu = self.devices[0]
        vram_mb = gpu.memory_mb

        batch_map = {
            "kawpow": min(vram_mb * 128, 1024 * 1024),
            "ethash": min(vram_mb * 256, 2 * 1024 * 1024),
            "randomx": min(vram_mb * 64, 512 * 1024),
            "equihash": min(vram_mb * 32, 256 * 1024),
        }
        return batch_map.get(algorithm, 4096)

    def get_power_draw(self, device_id: int = 0) -> float:
        """Get current power draw in watts."""
        for gpu in self.devices:
            if gpu.device_id == device_id:
                return gpu.power_draw
        return 0.0

    def get_temperature(self, device_id: int = 0) -> float:
        """Get current GPU temperature."""
        for gpu in self.devices:
            if gpu.device_id == device_id:
                return gpu.temperature
        return 0.0

    def get_status(self) -> list[dict]:
        """Get status of all GPUs."""
        return [
            {
                "device_id": gpu.device_id,
                "name": gpu.name,
                "memory_mb": gpu.memory_mb,
                "temperature": gpu.temperature,
                "power_draw": gpu.power_draw,
                "utilization": gpu.utilization,
                "fan_speed": gpu.fan_speed,
            }
            for gpu in self.devices
        ]
