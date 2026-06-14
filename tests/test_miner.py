"""Tests for GPU Compute Engine."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch


def test_config_load():
    """Test configuration loading."""
    from src.config import load_config, _apply_defaults

    config = _apply_defaults({})
    assert "miner" in config
    assert "gpu" in config
    assert "pools" in config
    assert "monitoring" in config


def test_algorithm_registry():
    """Test algorithm registry."""
    from src.algorithms import list_algorithms, get_algorithm

    algos = list_algorithms()
    assert "kawpow" in algos
    assert "ethash" in algos
    assert "randomx" in algos
    assert "equihash" in algos

    algo = get_algorithm("kawpow")
    assert algo.name == "kawpow"

    with pytest.raises(ValueError):
        get_algorithm("nonexistent")


def test_gpu_manager():
    """Test GPU manager initialization."""
    from src.gpu_manager import GPUManager

    config = {"devices": [0], "power_limit": 200, "temp_limit": 80}
    manager = GPUManager(config)
    assert manager._power_limit == 200
    assert manager._temp_limit == 80


def test_metrics_collector():
    """Test metrics collector."""
    from src.monitoring.metrics import MetricsCollector

    metrics = MetricsCollector()
    metrics.update_hashrate(100.0)
    assert metrics.get_hashrate() == 100.0

    metrics.record_share(accepted=True)
    metrics.record_share(accepted=False)
    assert metrics.shares_accepted == 1
    assert metrics.shares_rejected == 1


def test_pool_client():
    """Test pool client initialization."""
    from src.pool_client import PoolClient

    config = {"primary": {"url": "stratum+tcp://pool.example.com:3333"}}
    client = PoolClient(config)
    assert not client.is_connected


@pytest.mark.asyncio
async def test_kawpow_compute():
    """Test KawPow algorithm compute."""
    from src.algorithms.kawpow import KawPowAlgorithm

    algo = KawPowAlgorithm()
    mock_gpu = MagicMock()
    mock_gpu.get_optimal_batch_size.return_value = 100

    work = {
        "header_hash": "ab" * 32,
        "target": "ff" * 32,
        "nonce_start": 0,
        "epoch": 0,
    }

    # This should not raise
    result = await algo.compute(work, mock_gpu)
    # Result may be None (no solution found in small batch)
    assert result is None or isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
