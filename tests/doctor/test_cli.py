"""CLI smoke tests using typer.testing.CliRunner with mocked HTTP."""

import base64
import json

import responses
from typer.testing import CliRunner

from qkdsec._cli import app

BASE = "https://kme.example.com"
SAE = "sae-bob"


def _full_status(**overrides):
    s = {
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
    s.update(overrides)
    return s


def _key_payload(key_id, key_bytes):
    return {"key_ID": key_id, "key": base64.b64encode(key_bytes).decode()}


runner = CliRunner()


# ── version / help ────────────────────────────────────────────────────────


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    from qkdsec import __version__
    assert __version__ in result.stdout


def test_help_lists_subcommands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("doctor", "status", "keys", "version"):
        assert cmd in result.stdout


# ── status ────────────────────────────────────────────────────────────────


@responses.activate
def test_status_command():
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/status",
        json=_full_status(), status=200,
    )
    result = runner.invoke(app, ["status", BASE, SAE, "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["stored_key_count"] == 42


@responses.activate
def test_status_command_error_exit_code():
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/status",
        json={"message": "unauthorized"}, status=401,
    )
    result = runner.invoke(app, ["status", BASE, SAE])
    assert result.exit_code == 1


# ── keys ──────────────────────────────────────────────────────────────────


@responses.activate
def test_keys_get_command():
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"keys": [_key_payload("k-1", b"x" * 32)]}, status=200,
    )
    result = runner.invoke(app, ["keys", "get", BASE, SAE, "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["key_id"] == "k-1"
    assert payload[0]["size_bits"] == 256


@responses.activate
def test_keys_retrieve_command():
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/dec_keys",
        json={"keys": [_key_payload("k-1", b"x" * 32)]}, status=200,
    )
    result = runner.invoke(app, ["keys", "retrieve", BASE, SAE, "k-1", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["key_id"] == "k-1"


# ── doctor ────────────────────────────────────────────────────────────────


@responses.activate
def test_doctor_json_output():
    # All probes need mocks. Reuse the orchestrator-test fixtures style.
    for _ in range(20):
        responses.add(
            responses.GET, f"{BASE}/api/v1/keys/{SAE}/status",
            json=_full_status(), status=200,
        )
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"keys": [_key_payload("k-1", b"x" * 32)]}, status=200,
    )
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"message": "too many"}, status=400,
    )
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"keys": [_key_payload("k-2", b"y" * 32)]}, status=200,
    )
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"message": "bad size"}, status=400,
    )
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"keys": [_key_payload("kp-1", b"a" * 32)]}, status=200,
    )
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/enc_keys",
        json={"keys": [_key_payload("kp-2", b"b" * 32)]}, status=200,
    )
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/dec_keys",
        json={"keys": [_key_payload("k-2", b"y" * 32)]}, status=200,
    )
    responses.add(
        responses.POST, f"{BASE}/api/v1/keys/{SAE}/dec_keys",
        json={"message": "not found"}, status=404,
    )

    result = runner.invoke(
        app, ["doctor", BASE, "--slave-sae-id", SAE,
              "--format", "json", "--samples", "2"],
    )
    # exit 0 = passed, 1 = non-conformant. With these mocks expect 0.
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["counts"]["fail"] == 0


@responses.activate
def test_doctor_nonconformant_exits_1():
    responses.add(
        responses.GET, f"{BASE}/api/v1/keys/{SAE}/status",
        json={"message": "down"}, status=503,
    )
    result = runner.invoke(
        app, ["doctor", BASE, "--slave-sae-id", SAE, "--format", "json"],
    )
    assert result.exit_code == 1


def test_doctor_invalid_format():
    result = runner.invoke(app, ["doctor", BASE, "--format", "yaml"])
    assert result.exit_code == 2
