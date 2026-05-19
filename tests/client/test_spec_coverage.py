"""ETSI GS QKD 014 v1.1.1 spec-coverage tests for the sync client.

Covers fields beyond the happy path: multicast key delivery, mandatory and
optional vendor extensions, and container-level extensions.
"""

import base64
import json

import responses

from qkdsec.client import ETSI014Client, KeysContainer

BASE = "https://kme.example.com"


def _key_payload(key_id: str, key_bytes: bytes, **extras) -> dict:
    payload = {"key_ID": key_id, "key": base64.b64encode(key_bytes).decode()}
    payload.update(extras)
    return payload


# ── Status extension ──────────────────────────────────────────────────────


@responses.activate
def test_status_extension_parsed():
    responses.add(
        responses.GET,
        f"{BASE}/api/v1/keys/sae-bob/status",
        json={
            "source_KME_ID": "kme-01",
            "target_KME_ID": "kme-02",
            "master_SAE_ID": "sae-alice",
            "slave_SAE_ID": "sae-bob",
            "key_size": 256,
            "stored_key_count": 42,
            "max_key_count": 50,
            "max_key_per_request": 20,
            "max_key_size": 1024,
            "min_key_size": 64,
            "max_SAE_ID_count": 5,
            "status_extension": {"vendor_health": "GREEN", "rate_kbps": 2.4},
        },
        status=200,
    )
    s = ETSI014Client(BASE).status("sae-bob")
    assert s.status_extension == {"vendor_health": "GREEN", "rate_kbps": 2.4}


# ── Multicast (additional_slave_SAE_IDs) ──────────────────────────────────


@responses.activate
def test_multicast_forces_post_and_sends_additional_saes():
    responses.add(
        responses.POST,
        f"{BASE}/api/v1/keys/sae-bob/enc_keys",
        json={"keys": [_key_payload("k-1", b"x" * 32)]},
        status=200,
    )
    kme = ETSI014Client(BASE)
    kme.get_enc_keys(
        "sae-bob",
        number=1,
        size=256,
        additional_slave_sae_ids=["sae-charlie", "sae-dave"],
    )
    assert len(responses.calls) == 1
    body = json.loads(responses.calls[0].request.body)
    assert body["additional_slave_SAE_IDs"] == ["sae-charlie", "sae-dave"]
    assert body["number"] == 1
    assert body["size"] == 256


# ── Extensions (mandatory + optional) ─────────────────────────────────────


@responses.activate
def test_extension_mandatory_forces_post_and_appears_in_body():
    responses.add(
        responses.POST,
        f"{BASE}/api/v1/keys/sae-bob/enc_keys",
        json={"keys": [_key_payload("k-1", b"y" * 32)]},
        status=200,
    )
    ETSI014Client(BASE).get_enc_keys(
        "sae-bob",
        extension_mandatory=[{"route_type": "primary"}],
    )
    body = json.loads(responses.calls[0].request.body)
    assert body["extension_mandatory"] == [{"route_type": "primary"}]


@responses.activate
def test_extension_optional_appears_in_body():
    responses.add(
        responses.POST,
        f"{BASE}/api/v1/keys/sae-bob/enc_keys",
        json={"keys": [_key_payload("k-1", b"z" * 32)]},
        status=200,
    )
    ETSI014Client(BASE).get_enc_keys(
        "sae-bob",
        extension_optional=[{"preferred_qber": 0.02}],
    )
    body = json.loads(responses.calls[0].request.body)
    assert body["extension_optional"] == [{"preferred_qber": 0.02}]


# ── Container-level extensions on response ────────────────────────────────


@responses.activate
def test_get_enc_keys_container_surfaces_container_extension():
    responses.add(
        responses.GET,
        f"{BASE}/api/v1/keys/sae-bob/enc_keys",
        json={
            "keys": [_key_payload("k-1", b"a" * 32)],
            "key_container_extension": {"batch_id": "B-42"},
        },
        status=200,
    )
    container = ETSI014Client(BASE).get_enc_keys_container(
        "sae-bob", number=1, size=256
    )
    assert isinstance(container, KeysContainer)
    assert container.key_container_extension == {"batch_id": "B-42"}
    assert len(container) == 1
    assert container[0].key_id == "k-1"


@responses.activate
def test_per_key_extensions_parsed():
    responses.add(
        responses.GET,
        f"{BASE}/api/v1/keys/sae-bob/enc_keys",
        json={
            "keys": [
                _key_payload(
                    "k-1",
                    b"a" * 32,
                    key_ID_extension={"epoch": 17},
                    key_extension={"qber_observed": 0.018},
                ),
            ]
        },
        status=200,
    )
    keys = ETSI014Client(BASE).get_enc_keys("sae-bob")
    assert keys[0].key_id_extension == {"epoch": 17}
    assert keys[0].key_extension == {"qber_observed": 0.018}


# ── dec_keys with extensions ──────────────────────────────────────────────


@responses.activate
def test_dec_keys_carries_key_id_extension():
    responses.add(
        responses.POST,
        f"{BASE}/api/v1/keys/sae-bob/dec_keys",
        json={"keys": [_key_payload("k-1", b"b" * 32)]},
        status=200,
    )
    ETSI014Client(BASE).get_dec_keys(
        "sae-bob",
        key_ids=["k-1"],
        key_id_extensions={"k-1": {"hint": "use_in_session_2"}},
    )
    body = json.loads(responses.calls[0].request.body)
    assert body["key_IDs"] == [
        {"key_ID": "k-1", "key_ID_extension": {"hint": "use_in_session_2"}}
    ]


@responses.activate
def test_dec_keys_carries_key_ids_extension():
    responses.add(
        responses.POST,
        f"{BASE}/api/v1/keys/sae-bob/dec_keys",
        json={"keys": [_key_payload("k-1", b"c" * 32)]},
        status=200,
    )
    ETSI014Client(BASE).get_dec_keys(
        "sae-bob",
        key_ids=["k-1"],
        key_ids_extension={"audit_id": "audit-001"},
    )
    body = json.loads(responses.calls[0].request.body)
    assert body["key_IDs_extension"] == {"audit_id": "audit-001"}


# ── Backwards compatibility ───────────────────────────────────────────────


@responses.activate
def test_get_enc_keys_still_returns_list_unchanged():
    responses.add(
        responses.GET,
        f"{BASE}/api/v1/keys/sae-bob/enc_keys",
        json={"keys": [_key_payload("k-1", b"d" * 32)]},
        status=200,
    )
    keys = ETSI014Client(BASE).get_enc_keys("sae-bob", number=1, size=256)
    assert isinstance(keys, list)
    assert keys[0].key_id == "k-1"
    # Extensions default to None when KME doesn't return them
    assert keys[0].key_id_extension is None
    assert keys[0].key_extension is None
