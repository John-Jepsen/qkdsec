"""Smoke tests for the Qiskit Aer backend.

Skipped automatically when qiskit-aer is not installed (the ``sim`` extra).
"""

import pytest

pytest.importorskip("qiskit_aer")

from qkdsec.sim import BB84Protocol


def test_qiskit_clean_channel_yields_secure_key():
    result = BB84Protocol(
        error_rate=0.005, backend="qiskit", seed=7
    ).run(n_bits=2048)
    assert result.backend_used == "qiskit"
    assert result.secure
    assert result.reconciliation_verified
    assert result.qber < 0.05
    assert 0 < result.key_length_bits <= 256


def test_qiskit_eavesdropper_detected():
    result = BB84Protocol(
        error_rate=0.005, eavesdrop=True, backend="qiskit", seed=7
    ).run(n_bits=2048)
    assert not result.secure
    assert result.eavesdropper_detected
    # Intercept-resend produces ~25% QBER
    assert result.qber > 0.15
