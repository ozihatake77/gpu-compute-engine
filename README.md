# ⛏️ GPU Compute Engine

> High-performance multi-algorithm GPU compute engine with real-time monitoring, auto-tuning, and Docker orchestration.

[![CI](https://github.com/ozihatake77/gpu-compute-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/ozihatake77/gpu-compute-engine/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## ✨ Features

- **Multi-Algorithm Support** — RandomX, KawPow, Ethash, Equihash, CryptoNight, and more
- **Auto-Tuning** — GPU clock/memory/power auto-optimization per algorithm
- **Real-Time Dashboard** — Web-based monitoring with hashrate, temperature, power draw
- **Pool Failover** — Automatic pool switching on connection loss
- **Multi-GPU** — Native support for multi-GPU rigs (NVIDIA + AMD)
- **Docker Ready** — One-command deployment with GPU passthrough
- **REST API** — Full control via HTTP API for automation/scripting
- **Telegram Alerts** — Hashrate drops, GPU overheats, pool disconnects

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Core Engine | Python 3.10+, CUDA, ROCm |
| Algorithms | Custom kernels (OpenCL/CUDA) |
| Monitoring | FastAPI, WebSocket, Prometheus |
| Dashboard | React + TailwindCSS |
| Container | Docker + NVIDIA Container Toolkit |
| CI/CD | GitHub Actions |

## 📁 Project Structure

```
gpu-compute-engine/
├── src/
│   ├── miner.py              # Main mining engine
│   ├── algorithms/
│   │   ├── __init__.py
│   │   ├── base.py           # Base algorithm interface
│   │   ├── randomx.py        # RandomX (CPU/GPU hybrid)
│   │   ├── kawpow.py         # KawPow (RVN)
│   │   ├── ethash.py         # Ethash (ETH forks)
│   │   └── equihash.py       # Equihash (ZEC)
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── dashboard.py      # Web dashboard server
│   │   ├── metrics.py        # Prometheus metrics
│   │   └── alerts.py         # Telegram/Discord alerts
│   ├── gpu_manager.py        # GPU detection & management
│   ├── pool_client.py        # Stratum pool client
│   ├── config.py             # Configuration loader
│   └── api.py                # REST API endpoints
├── config/
│   ├── default.yaml          # Default configuration
│   └── pools.yaml            # Pool definitions
├── scripts/
│   ├── benchmark.sh          # GPU benchmark script
│   ├── setup_gpu.sh          # GPU driver setup
│   └── docker_build.sh       # Docker build helper
├── dashboard/                # Frontend (React)
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- NVIDIA GPU with CUDA 12.0+ or AMD GPU with ROCm 5.7+
- Python 3.10+
- Docker (optional)

### Install & Run

```bash
# Clone
git clone https://github.com/ozihatake77/gpu-compute-engine.git
cd gpu-compute-engine

# Install dependencies
pip install -r requirements.txt

# Configure
cp config/default.yaml config/local.yaml
# Edit config/local.yaml with your wallet & pool

# Run
python -m src.miner --config config/local.yaml
```

### Docker

```bash
docker compose up -d
```

### Benchmark

```bash
python -m src.miner --benchmark --algorithm kawpow --gpu 0
```

## ⚙️ Configuration

```yaml
# config/default.yaml
miner:
  wallet: "YOUR_WALLET_ADDRESS"
  worker: "rig-01"
  algorithms:
    - kawpow
    - ethash
    - randomx

gpu:
  devices: [0]           # GPU device IDs
  power_limit: 250       # Watts
  temp_limit: 85         # Celsius
  fan_curve: "aggressive"
  auto_tune: true

pools:
  primary:
    url: "stratum+tcp://pool.example.com:3636"
    algorithm: "kawpow"
  failover:
    - url: "stratum+tcp://backup.pool.com:3636"
      algorithm: "kawpow"

monitoring:
  dashboard_port: 8080
  api_port: 8081
  prometheus_port: 9090
  telegram:
    enabled: true
    bot_token: "${TELEGRAM_BOT_TOKEN}"
    chat_id: "${TELEGRAM_CHAT_ID}"

logging:
  level: "INFO"
  file: "logs/miner.log"
```

## 📊 REST API

```bash
# Get status
curl http://localhost:8081/api/status

# Get hashrate
curl http://localhost:8081/api/hashrate

# Switch algorithm
curl -X POST http://localhost:8081/api/algorithm \
  -H "Content-Type: application/json" \
  -d '{"algorithm": "ethash"}'

# GPU info
curl http://localhost:8081/api/gpu
```

## 🐳 Docker GPU Setup

```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

## 🧪 Testing

```bash
pytest tests/ -v
pytest tests/ --gpu  # GPU integration tests (requires GPU)
```

## 📈 Benchmarks

| Algorithm | GPU | Hashrate | Power |
|-----------|-----|----------|-------|
| KawPow | RTX 3080 | 32 MH/s | 230W |
| Ethash | RTX 3080 | 100 MH/s | 220W |
| RandomX | RTX 3080 | 2.1 KH/s | 200W |
| Equihash | RTX 3080 | 950 Sol/s | 210W |

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

Built with ❤️ for the GPU compute community.
