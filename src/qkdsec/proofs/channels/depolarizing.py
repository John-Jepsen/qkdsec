from dataclasses import dataclass

from .base import Channel


@dataclass
class DepolarizingChannel(Channel):
    qber: float

    def expectations(self) -> dict[str, float]:
        c = 1.0 - 2.0 * self.qber
        return {"ZZ": c, "XX": c}
