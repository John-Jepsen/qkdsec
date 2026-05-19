"""qkdsec — a developer toolkit for Quantum Key Distribution.

Subpackages:
    qkdsec.proofs   — numerical security proofs (key-rate lower bounds)
    qkdsec.sim      — BB84 simulator (Qiskit + classical backends)
    qkdsec.client   — ETSI GS QKD 014 REST client

Each subpackage may require optional dependencies. See README.md for install
options (e.g., ``pip install qkdsec[proofs]``).
"""

__version__ = "0.2.0"

__all__ = ["__version__"]
