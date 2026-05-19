from abc import ABC, abstractmethod


class Channel(ABC):
    @abstractmethod
    def expectations(self) -> dict[str, float]:
        ...

    def single_photon_yield(self) -> float:
        return 1.0

    def total_yield(self) -> float:
        return self.single_photon_yield()

    def total_qber(self) -> float:
        zz = self.expectations()["ZZ"]
        return (1.0 - zz) / 2.0
