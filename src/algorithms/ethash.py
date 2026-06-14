"""Ethash algorithm implementation (Ethereum forks)."""

import asyncio
import hashlib
import os
import struct
import time
from typing import Any, Optional

from .base import BaseAlgorithm


class EthashAlgorithm(BaseAlgorithm):
    """Ethash (Dagger-Hashimoto) GPU mining algorithm."""

    name = "ethash"
    description = "Ethash — Memory-hard PoW (ETHW, ETC, etc.)"
    supported_coins = ["ETHW", "ETC", "CLO", "MUSIC"]

    EPOCH_LENGTH = 30000
    MIX_BYTES = 128
    HASH_BYTES = 64
    DATASET_PARENTS = 256
    CACHE_ROUNDS = 3

    def __init__(self):
        super().__init__()
        self._cache = None
        self._dataset = None
        self._current_epoch = -1

    async def compute(self, work: dict, gpu_manager: Any) -> Optional[dict]:
        """Compute Ethash hashes."""
        header_hash = bytes.fromhex(work["header_hash"])
        target = bytes.fromhex(work["target"])
        nonce_start = work.get("nonce_start", 0)
        epoch = work.get("epoch", 0)

        if epoch != self._current_epoch:
            self._build_cache(epoch)
            self._current_epoch = epoch

        batch_size = gpu_manager.get_optimal_batch_size(self.name)

        for nonce in range(nonce_start, nonce_start + batch_size):
            result = self._hashimoto(header_hash, nonce)
            self._increment_hashes()

            if result <= target:
                return {
                    "nonce": nonce,
                    "hash": result.hex(),
                    "algorithm": self.name,
                }

        return None

    async def benchmark(self, gpu_manager: Any, duration: int = 10) -> dict:
        """Run Ethash benchmark."""
        self.reset_stats()
        test_header = os.urandom(32)
        test_target = b"ÿ" * 32
        nonce = 0

        start = time.time()
        while time.time() - start < duration:
            work = {"header_hash": test_header.hex(), "target": test_target.hex(), "nonce_start": nonce, "epoch": 0}
            await self.compute(work, gpu_manager)
            nonce += gpu_manager.get_optimal_batch_size(self.name)

        elapsed = time.time() - start
        return {"hashes": self._hash_count, "hashrate": self._hash_count / elapsed, "duration": elapsed}

    def _build_cache(self, epoch: int):
        """Build Ethash cache for epoch."""
        seed = hashlib.sha3_256(struct.pack(">Q", epoch * self.EPOCH_LENGTH)).digest()
        n = self.HASH_BYTES * 1024
        cache = bytearray()
        current = seed
        while len(cache) < n:
            current = hashlib.sha3_256(current).digest()
            cache.extend(current)
        self._cache = bytes(cache[:n])

    def _hashimoto(self, header: bytes, nonce: int) -> bytes:
        """Execute hashimoto (DAG lookup + mix)."""
        nonce_bytes = struct.pack("<Q", nonce)
        s = hashlib.sha3_256(header + nonce_bytes).digest()
        mix = s * (self.MIX_BYTES // 32)

        for _ in range(64):
            c = int.from_bytes(mix[:4], "little") % (len(self._cache) - self.MIX_BYTES) if self._cache else 0
            chunk = self._cache[c:c + self.MIX_BYTES] if self._cache else mix
            mix = bytes(a ^ b for a, b in zip(mix, chunk))

        compressed = hashlib.sha3_256(mix).digest()
        return hashlib.sha3_256(s + compressed).digest()
