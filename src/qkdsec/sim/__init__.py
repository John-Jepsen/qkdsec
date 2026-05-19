"""BB84 QKD protocol simulator.

Two backends are available:

- ``"classical"`` — pure-Python probabilistic simulation. No extra dependencies.
- ``"qiskit"``    — real quantum circuits on IBM Qiskit Aer with depolarizing
  noise. Requires the ``sim`` extra: ``pip install qkdsec[sim]``.

Example:
    >>> from qkdsec.sim import BB84Protocol
    >>> result = BB84Protocol(error_rate=0.01).run(n_bits=4096)
    >>> if result.secure:
    ...     print(result.final_key.hex())
"""

from .bb84 import BB84Protocol, BB84Result

__all__ = ["BB84Protocol", "BB84Result"]
