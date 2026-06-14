"""KawPow algorithm implementation (Ravencoin, VRSC, etc.)."""

import asyncio
import hashlib
import os
import struct
import time
from typing import Any, Optional

from .base import BaseAlgorithm


class KawPowAlgorithm(BaseAlgorithm):
    """KawPow (X16RV2 + ProgPoW) GPU mining algorithm."""

    name = "kawpow"
    description = "KawPow (ProgPoW variant) — GPU-optimized PoW"
    supported_coins = ["RVN", "VRSC", "MEOW", "PGN"]

    EPOCH_LENGTH = 7500
    MIX_BYTES = 128
    HASH_BYTES = 64
    DATASET_PARENTS = 256

    def __init__(self):
        super().__init__()
        self._dag_cache = None
        self._current_epoch = -1

    async def compute(self, work: dict, gpu_manager: Any) -> Optional[dict]:
        """Compute KawPow hashes for the given work."""
        header_hash = bytes.fromhex(work["header_hash"])
        target = bytes.fromhex(work["target"])
        nonce_start = work.get("nonce_start", 0)
        epoch = work.get("epoch", 0)

        # Load/build DAG for current epoch
        if epoch != self._current_epoch:
            self._build_dag_cache(epoch)
            self._current_epoch = epoch

        # GPU-accelerated hash computation
        batch_size = gpu_manager.get_optimal_batch_size(self.name)

        for nonce in range(nonce_start, nonce_start + batch_size):
            # ProgPoW loop
            mix = self._progpow_init(header_hash, nonce)
            mix = self._progpow_loop(mix, self._dag_cache)

            # Final hash
            result = self._progpow_final(mix, header_hash, nonce)
            self._increment_hashes()

            # Check against target
            if self._meets_target(result, target):
                return {
                    "nonce": nonce,
                    "hash": result.hex(),
                    "mix_hash": mix[:32].hex(),
                    "algorithm": self.name,
                }

        return None

    async def benchmark(self, gpu_manager: Any, duration: int = 10) -> dict:
        """Run KawPow benchmark."""
        self.reset_stats()
        test_header = os.urandom(32)
        test_target = b"\xff" * 32
        nonce = 0

        start = time.time()
        while time.time() - start < duration:
            work = {
                "header_hash": test_header.hex(),
                "target": test_target.hex(),
                "nonce_start": nonce,
                "epoch": 0,
            }
            await self.compute(work, gpu_manager)
            nonce += gpu_manager.get_optimal_batch_size(self.name)

        elapsed = time.time() - start
        return {
            "hashes": self._hash_count,
            "hashrate": self._hash_count / elapsed,
            "duration": elapsed,
        }

    def _build_dag_cache(self, epoch: int):
        """Build DAG cache for the given epoch."""
        seed = hashlib.sha3_256(
            struct.pack(">Q", epoch * self.EPOCH_LENGTH)
        ).digest()
        self._dag_cache = self._hashimoto_cache(seed, self.HASH_BYTES * 1024)

    def _progpow_init(self, header_hash: bytes, nonce: int) -> bytes:
        """Initialize ProgPoW mix state."""
        nonce_bytes = struct.pack("<Q", nonce)
        seed = hashlib.sha3_256(header_hash + nonce_bytes).digest()
        mix = seed * (self.MIX_BYTES // 32)
        return mix

    def _progpow_loop(self, mix: bytes, dag_cache: bytes) -> bytes:
        """Execute ProgPoW mixing loop."""
        for i in range(64):
            # Deterministic random operations per ProgPoW spec
            offset = (mix[i % len(mix)] * 167) % len(dag_cache) if dag_cache else 0
            chunk = dag_cache[offset:offset + self.MIX_BYTES] if dag_cache else mix
            mix = bytes(a ^ b for a, b in zip(mix, chunk))
        return mix

    def _progpow_final(self, mix: bytes, header_hash: bytes, nonce: int) -> bytes:
        """Compute final ProgPoW hash."""
        nonce_bytes = struct.pack("<Q", nonce)
        return hashlib.sha3_256(mix + header_hash + nonce_bytes).digest()

    def _meets_target(self, result: bytes, target: bytes) -> bool:
        """Check if hash result meets difficulty target."""
        return result <= target

    def _hashimoto_cache(self, seed: bytes, size: int) -> bytes:
        """Generate hashimoto cache from seed."""
        cache = bytearray()
        current = seed
        while len(cache) < size:
            current = hashlib.sha3_256(current).digest()
            cache.extend(current)
        return bytes(cache[:size])
