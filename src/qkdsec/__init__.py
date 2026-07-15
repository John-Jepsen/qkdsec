"""qkdsec — a developer toolkit for Quantum Key Distribution.

Subpackages:
    qkdsec.proofs   — numerical security proofs (key-rate lower bounds)
    qkdsec.sim      — BB84 simulator (Qiskit + classical backends)
    qkdsec.client   — ETSI GS QKD 014 REST client

Each subpackage may require optional dependencies. See README.md for install
options (e.g., ``pip install qkdsec[proofs]``).
"""

try:
    # Written by setuptools-scm at build/install time; derived from git tags.
    from qkdsec._version import __version__
except ImportError:
    try:
        from importlib.metadata import version as _dist_version

        __version__ = _dist_version("qkdsec")
    except Exception:
        __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
