"""
Key pool for the mock KME, backed by BB84Protocol.

Mirrors the lifecycle in John's kme_server.py:
  _available  — keys generated, not yet issued
  _pending    — issued to master SAE, awaiting slave SAE retrieval

Keys are deleted from _pending once the slave retrieves them,
matching real KME one-time-use semantics.
"""

from __future__ import annotations

import hashlib
import threading
import uuid
import base64
from collections import deque
from dataclasses import dataclass

from ..sim import BB84Protocol

DEFAULT_KEY_SIZE     = 256   # bits
MIN_KEY_SIZE         = 64    # bits
MAX_KEY_SIZE         = 1024  # bits
MAX_KEYS_PER_REQUEST = 10
POOL_TARGET          = 20    # keys to keep available
POOL_REFILL_TRIGGER  = 5     # refill when available drops below this


@dataclass
class StoredKey:
    key_id:    str
    key_bytes: bytes
    size_bits: int


class KeyPool:
    """
    Thread-safe key pool backed by BB84Protocol.

    Uses backend="classical" by default — no Qiskit install required
    for the mock server. Users can pass backend="qiskit" if they have
    the sim extra installed.
    """

    def __init__(self, backend: str = "classical", error_rate: float = 0.01) -> None:
        self._available:       dict[str, StoredKey] = {}
        self._available_order: deque[str]           = deque()
        self._pending:         dict[str, StoredKey] = {}
        self._lock = threading.Lock()
        self._proto = BB84Protocol(
            error_rate=error_rate,
            backend=backend,
        )
        self._fill_to_target()

    def _generate(self, size_bits: int = DEFAULT_KEY_SIZE) -> StoredKey:
        """
        Run BB84 and return a key of exactly size_bits bits.

        BB84's privacy amplification always outputs 32 bytes (256 bits).
        For other sizes we stretch with BLAKE2b or truncate.
        This matches John's approach in kme_server.py exactly.
        """
        n_raw = max(4096, size_bits * 25)
        result = self._proto.run(n_bits=n_raw)
        if not result.secure:
            raise RuntimeError("BB84 aborted — QBER exceeded threshold")

        needed = size_bits // 8
        key = result.final_key
        while len(key) < needed:
            key += hashlib.blake2b(key, digest_size=32).digest()
        key = key[:needed]

        return StoredKey(
            key_id=str(uuid.uuid4()),
            key_bytes=key,
            size_bits=size_bits,
        )

    def _fill_to_target(self) -> None:
        while len(self._available) < POOL_TARGET:
            k = self._generate()
            self._available[k.key_id] = k
            self._available_order.append(k.key_id)

    def _maybe_refill(self) -> None:
        if len(self._available) < POOL_REFILL_TRIGGER:
            threading.Thread(target=self._fill_to_target, daemon=True).start()

    def get_keys(self, count: int, size_bits: int = DEFAULT_KEY_SIZE) -> list[StoredKey]:
        """
        Issue `count` keys to the master SAE.
        Keys move _available → _pending.
        """
        with self._lock:
            matching = [
                kid for kid in self._available_order
                if self._available[kid].size_bits == size_bits
            ]
            while len(matching) < count:
                k = self._generate(size_bits)
                self._available[k.key_id] = k
                self._available_order.append(k.key_id)
                matching.append(k.key_id)

            keys = []
            for kid in matching[:count]:
                k = self._available.pop(kid)
                self._available_order.remove(kid)
                self._pending[kid] = k
                keys.append(k)

        self._maybe_refill()
        return keys

    def get_by_ids(self, key_ids: list[str]) -> tuple[list[StoredKey], list[str]]:
        """
        Retrieve specific keys by ID for the slave SAE.
        Found keys are removed from _pending (one-time use).
        Returns (found, missing).
        """
        found   = []
        missing = []
        with self._lock:
            for kid in key_ids:
                if kid in self._pending:
                    found.append(self._pending.pop(kid))
                else:
                    missing.append(kid)
        return found, missing

    @property
    def available_count(self) -> int:
        return len(self._available)


def key_to_dict(k: StoredKey) -> dict:
    return {
        "key_ID": k.key_id,
        "key":    base64.b64encode(k.key_bytes).decode("ascii"),
    }