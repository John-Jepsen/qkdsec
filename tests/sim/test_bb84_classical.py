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
    # Even without Eve, a high channel error rate should trigger abort.
    # Seeded: with 10% QBER sampling, an unseeded run at 0.15 lands under
    # the 0.11 threshold ~3% of the time and flakes.
    result = BB84Protocol(
        error_rate=0.15,
        backend="classical",
        seed=2,
    ).run(n_bits=4096)
    assert not result.secure
    assert result.eavesdropper_detected


def test_seeded_runs_are_reproducible():
    r1 = BB84Protocol(error_rate=0.01, backend="classical", seed=1234).run(4096)
    r2 = BB84Protocol(error_rate=0.01, backend="classical", seed=1234).run(4096)
    assert r1.final_key == r2.final_key
    assert r1.final_key != b""
    assert r1.qber == r2.qber
    assert r1.leaked_bits == r2.leaked_bits


def test_reconciliation_verified_and_leak_accounted():
    result = BB84Protocol(
        error_rate=0.02, backend="classical", seed=7
    ).run(n_bits=4096)
    assert result.secure
    assert result.reconciliation_verified
    # Announced parities plus the verification tag must all be accounted
    assert result.leaked_bits > result.sifted_bits // 10


def test_reconcile_corrects_scattered_errors():
    proto = BB84Protocol(backend="classical", seed=3)
    alice = [(i * 7 + 3) % 2 for i in range(1000)]
    bob = alice[:]
    for i in (5, 123, 124, 411, 700, 999):  # includes an adjacent pair
        bob[i] ^= 1
    corrected, leaked = proto._reconcile(alice, bob)
    assert corrected == alice
    # At minimum one parity per block per pass was announced
    assert leaked >= 1000 // 8


def test_sub_permille_error_rate_not_quantized_to_zero():
    # Regression: probabilities were once quantized to 1/1000 granularity,
    # silently turning error_rate < 0.001 into exactly 0.
    import random

    from qkdsec.sim._classical import ClassicalQuantumChannel

    chan = ClassicalQuantumChannel(error_rate=5e-4, rng=random.Random(99))
    alice_bits = [0] * 40_000
    alice_bases = [0] * 40_000
    bob_bits, bob_bases = chan.transmit(alice_bits, alice_bases)
    flips = sum(
        b != 0 for b, bb in zip(bob_bits, bob_bases, strict=True) if bb == 0
    )
    assert flips > 0
