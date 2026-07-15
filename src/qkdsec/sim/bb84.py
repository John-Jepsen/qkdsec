"""BB84 QKD protocol — top-level orchestration.

Steps:
    1. Alice prepares qubits in Z or X basis
    2. Qubits traverse a (noisy, optionally eavesdropped) quantum channel
    3. Bob measures in a random basis; basis sifting discards mismatches
    4. QBER estimation on a random public sample detects eavesdropping
    5. Error correction — Cascade-style parity reconciliation. Alice's bits
       are consulted only through block parities (the information she would
       announce publicly); every announced parity is counted as leaked.
    6. Verification — Alice and Bob compare a short hash of their corrected
       keys; a mismatch marks the run insecure instead of silently emitting
       divergent keys.
    7. Privacy amplification — hash-based compression sized from the
       remaining entropy: sifted bits minus Eve's QBER-bound information
       minus everything leaked during reconciliation.

Security properties:
    - Aborts if estimated QBER exceeds 11% (BB84 security threshold)
    - Final key length never exceeds the entropy budget
      ``n - n*h(QBER) - leaked_bits`` (capped at 256 bits)

Caveat: privacy amplification uses BLAKE2b as the extractor. That is the
standard practical substitution, but BLAKE2b is a cryptographic hash, not a
seeded 2-universal family, so the information-theoretic leftover-hash
guarantee does not formally apply.
"""

import hashlib
import math
import random
from dataclasses import dataclass
from typing import Optional

# Length of the public hash tag Alice and Bob compare to verify their
# corrected keys match; counted against the entropy budget.
_VERIFICATION_TAG_BITS = 128


def _binary_entropy(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


@dataclass
class BB84Result:
    final_key: bytes
    key_length_bits: int
    raw_bits: int
    sifted_bits: int
    qber: float
    eavesdropper_detected: bool
    secure: bool
    backend_used: str = "qiskit"
    sift_ratio: float = 0.0
    block_error_rates: Optional[list[float]] = None
    error_variance: float = 0.0
    max_burst_length: int = 0
    reconciliation_verified: bool = False
    leaked_bits: int = 0


class BB84Protocol:
    """Full BB84 QKD protocol.

    Parameters
    ----------
    error_rate : float
        Background channel error rate (without eavesdropping). Default 0.01.
    eavesdrop : bool
        Simulate an intercept-resend eavesdropper. Default False.
    eavesdrop_fraction : float
        Fraction of qubits Eve intercepts. Only used when eavesdrop=True.
    qber_threshold : float
        Maximum tolerable QBER. Protocol aborts above this. Default 0.11.
    sample_fraction : float
        Fraction of sifted bits sacrificed for QBER estimation. Default 0.10.
    backend : str
        ``"qiskit"`` — IBM Qiskit Aer simulator (requires qkdsec[sim] extra).
        ``"classical"`` — pure-Python probabilistic simulation (no extras).
    seed : int, optional
        Seed for reproducible runs. When omitted, all randomness comes from
        the operating system (``random.SystemRandom``). Seeded runs are for
        research reproducibility only — never seed a run whose key you
        intend to use.
    """

    def __init__(
        self,
        error_rate: float = 0.01,
        eavesdrop: bool = False,
        eavesdrop_fraction: float = 1.0,
        qber_threshold: float = 0.11,
        sample_fraction: float = 0.10,
        backend: str = "qiskit",
        seed: Optional[int] = None,
    ):
        self.backend_name = backend
        self._rng: random.Random = (
            random.Random(seed) if seed is not None else random.SystemRandom()
        )
        if backend == "qiskit":
            from ._qiskit import QiskitQuantumChannel
            self.channel = QiskitQuantumChannel(
                error_rate=error_rate,
                eavesdrop=eavesdrop,
                eavesdrop_fraction=eavesdrop_fraction,
                rng=self._rng,
                seed=seed,
            )
        elif backend == "classical":
            from ._classical import ClassicalQuantumChannel
            self.channel = ClassicalQuantumChannel(
                error_rate=error_rate,
                eavesdrop=eavesdrop,
                eavesdrop_fraction=eavesdrop_fraction,
                rng=self._rng,
            )
        else:
            raise ValueError(
                f"Unknown backend: {backend!r} (use 'qiskit' or 'classical')"
            )
        self.qber_threshold = qber_threshold
        self.sample_fraction = sample_fraction

    def run(self, n_bits: int = 4096) -> BB84Result:
        """Execute the full BB84 protocol and return a BB84Result."""
        alice_bits = [self._rng.randrange(2) for _ in range(n_bits)]
        alice_bases = [self._rng.randrange(2) for _ in range(n_bits)]

        bob_bits, bob_bases = self.channel.transmit(alice_bits, alice_bases)

        sifted_alice: list[int] = []
        sifted_bob: list[int] = []
        for i in range(n_bits):
            if alice_bases[i] == bob_bases[i]:
                sifted_alice.append(alice_bits[i])
                sifted_bob.append(bob_bits[i])

        n_sifted = len(sifted_alice)
        if n_sifted < 40:
            raise RuntimeError(
                f"Only {n_sifted} sifted bits — increase n_bits (try 4096+)"
            )

        # Sample indices are chosen at random *after* transmission so Eve
        # cannot treat estimation and key positions differently.
        sample_size = max(10, int(n_sifted * self.sample_fraction))
        sample_idx = set(self._rng.sample(range(n_sifted), sample_size))
        sample_alice = [sifted_alice[i] for i in range(n_sifted) if i in sample_idx]
        sample_bob = [sifted_bob[i] for i in range(n_sifted) if i in sample_idx]
        key_alice = [sifted_alice[i] for i in range(n_sifted) if i not in sample_idx]
        key_bob = [sifted_bob[i] for i in range(n_sifted) if i not in sample_idx]

        errors = sum(a != b for a, b in zip(sample_alice, sample_bob, strict=True))
        qber = errors / sample_size

        sift_ratio = n_sifted / n_bits
        block_error_rates = self._compute_block_error_rates(
            sample_alice, sample_bob, block_size=8
        )
        error_variance = (
            sum((r - qber) ** 2 for r in block_error_rates) / len(block_error_rates)
            if block_error_rates else 0.0
        )
        max_burst = self._max_error_burst(sample_alice, sample_bob)

        def _result(
            final_key: bytes = b"",
            secure: bool = False,
            eavesdropper_detected: bool = False,
            reconciliation_verified: bool = False,
            leaked_bits: int = 0,
        ) -> BB84Result:
            return BB84Result(
                final_key=final_key,
                key_length_bits=len(final_key) * 8,
                raw_bits=n_bits,
                sifted_bits=n_sifted,
                qber=qber,
                eavesdropper_detected=eavesdropper_detected,
                secure=secure,
                backend_used=self.backend_name,
                sift_ratio=sift_ratio,
                block_error_rates=block_error_rates,
                error_variance=error_variance,
                max_burst_length=max_burst,
                reconciliation_verified=reconciliation_verified,
                leaked_bits=leaked_bits,
            )

        if qber > self.qber_threshold or not key_alice:
            return _result(eavesdropper_detected=qber > self.qber_threshold)

        corrected_bob, leaked = self._reconcile(key_alice, key_bob)
        # Verification: compare a short hash of both corrected keys (the
        # public hash-comparison step of a real deployment). Its length is
        # conservatively counted against the entropy budget below.
        verified = self._key_digest(key_alice) == self._key_digest(corrected_bob)
        leaked += _VERIFICATION_TAG_BITS
        if not verified:
            return _result(leaked_bits=leaked)

        final_key = self._privacy_amplify(corrected_bob, qber, leaked)
        return _result(
            final_key=final_key,
            secure=len(final_key) > 0,
            reconciliation_verified=True,
            leaked_bits=leaked,
        )

    @staticmethod
    def _compute_block_error_rates(
        alice: list[int], bob: list[int], block_size: int = 8
    ) -> list[float]:
        rates = []
        for start in range(0, len(alice) - block_size + 1, block_size):
            errs = sum(
                a != b for a, b in zip(
                    alice[start : start + block_size],
                    bob[start : start + block_size],
                    strict=True,
                )
            )
            rates.append(errs / block_size)
        return rates

    @staticmethod
    def _max_error_burst(alice: list[int], bob: list[int]) -> int:
        max_run = 0
        current = 0
        for a, b in zip(alice, bob, strict=True):
            if a != b:
                current += 1
                max_run = max(max_run, current)
            else:
                current = 0
        return max_run

    # ── Error correction ───────────────────────────────────────────────────

    @staticmethod
    def _parity(bits: list[int], indices: list[int]) -> int:
        p = 0
        for i in indices:
            p ^= bits[i]
        return p

    def _reconcile(
        self, alice_bits: list[int], bob_bits: list[int]
    ) -> tuple[list[int], int]:
        """Cascade-style parity reconciliation over public parities only.

        Runs several passes; each pass partitions the (re-shuffled) key into
        blocks and, for every block whose parity disagrees with Alice's
        announced parity, locates one error by binary search over Alice's
        sub-block parities. Alice's bits are consulted exclusively through
        parities — exactly the information she would announce over the
        classical channel. Every announced parity counts as one leaked bit.

        Blocks with an even number of errors survive a pass; the growing,
        re-shuffled blocks of later passes catch nearly all of them, and the
        hash-verification step in :meth:`run` catches the remainder.
        """
        n = len(alice_bits)
        corrected = bob_bits[:]
        leaked = 0
        order = list(range(n))
        block_size = 8
        for pass_no in range(4):
            if pass_no > 0:
                self._rng.shuffle(order)  # public, shared permutation
                block_size = min(n, block_size * 2)
            for start in range(0, n, block_size):
                block = order[start : start + block_size]
                leaked += 1
                if self._parity(alice_bits, block) == self._parity(corrected, block):
                    continue
                lo, hi = 0, len(block)
                while hi - lo > 1:
                    mid = (lo + hi) // 2
                    leaked += 1
                    if (
                        self._parity(alice_bits, block[lo:mid])
                        != self._parity(corrected, block[lo:mid])
                    ):
                        hi = mid
                    else:
                        lo = mid
                corrected[block[lo]] ^= 1
        return corrected, leaked

    # ── Verification & privacy amplification ──────────────────────────────

    @staticmethod
    def _pack_bits(bits: list[int]) -> bytes:
        padded = bits + [0] * ((-len(bits)) % 8)
        return bytes(
            sum(padded[i + j] << (7 - j) for j in range(8))
            for i in range(0, len(padded), 8)
        )

    @classmethod
    def _key_digest(cls, bits: list[int]) -> bytes:
        return hashlib.blake2b(
            cls._pack_bits(bits),
            digest_size=_VERIFICATION_TAG_BITS // 8,
            person=b"qkdsec-verify",
        ).digest()

    def _privacy_amplify(
        self, bits: list[int], qber: float, leaked_bits: int
    ) -> bytes:
        """Privacy amplification sized from the remaining entropy budget.

        Output length is ``min(256, n - n*h(QBER) - leaked_bits)`` rounded
        down to whole bytes: Eve's information is bounded by the binary
        entropy of the estimated QBER, and every parity announced during
        reconciliation (plus the verification tag) is subtracted. Returns
        ``b""`` when nothing extractable remains.
        """
        n = len(bits)
        eve_bound = math.ceil(n * _binary_entropy(qber))
        secure_bits = n - eve_bound - leaked_bits
        out_bits = min(256, (secure_bits // 8) * 8)
        if out_bits <= 0:
            return b""
        return hashlib.blake2b(
            self._pack_bits(bits), digest_size=out_bits // 8
        ).digest()
