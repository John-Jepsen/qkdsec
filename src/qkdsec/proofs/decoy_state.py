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
    """Vacuum + weak-decoy bounds on single-photon yield and error rate
    (Ma, Qi, Zhao & Lo, PRA 72, 012326, 2005).

    All clamping is in the conservative (security-preserving) direction:
    a lower bound is never raised and an upper bound is never lowered.
    Statistically inconsistent inputs therefore degrade the certified rate
    rather than inflate it.
    """
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
        # A negative value means the inputs are statistically inconsistent
        # (background errors exceed all observed errors). Clamping an
        # *upper* bound up to 0 would certify zero single-photon errors —
        # the most optimistic possible reading — so fail conservative
        # instead: assume the worst (0.5) and let the key rate go to zero.
        e_1_upper = 0.5 if e_1_upper < 0.0 else min(0.5, e_1_upper)
    else:
        e_1_upper = 0.5

    return DecoyBounds(
        Y_0=Y_0,
        Y_1_lower=Y_1_lower,
        Q_1_lower=Q_1_lower,
        e_1_upper=e_1_upper,
    )
