import math


def tomamichel_correction(n_detected: int, eps_security: float) -> float:
    if n_detected <= 0:
        return float("inf")
    return 7.0 * math.sqrt(math.log2(2.0 / eps_security) / n_detected)


def qber_statistical_inflation(n_detected: int, eps_security: float) -> float:
    if n_detected <= 0:
        return float("inf")
    return math.sqrt(math.log(1.0 / eps_security) / (2.0 * n_detected))
