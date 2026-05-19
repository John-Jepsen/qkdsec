"""Classical probabilistic simulation of the BB84 quantum channel.

No external dependencies. Faster than the Qiskit backend; used as the default
fallback when ``qiskit-aer`` is not installed.
"""

import secrets


class ClassicalQuantumChannel:
    """Probabilistic model of BB84 quantum channel (no Qiskit required)."""

    def __init__(
        self,
        error_rate: float = 0.01,
        eavesdrop: bool = False,
        eavesdrop_fraction: float = 1.0,
    ):
        if not 0.0 <= error_rate <= 0.5:
            raise ValueError("error_rate must be between 0.0 and 0.5")
        if not 0.0 <= eavesdrop_fraction <= 1.0:
            raise ValueError("eavesdrop_fraction must be between 0.0 and 1.0")
        self.error_rate = error_rate
        self.eavesdrop = eavesdrop
        self.eavesdrop_fraction = eavesdrop_fraction

    def transmit(
        self, alice_bits: list[int], alice_bases: list[int]
    ) -> tuple[list[int], list[int]]:
        n = len(alice_bits)
        bob_bases = [secrets.randbelow(2) for _ in range(n)]
        bob_bits = []
        noise_threshold = int(self.error_rate * 1000)
        intercept_threshold = int(self.eavesdrop_fraction * 1000)

        for i in range(n):
            transmitted_bit = alice_bits[i]
            transmitted_basis = alice_bases[i]

            if self.eavesdrop and secrets.randbelow(1000) < intercept_threshold:
                eve_basis = secrets.randbelow(2)
                if eve_basis == alice_bases[i]:
                    eve_bit = alice_bits[i]
                else:
                    eve_bit = secrets.randbelow(2)
                transmitted_bit = eve_bit
                transmitted_basis = eve_basis

            if bob_bases[i] == transmitted_basis:
                bit = transmitted_bit
            else:
                bit = secrets.randbelow(2)

            if secrets.randbelow(1000) < noise_threshold:
                bit ^= 1

            bob_bits.append(bit)

        return bob_bits, bob_bases
