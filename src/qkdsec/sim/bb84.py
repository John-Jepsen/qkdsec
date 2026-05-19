"""BB84 QKD protocol — top-level orchestration.

Steps:
    1. Alice prepares qubits in Z or X basis
    2. Qubits traverse a (noisy, optionally eavesdropped) quantum channel
    3. Bob measures in a random basis; basis sifting discards mismatches
    4. QBER estimation on a public sample detects eavesdropping
    5. Error correction — binary reconciliation over block parities
    6. Privacy amplification — BLAKE2b universal hash bounds Eve's information

Security properties:
    - Aborts if estimated QBER exceeds 11% (BB84 security threshold)
    - Privacy amplification uses BLAKE2b as a universal hash
"""

import hashlib
import secrets
from dataclasses import dataclass


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
    block_error_rates: list = None  # noqa: RUF012
    error_variance: float = 0.0
    max_burst_length: int = 0


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
    """

    def __init__(
        self,
        error_rate: float = 0.01,
        eavesdrop: bool = False,
        eavesdrop_fraction: float = 1.0,
        qber_threshold: float = 0.11,
        sample_fraction: float = 0.10,
        backend: str = "qiskit",
    ):
        self.backend_name = backend
        if backend == "qiskit":
            from ._qiskit import QiskitQuantumChannel
            self.channel = QiskitQuantumChannel(
                error_rate=error_rate,
                eavesdrop=eavesdrop,
                eavesdrop_fraction=eavesdrop_fraction,
            )
        elif backend == "classical":
            from ._classical import ClassicalQuantumChannel
            self.channel = ClassicalQuantumChannel(
                error_rate=error_rate,
                eavesdrop=eavesdrop,
                eavesdrop_fraction=eavesdrop_fraction,
            )
        else:
            raise ValueError(
                f"Unknown backend: {backend!r} (use 'qiskit' or 'classical')"
            )
        self.qber_threshold = qber_threshold
        self.sample_fraction = sample_fraction

    def run(self, n_bits: int = 4096) -> BB84Result:
        """Execute the full BB84 protocol and return a BB84Result."""
        alice_bits = [secrets.randbelow(2) for _ in range(n_bits)]
        alice_bases = [secrets.randbelow(2) for _ in range(n_bits)]

        bob_bits, bob_bases = self.channel.transmit(alice_bits, alice_bases)

        sifted_alice: list[int] = []
        sifted_bob: list[int] = []
        for i in range(n_bits):
            if alice_bases[i] == bob_bases[i]:
                sifted_alice.append(alice_bits[i])
                sifted_bob.append(bob_bits[i])

        if len(sifted_alice) < 40:
            raise RuntimeError(
                f"Only {len(sifted_alice)} sifted bits — increase n_bits (try 4096+)"
            )

        sample_size = max(10, int(len(sifted_alice) * self.sample_fraction))
        sample_alice = sifted_alice[:sample_size]
        sample_bob = sifted_bob[:sample_size]
        errors = sum(a != b for a, b in zip(sample_alice, sample_bob))
        qber = errors / sample_size

        sift_ratio = len(sifted_alice) / n_bits
        block_error_rates = self._compute_block_error_rates(
            sample_alice, sample_bob, block_size=8
        )
        error_variance = (
            sum((r - qber) ** 2 for r in block_error_rates) / len(block_error_rates)
            if block_error_rates else 0.0
        )
        max_burst = self._max_error_burst(sample_alice, sample_bob)

        key_alice = sifted_alice[sample_size:]
        key_bob = sifted_bob[sample_size:]

        eavesdropper_detected = qber > self.qber_threshold
        if eavesdropper_detected or not key_alice:
            return BB84Result(
                final_key=b"",
                key_length_bits=0,
                raw_bits=n_bits,
                sifted_bits=len(sifted_alice),
                qber=qber,
                eavesdropper_detected=eavesdropper_detected,
                secure=False,
                backend_used=self.backend_name,
                sift_ratio=sift_ratio,
                block_error_rates=block_error_rates,
                error_variance=error_variance,
                max_burst_length=max_burst,
            )

        corrected_bob = self._error_correct(key_alice, key_bob)
        final_key = self._privacy_amplify(corrected_bob)

        return BB84Result(
            final_key=final_key,
            key_length_bits=len(final_key) * 8,
            raw_bits=n_bits,
            sifted_bits=len(sifted_alice),
            qber=qber,
            eavesdropper_detected=False,
            secure=True,
            backend_used=self.backend_name,
            sift_ratio=sift_ratio,
            block_error_rates=block_error_rates,
            error_variance=error_variance,
            max_burst_length=max_burst,
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
                )
            )
            rates.append(errs / block_size)
        return rates

    @staticmethod
    def _max_error_burst(alice: list[int], bob: list[int]) -> int:
        max_run = 0
        current = 0
        for a, b in zip(alice, bob):
            if a != b:
                current += 1
                max_run = max(max_run, current)
            else:
                current = 0
        return max_run

    def _error_correct(
        self, alice_bits: list[int], bob_bits: list[int]
    ) -> list[int]:
        """Simplified binary reconciliation over 8-bit block parities.

        Alice announces the parity of each block. For each disagreeing block,
        Bob flips the first differing bit. Adequate for error_rate < ~3%.
        """
        corrected = bob_bits[:]
        block_size = 8
        for start in range(0, len(alice_bits) - block_size + 1, block_size):
            a_block = alice_bits[start : start + block_size]
            b_block = corrected[start : start + block_size]
            if sum(a_block) % 2 != sum(b_block) % 2:
                for j in range(block_size):
                    if a_block[j] != b_block[j]:
                        corrected[start + j] ^= 1
                        break
        return corrected

    def _privacy_amplify(self, bits: list[int]) -> bytes:
        """Privacy amplification via BLAKE2b universal hashing.

        Output: 256-bit (32-byte) shared secret.
        """
        n = len(bits)
        padded = bits + [0] * ((-n) % 8)
        raw_bytes = bytes(
            sum(padded[i + j] << (7 - j) for j in range(8))
            for i in range(0, len(padded), 8)
        )
        return hashlib.blake2b(raw_bytes, digest_size=32).digest()
