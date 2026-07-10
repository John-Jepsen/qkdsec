import numpy as np

from ..channels.base import Channel
from .base import Protocol

_Z = np.diag([1.0, -1.0])
_X = np.array([[0.0, 1.0], [1.0, 0.0]])
_P0 = np.array([[1.0, 0.0], [0.0, 0.0]])
_P1 = np.array([[0.0, 0.0], [0.0, 1.0]])


def _h(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return float(-p * np.log2(p) - (1.0 - p) * np.log2(1.0 - p))


class BB84(Protocol):
    """BB84 protocol model for the key-rate SDP.

    Parameters
    ----------
    f_ec : float
        Error-correction inefficiency. Real reconciliation codes leak
        ``f_ec * h(QBER)`` bits per pulse; the Shannon limit is 1.0, and
        practical Cascade/LDPC implementations sit around 1.1-1.2. The
        default 1.16 keeps the certified rate honest for deployments;
        pass 1.0 to reproduce ideal-reconciliation literature values.
    """

    dim_a = 2
    dim_b = 2

    def __init__(self, f_ec: float = 1.16):
        if f_ec < 1.0:
            raise ValueError("f_ec must be >= 1.0 (Shannon limit)")
        self.f_ec = f_ec

    def observables(self) -> dict[str, np.ndarray]:
        return {
            "ZZ": np.kron(_Z, _Z),
            "XX": np.kron(_X, _X),
        }

    def key_projectors(self) -> list[np.ndarray]:
        return [_P0, _P1]

    def leakage(self, channel: Channel) -> float:
        return channel.total_yield() * self.f_ec * _h(channel.total_qber())
