from dataclasses import dataclass, field

from ..decoy_state import DecoyBounds, two_decoy_bounds
from .base import Channel


@dataclass
class DecoyChannel(Channel):
    mu_signal: float
    mu_decoy: float
    gain_signal: float
    gain_decoy: float
    gain_vacuum: float
    qber_signal: float
    qber_decoy: float
    e_0: float = 0.5

    bounds: DecoyBounds = field(init=False)

    def __post_init__(self) -> None:
        self.bounds = two_decoy_bounds(
            mu_signal=self.mu_signal,
            mu_decoy=self.mu_decoy,
            gain_signal=self.gain_signal,
            gain_decoy=self.gain_decoy,
            gain_vacuum=self.gain_vacuum,
            qber_decoy=self.qber_decoy,
            e_0=self.e_0,
        )

    def expectations(self) -> dict[str, float]:
        c = 1.0 - 2.0 * self.bounds.e_1_upper
        return {"ZZ": c, "XX": c}

    def single_photon_yield(self) -> float:
        return self.bounds.Q_1_lower

    def total_yield(self) -> float:
        return self.gain_signal

    def total_qber(self) -> float:
        return self.qber_signal
