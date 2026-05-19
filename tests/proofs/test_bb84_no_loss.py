import numpy as np
import pytest

from qkdsec.proofs import BB84, DepolarizingChannel, key_rate


def _shor_preskill(q: float) -> float:
    if q <= 0.0:
        return 1.0
    if q >= 0.5:
        return 0.0
    h = -q * np.log2(q) - (1.0 - q) * np.log2(1.0 - q)
    return max(0.0, 1.0 - 2.0 * h)


@pytest.mark.parametrize("qber", [0.005, 0.01, 0.03, 0.05, 0.08, 0.10])
def test_bb84_matches_shor_preskill(qber):
    result = key_rate(BB84(), DepolarizingChannel(qber=qber))
    expected = _shor_preskill(qber)
    assert result.sdp_status in ("optimal", "optimal_inaccurate")
    assert abs(result.r_lower - expected) < 0.01, (
        f"qber={qber}: got {result.r_lower:.4f}, expected {expected:.4f}"
    )


def test_bb84_aborts_above_threshold():
    result = key_rate(BB84(), DepolarizingChannel(qber=0.20))
    assert result.r_lower == 0.0
