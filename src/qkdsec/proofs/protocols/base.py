from abc import ABC, abstractmethod

import numpy as np


class Protocol(ABC):
    dim_a: int
    dim_b: int

    @abstractmethod
    def observables(self) -> dict[str, np.ndarray]:
        ...

    @abstractmethod
    def key_projectors(self) -> list[np.ndarray]:
        ...

    @abstractmethod
    def leakage(self, channel) -> float:
        ...
