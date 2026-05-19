from dataclasses import dataclass

from .base import Channel


@dataclass
class LossChannel(Channel):
    qber: float
    loss_db: float

    def expectations(self) -> dict[str, float]:
        c = 1.0 - 2.0 * self.qber
        return {"ZZ": c, "XX": c}

    def single_photon_yield(self) -> float:
        return 10.0 ** (-self.loss_db / 10.0)
