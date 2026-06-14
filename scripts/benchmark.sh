#!/bin/bash
# GPU Benchmark Script
set -e

echo "=== GPU Compute Engine Benchmark ==="
echo ""

# Detect GPUs
echo "Detecting GPUs..."
nvidia-smi --query-gpu=index,name,memory.total,temperature.gpu --format=csv,noheader 2>/dev/null || echo "No NVIDIA GPU detected"

echo ""
echo "Running benchmarks..."
echo ""

# Benchmark each algorithm
for algo in kawpow ethash randomx equihash; do
    echo "--- $algo ---"
    python3 -m src.miner --benchmark --algorithm "$algo" --gpu 0 --duration 30
    echo ""
done

echo "=== Benchmark Complete ==="
