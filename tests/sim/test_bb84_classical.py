from qkdsec.sim import BB84Protocol


def test_clean_channel_yields_secure_key():
    result = BB84Protocol(error_rate=0.005, backend="classical").run(n_bits=4096)
    assert result.secure
    assert result.qber < 0.05
    assert result.key_length_bits == 256
    assert len(result.final_key) == 32


def test_eavesdropper_detected():
    result = BB84Protocol(
        error_rate=0.005,
        eavesdrop=True,
        backend="classical",
    ).run(n_bits=4096)
    assert not result.secure
    assert result.eavesdropper_detected
    # Intercept-resend produces ~25% QBER
    assert result.qber > 0.15


def test_sifting_yields_roughly_half():
    result = BB84Protocol(error_rate=0.0, backend="classical").run(n_bits=8192)
    # Basis matching is 50% in expectation; allow generous slack
    assert 0.4 < result.sift_ratio < 0.6


def test_invalid_backend_raises():
    import pytest
    with pytest.raises(ValueError):
        BB84Protocol(backend="not-a-real-backend")


def test_qber_threshold_aborts_below_eve_level():
    # Even without Eve, a high channel error rate should trigger abort
    result = BB84Protocol(
        error_rate=0.15,
        backend="classical",
    ).run(n_bits=4096)
    assert not result.secure
    assert result.eavesdropper_detected
