"""Unit tests for individual doctor probes with mocked HTTP."""

import base64

import responses

from qkdsec.client import ETSI014Client
from qkdsec.doctor.probes import (
    ProbeStatus,
    probe_dec_keys_roundtrip,
    probe_enc_keys_caps,
    probe_enc_keys_get,
    probe_enc_keys_post,
    probe_error_contract_400,
    probe_error_contract_404,
    probe_extensions_accepted,
    probe_latency,
    probe_reachability,
    probe_status_fields,
    run_all,
)

BASE = "https://kme.example.com"
SAE = "sae-bob"


def _full_status(**overrides):
    base = {
        "source_KME_ID": "kme-01",
        "target_KME_ID": "kme-02",
        "master_SAE_ID": "sae-alice",
        "slave_SAE_ID": SAE,
        "key_size": 256,
        "stored_key_count": 42,
        "max_key_count": 50,
        "max_key_per_request": 20,
        "max_key_size": 1024,
        "min_key_size": 64,
        "max_SAE_ID_count": 0,
    }
    base.update(overrides)
    return base


def _key_payload(key_id: str, key_bytes: bytes) -> dict:
    return {"key_ID": key_id, "key": base64.b64encode(key_bytes).decode()}


# ── reachability ──────────────────────────────────────────────────────────


@responses.activate
def test_probe_reachability_pass():
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/status",
        json=_full_status(), status=200,
    )
    r = probe_reachability(ETSI014Client(BASE), SAE)
    assert r.status == ProbeStatus.PASS


@responses.activate
def test_probe_reachability_fail():
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/status",
        json={"message": "unauthorized"}, status=401,
    )
    r = probe_reachability(ETSI014Client(BASE), SAE)
    assert r.status == ProbeStatus.FAIL


# ── status fields ─────────────────────────────────────────────────────────


@responses.activate
def test_probe_status_fields_pass():
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/status",
        json=_full_status(), status=200,
    )
    r, raw = probe_status_fields(ETSI014Client(BASE), SAE)
    assert r.status == ProbeStatus.PASS
    assert raw["key_size"] == 256


@responses.activate
def test_probe_status_fields_missing_required_fails():
    incomplete = _full_status()
    del incomplete["min_key_size"]
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/status",
        json=incomplete, status=200,
    )
    r, _ = probe_status_fields(ETSI014Client(BASE), SAE)
    assert r.status == ProbeStatus.FAIL
    assert "min_key_size" in r.details["missing_fields"]


@responses.activate
def test_probe_status_fields_unknown_field_warns():
    extra = _full_status(vendor_undocumented="hello")
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/status",
        json=extra, status=200,
    )
    r, _ = probe_status_fields(ETSI014Client(BASE), SAE)
    assert r.status == ProbeStatus.WARN
    assert "vendor_undocumented" in r.details["unknown_fields"]


@responses.activate
def test_probe_status_fields_type_mismatch_fails():
    bad = _full_status(key_size="256")  # string, not int
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/status",
        json=bad, status=200,
    )
    r, _ = probe_status_fields(ETSI014Client(BASE), SAE)
    assert r.status == ProbeStatus.FAIL
    assert any("key_size" in e for e in r.details["type_errors"])


# ── enc_keys GET / POST ───────────────────────────────────────────────────


@responses.activate
def test_probe_enc_keys_get_pass():
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"keys": [_key_payload("k-1", b"x" * 32)]}, status=200,
    )
    r, kid = probe_enc_keys_get(ETSI014Client(BASE), SAE)
    assert r.status == ProbeStatus.PASS
    assert kid == "k-1"


@responses.activate
def test_probe_enc_keys_get_wrong_size_fails():
    # Ask for 256, KME returns 128 bits
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"keys": [_key_payload("k-1", b"x" * 16)]}, status=200,
    )
    r, _ = probe_enc_keys_get(ETSI014Client(BASE), SAE, size=256)
    assert r.status == ProbeStatus.FAIL


@responses.activate
def test_probe_enc_keys_post_warn_when_unsupported():
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"message": "method not allowed"}, status=405,
    )
    r, _ = probe_enc_keys_post(ETSI014Client(BASE), SAE)
    assert r.status == ProbeStatus.WARN


# ── caps ──────────────────────────────────────────────────────────────────


@responses.activate
def test_probe_caps_pass_when_enforced():
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"message": "too many"}, status=400,
    )
    r = probe_enc_keys_caps(ETSI014Client(BASE), SAE, max_per_request=20, max_size=1024)
    assert r.status == ProbeStatus.PASS


@responses.activate
def test_probe_caps_warn_when_not_enforced():
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"keys": [_key_payload("k-1", b"x" * 32)]}, status=200,
    )
    r = probe_enc_keys_caps(ETSI014Client(BASE), SAE, max_per_request=20, max_size=1024)
    assert r.status == ProbeStatus.WARN


# ── extensions ────────────────────────────────────────────────────────────


@responses.activate
def test_probe_extensions_accepted_pass():
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"keys": [_key_payload("k-1", b"x" * 32)]}, status=200,
    )
    r = probe_extensions_accepted(ETSI014Client(BASE), SAE)
    assert r.status == ProbeStatus.PASS


@responses.activate
def test_probe_extensions_rejected_warns():
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"message": "extension not understood"}, status=400,
    )
    r = probe_extensions_accepted(ETSI014Client(BASE), SAE)
    assert r.status == ProbeStatus.WARN


# ── dec_keys roundtrip ────────────────────────────────────────────────────


@responses.activate
def test_probe_dec_keys_roundtrip_pass():
    same_bytes = b"K" * 32
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"keys": [_key_payload("k-1", same_bytes)]}, status=200,
    )
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/dec_keys",
        json={"keys": [_key_payload("k-1", same_bytes)]}, status=200,
    )
    r = probe_dec_keys_roundtrip(ETSI014Client(BASE), SAE)
    assert r.status == ProbeStatus.PASS


@responses.activate
def test_probe_dec_keys_roundtrip_byte_mismatch_fails():
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"keys": [_key_payload("k-1", b"A" * 32)]}, status=200,
    )
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/dec_keys",
        json={"keys": [_key_payload("k-1", b"B" * 32)]}, status=200,
    )
    r = probe_dec_keys_roundtrip(ETSI014Client(BASE), SAE)
    assert r.status == ProbeStatus.FAIL


# ── error contracts ──────────────────────────────────────────────────────


@responses.activate
def test_probe_404_pass():
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/dec_keys",
        json={"message": "not found"}, status=404,
    )
    r = probe_error_contract_404(ETSI014Client(BASE), SAE)
    assert r.status == ProbeStatus.PASS


@responses.activate
def test_probe_404_warn_when_kme_returns_200():
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/dec_keys",
        json={"keys": []}, status=200,
    )
    r = probe_error_contract_404(ETSI014Client(BASE), SAE)
    assert r.status == ProbeStatus.WARN


@responses.activate
def test_probe_400_pass():
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"message": "bad size"}, status=400,
    )
    r = probe_error_contract_400(ETSI014Client(BASE), SAE)
    assert r.status == ProbeStatus.PASS


# ── latency ───────────────────────────────────────────────────────────────


@responses.activate
def test_probe_latency_collects_samples():
    for _ in range(5):
        responses.add(
            responses.GET, f"{BASE}/api/v1/keys/{SAE}/status",
            json=_full_status(), status=200,
        )
    r = probe_latency(ETSI014Client(BASE), SAE, samples=5)
    assert r.status == ProbeStatus.PASS
    assert r.details["samples"] == 5


# ── orchestrator ──────────────────────────────────────────────────────────


@responses.activate
def test_run_all_happy_path_is_conformant():
    # Status used many times (status_fields probe, reachability, latency × 5)
    for _ in range(20):
        responses.add(
            responses.GET, f"{BASE}/api/v1/keys/{SAE}/status",
            json=_full_status(), status=200,
        )
    # enc_keys GET — used 4 times (get probe, caps probe, roundtrip, 400 probe)
    # Some succeed, some return 400. responses matches in order added.
    # We need richer mocks; use call counts via responses.replace or just
    # add many of each.
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"keys": [_key_payload("k-1", b"x" * 32)]}, status=200,
    )
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"message": "too many keys"}, status=400,
    )
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"keys": [_key_payload("k-2", b"y" * 32)]}, status=200,
    )
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"message": "bad size"}, status=400,
    )
    # enc_keys POST — used by post probe and extensions probe
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"keys": [_key_payload("kp-1", b"a" * 32)]}, status=200,
    )
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"keys": [_key_payload("kp-2", b"b" * 32)]}, status=200,
    )
    # dec_keys POST — roundtrip success then 404 for bogus
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/dec_keys",
        json={"keys": [_key_payload("k-2", b"y" * 32)]}, status=200,
    )
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/dec_keys",
        json={"message": "not found"}, status=404,
    )

    report = run_all(ETSI014Client(BASE), SAE, latency_samples=3)
    counts = report.counts
    # Expect no FAILs in a fully conformant scenario
    assert counts["fail"] == 0, [r.summary for r in report.results if r.status == ProbeStatus.FAIL]


@responses.activate
def test_run_all_short_circuits_on_unreachable():
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/status",
        json={"message": "down"}, status=503,
    )
    report = run_all(ETSI014Client(BASE), SAE)
    assert any(r.name == "reachability" and r.status == ProbeStatus.FAIL for r in report.results)
    # Once reachability fails, the probe set stops early
    assert len(report.results) == 1


@responses.activate
def test_run_all_no_consume_skips_destructive():
    for _ in range(20):
        responses.add(
            responses.GET, f"{BASE}/api/v1/keys/{SAE}/status",
            json=_full_status(), status=200,
        )
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/dec_keys",
        json={"message": "not found"}, status=404,
    )
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"message": "bad size"}, status=400,
    )
    report = run_all(ETSI014Client(BASE), SAE, consume_keys=False, latency_samples=2)
    skipped = [r for r in report.results if r.status == ProbeStatus.SKIP]
    assert {r.name for r in skipped} == {
        "enc_keys_get", "enc_keys_post", "enc_keys_caps",
        "extensions_accepted", "dec_keys_roundtrip",
    }
