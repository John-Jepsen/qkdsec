import math
from dataclasses import dataclass


@dataclass
class DecoyBounds:
    Y_0: float
    Y_1_lower: float
    Q_1_lower: float
    e_1_upper: float


def two_decoy_bounds(
    mu_signal: float,
    mu_decoy: float,
    gain_signal: float,
    gain_decoy: float,
    gain_vacuum: float,
    qber_decoy: float,
    e_0: float = 0.5,
) -> DecoyBounds:
    if not (mu_signal > mu_decoy > 0.0):
        raise ValueError("require mu_signal > mu_decoy > 0")

    mu = mu_signal
    nu = mu_decoy
    Y_0 = max(0.0, gain_vacuum)

    Y_1_lower = (mu / (mu * nu - nu ** 2)) * (
        gain_decoy * math.exp(nu)
        - gain_signal * math.exp(mu) * (nu ** 2 / mu ** 2)
        - ((mu ** 2 - nu ** 2) / mu ** 2) * Y_0
    )
    Y_1_lower = max(0.0, Y_1_lower)

    Q_1_lower = mu * math.exp(-mu) * Y_1_lower

    if Y_1_lower > 0.0:
        e_1_upper = (
            qber_decoy * gain_decoy * math.exp(nu) - e_0 * Y_0
        ) / (Y_1_lower * nu)
        e_1_upper = max(0.0, min(0.5, e_1_upper))
    else:
        e_1_upper = 0.5

    return DecoyBounds(
        Y_0=Y_0,
        Y_1_lower=Y_1_lower,
        Q_1_lower=Q_1_lower,
        e_1_upper=e_1_upper,
    )
