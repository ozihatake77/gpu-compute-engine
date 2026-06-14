"""RandomX algorithm implementation (Monero)."""

import asyncio
import hashlib
import os
import struct
import time
from typing import Any, Optional

from .base import BaseAlgorithm


class RandomXAlgorithm(BaseAlgorithm):
    """RandomX CPU/GPU hybrid mining algorithm."""

    name = "randomx"
    description = "RandomX — CPU-optimized, ASIC-resistant PoW"
    supported_coins = ["XMR", "ZEPH"]

    SCRATCHPAD_L3 = 2 * 1024 * 1024  # 2MB
    SCRATCHPAD_L2 = 256 * 1024        # 256KB
    REGISTER_COUNT = 8
    PROGRAM_SIZE = 256
    PROGRAM_ITERATIONS = 2048

    def __init__(self):
        super().__init__()
        self._dataset = None
        self._cache = None

    async def compute(self, work: dict, gpu_manager: Any) -> Optional[dict]:
        """Compute RandomX hashes."""
        header = bytes.fromhex(work["header_hash"])
        target = bytes.fromhex(work["target"])
        seed_hash = bytes.fromhex(work.get("seed_hash", "00" * 32))
        nonce_start = work.get("nonce_start", 0)

        if not self._dataset:
            self._init_dataset(seed_hash)

        batch_size = gpu_manager.get_optimal_batch_size(self.name)

        for nonce in range(nonce_start, nonce_start + batch_size):
            nonce_bytes = struct.pack("<Q", nonce)
            input_data = header + nonce_bytes

            # Initialize scratchpad
            scratchpad = self._init_scratchpad(input_data)

            # Execute random program
            registers = [0] * self.REGISTER_COUNT
            for _ in range(self.PROGRAM_ITERATIONS):
                registers = self._execute_program(registers, scratchpad)

            # Finalize
            result = self._finalize(registers, scratchpad)
            self._increment_hashes()

            if result <= target:
                return {
                    "nonce": nonce,
                    "hash": result.hex(),
                    "algorithm": self.name,
                }

        return None

    async def benchmark(self, gpu_manager: Any, duration: int = 10) -> dict:
        """Run RandomX benchmark."""
        self.reset_stats()
        test_header = os.urandom(32)
        test_target = b"ÿ" * 32
        test_seed = os.urandom(32)
        nonce = 0

        start = time.time()
        while time.time() - start < duration:
            work = {
                "header_hash": test_header.hex(),
                "target": test_target.hex(),
                "seed_hash": test_seed.hex(),
                "nonce_start": nonce,
            }
            await self.compute(work, gpu_manager)
            nonce += gpu_manager.get_optimal_batch_size(self.name)

        elapsed = time.time() - start
        return {"hashes": self._hash_count, "hashrate": self._hash_count / elapsed, "duration": elapsed}

    def _init_dataset(self, seed: bytes):
        """Initialize RandomX dataset."""
        self._cache = hashlib.sha3_256(seed).digest()
        self._dataset = self._cache * (self.SCRATCHPAD_L3 // 32)

    def _init_scratchpad(self, input_data: bytes) -> bytearray:
        """Initialize scratchpad from input data."""
        hash_val = hashlib.sha3_256(input_data).digest()
        scratchpad = bytearray(hash_val * (self.SCRATCHPAD_L3 // 32))
        return scratchpad

    def _execute_program(self, registers: list, scratchpad: bytearray) -> list:
        """Execute a random program on registers."""
        for i in range(self.PROGRAM_SIZE):
            op = (registers[i % 8] ^ i) & 0xFF
            src = op % self.REGISTER_COUNT
            dst = (op >> 3) % self.REGISTER_COUNT

            if op & 0x80:
                addr = registers[src] % (len(scratchpad) - 8)
                val = int.from_bytes(scratchpad[addr:addr + 8], "little")
                registers[dst] = (registers[dst] + val) & 0xFFFFFFFFFFFFFFFF
            elif op & 0x40:
                registers[dst] = (registers[src] ^ registers[dst]) & 0xFFFFFFFFFFFFFFFF
            else:
                registers[dst] = (registers[src] + registers[dst]) & 0xFFFFFFFFFFFFFFFF

        return registers

    def _finalize(self, registers: list, scratchpad: bytearray) -> bytes:
        """Compute final hash from registers and scratchpad."""
        data = b"".join(struct.pack("<Q", r) for r in registers)
        data += bytes(scratchpad[:256])
        return hashlib.sha3_256(data).digest()
