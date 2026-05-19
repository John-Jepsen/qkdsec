"""Qiskit-backed quantum channel for BB84 simulation.

Each qubit is prepared with real gate operations (X, H) and measured through
the Aer simulator. Channel noise is modeled as a single-qubit depolarizing
error applied via an identity gate inserted between preparation and
measurement.

Requires the ``sim`` extra: ``pip install qkdsec[sim]``.
"""

import secrets

try:
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, depolarizing_error
except ImportError as e:
    raise ImportError(
        "qkdsec.sim qiskit backend requires extra dependencies. "
        "Install with: pip install qkdsec[sim]"
    ) from e

_BATCH_SIZE = 256


class QiskitQuantumChannel:
    """Quantum channel backed by IBM Qiskit Aer simulator.

    Parameters
    ----------
    error_rate : float
        Background QBER from channel noise. Mapped to depolarizing probability
        p = 3*error_rate/2 so that the resulting bit-flip rate matches.
    eavesdrop : bool
        Simulate an intercept-resend eavesdropper using two-circuit model.
    eavesdrop_fraction : float
        Fraction of qubits Eve intercepts (0.0 to 1.0). Only used when
        eavesdrop=True. Default 1.0 (full intercept-resend).
    """

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

        self._ideal_backend = AerSimulator()
        self._noisy_backend = self._build_noisy_backend() if error_rate > 0 else None

    def _build_noisy_backend(self) -> "AerSimulator":
        noise_model = NoiseModel()
        p = min(1.0, 3 * self.error_rate / 2)
        noise_model.add_all_qubit_quantum_error(
            depolarizing_error(p, 1), ["id"]
        )
        return AerSimulator(noise_model=noise_model)

    def transmit(
        self, alice_bits: list[int], alice_bases: list[int]
    ) -> tuple[list[int], list[int]]:
        n = len(alice_bits)
        bob_bases = [secrets.randbelow(2) for _ in range(n)]

        if self.eavesdrop:
            if self.eavesdrop_fraction >= 1.0:
                eve_bases = [secrets.randbelow(2) for _ in range(n)]
                eve_bits = self._run_circuit(
                    alice_bits, alice_bases, eve_bases, noisy=False
                )
                bob_bits = self._run_circuit(
                    eve_bits, eve_bases, bob_bases, noisy=True
                )
            else:
                intercepted = [
                    secrets.randbelow(1000) < int(self.eavesdrop_fraction * 1000)
                    for _ in range(n)
                ]
                eve_bases = [secrets.randbelow(2) for _ in range(n)]

                eve_bits = self._run_circuit(
                    alice_bits, alice_bases, eve_bases, noisy=False
                )
                clean_bits = self._run_circuit(
                    alice_bits, alice_bases, bob_bases, noisy=True
                )
                eve_resend = self._run_circuit(
                    eve_bits, eve_bases, bob_bases, noisy=True
                )

                bob_bits = [
                    eve_resend[i] if intercepted[i] else clean_bits[i]
                    for i in range(n)
                ]
        else:
            bob_bits = self._run_circuit(
                alice_bits, alice_bases, bob_bases, noisy=True
            )

        return bob_bits, bob_bases

    def _run_circuit(
        self,
        sender_bits: list[int],
        sender_bases: list[int],
        receiver_bases: list[int],
        noisy: bool = True,
    ) -> list[int]:
        n = len(sender_bits)
        all_results: list[int] = []

        for start in range(0, n, _BATCH_SIZE):
            end = min(start + _BATCH_SIZE, n)
            batch_size = end - start

            qc = QuantumCircuit(batch_size, batch_size)

            for i in range(batch_size):
                idx = start + i
                if sender_bits[idx] == 1:
                    qc.x(i)
                if sender_bases[idx] == 1:
                    qc.h(i)

            if noisy and self.error_rate > 0:
                for i in range(batch_size):
                    qc.id(i)

            for i in range(batch_size):
                idx = start + i
                if receiver_bases[idx] == 1:
                    qc.h(i)
                qc.measure(i, i)

            backend = (
                self._noisy_backend
                if (noisy and self._noisy_backend)
                else self._ideal_backend
            )
            job = backend.run(qc, shots=1)
            counts = job.result().get_counts()

            bitstring = list(counts.keys())[0].zfill(batch_size)
            bits = [int(b) for b in reversed(bitstring)]
            all_results.extend(bits[:batch_size])

        return all_results
