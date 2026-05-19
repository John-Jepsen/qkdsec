import math

import pytest

from qkdsec.proofs import BB84, DecoyChannel, key_rate, two_decoy_bounds


def _gain(eta: float, mu: float, Y_0: float) -> float:
    return Y_0 + 1.0 - math.exp(-eta * mu)


def _qber(eta: float, mu: float, Y_0: float, e_misalign: float, e_0: float = 0.5) -> float:
    sig = (1.0 - math.exp(-eta * mu)) * e_misalign
    bg = e_0 * Y_0
    return (sig + bg) / _gain(eta, mu, Y_0)


def test_bounds_y1_in_valid_range():
    mu, nu = 0.5, 0.1
    eta = 0.01
    Y_0 = 1e-6
    Q_mu = _gain(eta, mu, Y_0)
    Q_nu = _gain(eta, nu, Y_0)
    Q_0 = Y_0
    E_nu = _qber(eta, nu, Y_0, e_misalign=0.015)

    b = two_decoy_bounds(
        mu_signal=mu, mu_decoy=nu,
        gain_signal=Q_mu, gain_decoy=Q_nu, gain_vacuum=Q_0,
        qber_decoy=E_nu,
    )

    assert 0.0 <= b.Y_1_lower <= 1.0
    assert b.Y_1_lower < eta * 1.05
    assert b.Y_1_lower > eta * 0.5
    assert 0.0 <= b.e_1_upper <= 0.5


def test_bounds_degrade_with_dark_count():
    mu, nu = 0.5, 0.1
    eta = 0.01
    e_align = 0.015

    clean = two_decoy_bounds(
        mu_signal=mu, mu_decoy=nu,
        gain_signal=_gain(eta, mu, 1e-6),
        gain_decoy=_gain(eta, nu, 1e-6),
        gain_vacuum=1e-6,
        qber_decoy=_qber(eta, nu, 1e-6, e_align),
    )
    dark = two_decoy_bounds(
        mu_signal=mu, mu_decoy=nu,
        gain_signal=_gain(eta, mu, 1e-3),
        gain_decoy=_gain(eta, nu, 1e-3),
        gain_vacuum=1e-3,
        qber_decoy=_qber(eta, nu, 1e-3, e_align),
    )
    assert dark.e_1_upper >= clean.e_1_upper


@pytest.mark.parametrize(
    "distance_km, eta_d, expected_min_rate",
    [
        (50, 0.10, 1e-4),
        (100, 0.10, 1e-6),
    ],
)
def test_certified_rate_at_distance_realistic(distance_km, eta_d, expected_min_rate):
    alpha_db_per_km = 0.2
    eta_chan = 10.0 ** (-alpha_db_per_km * distance_km / 10.0)
    eta = eta_chan * eta_d

    mu = 0.5
    nu = 0.1
    Y_0 = 1e-6
    e_misalign = 0.015

    chan = DecoyChannel(
        mu_signal=mu,
        mu_decoy=nu,
        gain_signal=_gain(eta, mu, Y_0),
        gain_decoy=_gain(eta, nu, Y_0),
        gain_vacuum=Y_0,
        qber_signal=_qber(eta, mu, Y_0, e_misalign),
        qber_decoy=_qber(eta, nu, Y_0, e_misalign),
    )

    result = key_rate(BB84(), chan)
    assert result.sdp_status in ("optimal", "optimal_inaccurate")
    assert result.r_lower > expected_min_rate, (
        f"distance={distance_km}km eta_d={eta_d}: r_lower={result.r_lower:.2e}"
    )


def test_decoy_aborts_at_excessive_loss():
    eta = 1e-6
    mu, nu = 0.5, 0.1
    Y_0 = 1e-4
    chan = DecoyChannel(
        mu_signal=mu, mu_decoy=nu,
        gain_signal=_gain(eta, mu, Y_0),
        gain_decoy=_gain(eta, nu, Y_0),
        gain_vacuum=Y_0,
        qber_signal=_qber(eta, mu, Y_0, 0.02),
        qber_decoy=_qber(eta, nu, Y_0, 0.02),
    )
    result = key_rate(BB84(), chan)
    assert result.r_lower == 0.0
