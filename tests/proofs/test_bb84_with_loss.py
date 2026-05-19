import math

import pytest

from qkdsec.proofs import BB84, LossChannel, key_rate


def _shor_preskill(q: float) -> float:
    if q <= 0.0:
        return 1.0
    if q >= 0.5:
        return 0.0
    h = -q * math.log2(q) - (1.0 - q) * math.log2(1.0 - q)
    return max(0.0, 1.0 - 2.0 * h)


def test_lossless_matches_depolarizing():
    result = key_rate(BB84(), LossChannel(qber=0.05, loss_db=0.0))
    assert abs(result.r_lower - _shor_preskill(0.05)) < 0.01


@pytest.mark.parametrize("loss_db", [2.0, 10.0, 20.0])
def test_rate_scales_with_transmission(loss_db):
    q = 0.03
    result = key_rate(BB84(), LossChannel(qber=q, loss_db=loss_db))
    eta = 10.0 ** (-loss_db / 10.0)
    expected = eta * _shor_preskill(q)
    assert result.sdp_status in ("optimal", "optimal_inaccurate")
    assert abs(result.r_lower - expected) < 0.01 * max(expected, 1e-4)


@pytest.mark.parametrize(
    "distance_km, qber",
    [(10, 0.02), (50, 0.02), (100, 0.02)],
)
def test_rate_vs_distance_1550nm(distance_km, qber):
    alpha_db_per_km = 0.2
    eta_d = 0.93
    channel_loss_db = alpha_db_per_km * distance_km
    detector_loss_db = -10.0 * math.log10(eta_d)
    total_loss_db = channel_loss_db + detector_loss_db

    result = key_rate(BB84(), LossChannel(qber=qber, loss_db=total_loss_db))

    eta = 10.0 ** (-total_loss_db / 10.0)
    expected = eta * _shor_preskill(qber)
    assert result.r_lower > 0
    assert abs(result.r_lower - expected) / expected < 0.02
