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
    dim_a = 2
    dim_b = 2

    def observables(self) -> dict[str, np.ndarray]:
        return {
            "ZZ": np.kron(_Z, _Z),
            "XX": np.kron(_X, _X),
        }

    def key_projectors(self) -> list[np.ndarray]:
        return [_P0, _P1]

    def leakage(self, channel: Channel) -> float:
        return channel.total_yield() * _h(channel.total_qber())
