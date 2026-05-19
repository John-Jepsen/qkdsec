from qkdsec.proofs import BB84, LossChannel, key_rate


def test_finite_below_asymptotic():
    chan = LossChannel(qber=0.02, loss_db=2.0)
    asymp = key_rate(BB84(), chan)
    finite = key_rate(BB84(), chan, n_signals=10_000_000)
    assert finite.r_lower < asymp.r_lower
    assert finite.r_lower > 0


def test_finite_approaches_asymptotic():
    chan = LossChannel(qber=0.02, loss_db=2.0)
    asymp = key_rate(BB84(), chan)
    near = key_rate(BB84(), chan, n_signals=10_000_000_000_000)
    assert abs(near.r_lower - asymp.r_lower) / asymp.r_lower < 0.001


def test_finite_aborts_when_correction_dominates():
    chan = LossChannel(qber=0.10, loss_db=2.0)
    tiny = key_rate(BB84(), chan, n_signals=1_000)
    assert tiny.r_lower == 0.0
