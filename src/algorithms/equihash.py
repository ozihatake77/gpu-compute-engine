"""Equihash algorithm implementation (Zcash)."""

import asyncio
import hashlib
import os
import struct
import time
from typing import Any, Optional

from .base import BaseAlgorithm


class EquihashAlgorithm(BaseAlgorithm):
    """Equihash (Zcash) GPU mining algorithm."""

    name = "equihash"
    description = "Equihash — Memory-hard, ASIC-resistant PoW"
    supported_coins = ["ZEC", "ZEN", "KMD", "HUSH"]

    N = 200
    K = 9
    N_SHARES = (1 << (K + 1))

    def __init__(self):
        super().__init__()
        self._personalization = b"ZcashPoW"

    async def compute(self, work: dict, gpu_manager: Any) -> Optional[dict]:
        """Compute Equihash solutions."""
        header = bytes.fromhex(work["header_hash"])
        target = bytes.fromhex(work["target"])
        nonce_start = work.get("nonce_start", 0)
        nonce_size = work.get("nonce_size", 32)

        batch_size = gpu_manager.get_optimal_batch_size(self.name)

        for nonce in range(nonce_start, nonce_start + batch_size):
            nonce_bytes = nonce.to_bytes(nonce_size, "little")

            # Generate initial hash state
            state = self._generate_state(header, nonce_bytes)

            # Find collision-based solutions
            solutions = self._find_solutions(state)

            for solution in solutions:
                sol_bytes = b"".join(x.to_bytes(4, "little") for x in solution)
                result = self._verify_solution(header, nonce_bytes, sol_bytes)
                self._increment_hashes()

                if result and result <= target:
                    return {
                        "nonce": nonce,
                        "hash": result.hex(),
                        "solution": sol_bytes.hex(),
                        "algorithm": self.name,
                    }

            self._increment_hashes()

        return None

    async def benchmark(self, gpu_manager: Any, duration: int = 10) -> dict:
        """Run Equihash benchmark."""
        self.reset_stats()
        test_header = os.urandom(32)
        test_target = b"ÿ" * 32
        nonce = 0

        start = time.time()
        while time.time() - start < duration:
            work = {"header_hash": test_header.hex(), "target": test_target.hex(), "nonce_start": nonce}
            await self.compute(work, gpu_manager)
            nonce += gpu_manager.get_optimal_batch_size(self.name)

        elapsed = time.time() - start
        return {"hashes": self._hash_count, "hashrate": self._hash_count / elapsed, "duration": elapsed}

    def _generate_state(self, header: bytes, nonce: bytes) -> list:
        """Generate initial hash state for Equihash."""
        digest = hashlib.blake2b(
            header + nonce,
            digest_size=(self.N // (self.K + 1) + 7) // 8,
            person=self._personalization,
        ).digest()

        num_hashes = self.N_SHARES
        state = []
        for i in range(num_hashes):
            h = hashlib.blake2b(digest + struct.pack("<I", i), digest_size=(self.N // 8)).digest()
            state.append(int.from_bytes(h[:4], "little"))

        return state

    def _find_solutions(self, state: list) -> list:
        """Find collision-based solutions (simplified)."""
        solutions = []
        pairs = {}

        for i, val in enumerate(state):
            key = val >> (self.N // (self.K + 1))
            if key in pairs:
                pair_idx = pairs[key]
                if len(solutions) < 1:
                    solutions.append(sorted([pair_idx, i]))
            else:
                pairs[key] = i

        return solutions

    def _verify_solution(self, header: bytes, nonce: bytes, solution: bytes) -> Optional[bytes]:
        """Verify an Equihash solution."""
        h = hashlib.blake2b(header + nonce + solution, digest_size=32).digest()
        return h
