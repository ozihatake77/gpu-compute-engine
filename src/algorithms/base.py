"""Base algorithm interface."""

from abc import ABC, abstractmethod
from typing import Any, Optional
import time


class BaseAlgorithm(ABC):
    """Abstract base class for mining algorithms."""

    name: str = "base"
    description: str = "Base algorithm"
    supported_coins: list[str] = []

    def __init__(self):
        self._hash_count = 0
        self._start_time = None
        self._current_hashrate = 0.0

    @abstractmethod
    async def compute(self, work: dict, gpu_manager: Any) -> Optional[dict]:
        """Compute hashes for the given work.

        Args:
            work: Work unit from pool
            gpu_manager: GPU manager instance

        Returns:
            Result dict if solution found, None otherwise
        """
        pass

    @abstractmethod
    async def benchmark(self, gpu_manager: Any, duration: int = 10) -> dict:
        """Run benchmark for this algorithm.

        Args:
            gpu_manager: GPU manager instance
            duration: Benchmark duration in seconds

        Returns:
            Dict with benchmark results
        """
        pass

    def get_hashrate(self) -> float:
        """Get current hashrate in H/s."""
        if self._start_time and self._hash_count > 0:
            elapsed = time.time() - self._start_time
            self._current_hashrate = self._hash_count / elapsed
        return self._current_hashrate

    def reset_stats(self):
        """Reset hash statistics."""
        self._hash_count = 0
        self._start_time = time.time()

    def _increment_hashes(self, count: int = 1):
        """Increment hash counter."""
        self._hash_count += count
        if not self._start_time:
            self._start_time = time.time()
