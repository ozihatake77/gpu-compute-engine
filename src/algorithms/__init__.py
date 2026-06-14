"""Algorithm registry."""

from .base import BaseAlgorithm
from .randomx import RandomXAlgorithm
from .kawpow import KawPowAlgorithm
from .ethash import EthashAlgorithm
from .equihash import EquihashAlgorithm

ALGORITHMS = {
    "randomx": RandomXAlgorithm,
    "kawpow": KawPowAlgorithm,
    "ethash": EthashAlgorithm,
    "equihash": EquihashAlgorithm,
}


def get_algorithm(name: str) -> BaseAlgorithm:
    """Get algorithm instance by name."""
    algo_class = ALGORITHMS.get(name.lower())
    if not algo_class:
        raise ValueError(f"Unknown algorithm: {name}. Available: {list(ALGORITHMS.keys())}")
    return algo_class()


def list_algorithms() -> list[str]:
    """List available algorithms."""
    return list(ALGORITHMS.keys())
