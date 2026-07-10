"""Numerical security proofs for QKD via semidefinite programming.

Requires the ``proofs`` extra: ``pip install qkdsec[proofs]``.

Example:
    >>> from qkdsec.proofs import key_rate, BB84, DepolarizingChannel
    >>> result = key_rate(BB84(), DepolarizingChannel(qber=0.03))
    >>> print(result.r_lower, result.secure)
"""

try:
    import cvxpy  # noqa: F401
    import numpy  # noqa: F401
    import scipy  # noqa: F401
except ImportError as e:
    raise ImportError(
        "qkdsec.proofs requires extra dependencies. "
        "Install with: pip install qkdsec[proofs]"
    ) from e

from ._api import key_rate
from ._types import KeyRateResult
from .channels import Channel, DecoyChannel, DepolarizingChannel, LossChannel
from .decoy_state import DecoyBounds, two_decoy_bounds
from .finite_size import qber_statistical_inflation, tomamichel_correction
from .protocols import BB84, Protocol
from .sdp import solve_key_rate_sdp

__all__ = [
    "BB84",
    "Channel",
    "DecoyBounds",
    "DecoyChannel",
    "DepolarizingChannel",
    "KeyRateResult",
    "LossChannel",
    "Protocol",
    "key_rate",
    "qber_statistical_inflation",
    "solve_key_rate_sdp",
    "tomamichel_correction",
    "two_decoy_bounds",
]
