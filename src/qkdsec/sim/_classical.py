"""Classical probabilistic simulation of the BB84 quantum channel.

No external dependencies. Faster than the Qiskit backend; used as the default
fallback when ``qiskit-aer`` is not installed.
"""

import random
from typing import Optional


class ClassicalQuantumChannel:
    """Probabilistic model of BB84 quantum channel (no Qiskit required).

    Parameters
    ----------
    error_rate : float
        Background QBER from channel noise.
    eavesdrop : bool
        Simulate an intercept-resend eavesdropper.
    eavesdrop_fraction : float
        Fraction of qubits Eve intercepts (0.0 to 1.0).
    rng : random.Random, optional
        Randomness source. Defaults to ``random.SystemRandom()`` (OS
        entropy); pass a seeded ``random.Random`` for reproducible runs.
    """

    def __init__(
        self,
        error_rate: float = 0.01,
        eavesdrop: bool = False,
        eavesdrop_fraction: float = 1.0,
        rng: Optional[random.Random] = None,
    ):
        if not 0.0 <= error_rate <= 0.5:
            raise ValueError("error_rate must be between 0.0 and 0.5")
        if not 0.0 <= eavesdrop_fraction <= 1.0:
            raise ValueError("eavesdrop_fraction must be between 0.0 and 1.0")
        self.error_rate = error_rate
        self.eavesdrop = eavesdrop
        self.eavesdrop_fraction = eavesdrop_fraction
        self._rng = rng if rng is not None else random.SystemRandom()

    def transmit(
        self, alice_bits: list[int], alice_bases: list[int]
    ) -> tuple[list[int], list[int]]:
        rng = self._rng
        n = len(alice_bits)
        bob_bases = [rng.randrange(2) for _ in range(n)]
        bob_bits = []

        for i in range(n):
            transmitted_bit = alice_bits[i]
            transmitted_basis = alice_bases[i]

            if self.eavesdrop and rng.random() < self.eavesdrop_fraction:
                eve_basis = rng.randrange(2)
                if eve_basis == alice_bases[i]:
                    eve_bit = alice_bits[i]
                else:
                    eve_bit = rng.randrange(2)
                transmitted_bit = eve_bit
                transmitted_basis = eve_basis

            if bob_bases[i] == transmitted_basis:
                bit = transmitted_bit
            else:
                bit = rng.randrange(2)

            if rng.random() < self.error_rate:
                bit ^= 1

            bob_bits.append(bit)

        return bob_bits, bob_bases
