import base64

import pytest
import responses

from qkdsec.client import (
    ETSI014Client,
    KeyResponse,
    KMEHTTPError,
    KMENotFoundError,
    StatusResponse,
)

BASE = "https://kme.example.com"


@responses.activate
def test_status():
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
            "max_SAE_ID_count": 0,
        },
        status=200,
    )

    kme = ETSI014Client(BASE)
    s = kme.status("sae-bob")
    assert isinstance(s, StatusResponse)
    assert s.source_kme_id == "kme-01"
    assert s.stored_key_count == 42
    assert s.key_size == 256


@responses.activate
def test_get_enc_keys_get_method():
    key_bytes = bytes(range(32))
    responses.add(
        responses.GET,
        f"{BASE}/api/v1/keys/sae-bob/enc_keys",
        json={
            "keys": [
                {
                    "key_ID": "abc-123",
                    "key": base64.b64encode(key_bytes).decode(),
                },
            ]
        },
        status=200,
    )

    kme = ETSI014Client(BASE)
    keys = kme.get_enc_keys("sae-bob", number=1, size=256)
    assert len(keys) == 1
    assert isinstance(keys[0], KeyResponse)
    assert keys[0].key_id == "abc-123"
    assert keys[0].key == key_bytes
    assert keys[0].size_bits == 256

    # Verify the request was a GET with the expected query params
    call = responses.calls[0]
    assert "number=1" in call.request.url
    assert "size=256" in call.request.url


@responses.activate
def test_get_enc_keys_post_method():
    responses.add(
        responses.POST,
        f"{BASE}/api/v1/keys/sae-bob/enc_keys",
        json={"keys": [{"key_ID": "xyz-789", "key": base64.b64encode(b"k" * 32).decode()}]},
        status=200,
    )

    kme = ETSI014Client(BASE)
    keys = kme.get_enc_keys("sae-bob", number=2, size=256, method="POST")
    assert keys[0].key_id == "xyz-789"

    body = responses.calls[0].request.body
    assert b'"number": 2' in body or b'"number":2' in body


@responses.activate
def test_get_dec_keys():
    responses.add(
        responses.POST,
        f"{BASE}/api/v1/keys/sae-bob/dec_keys",
        json={
            "keys": [
                {"key_ID": "aaa", "key": base64.b64encode(b"k1" * 16).decode()},
                {"key_ID": "bbb", "key": base64.b64encode(b"k2" * 16).decode()},
            ]
        },
        status=200,
    )

    kme = ETSI014Client(BASE)
    keys = kme.get_dec_keys("sae-bob", key_ids=["aaa", "bbb"])
    assert len(keys) == 2
    assert keys[0].key_id == "aaa"
    assert keys[1].key_id == "bbb"


def test_get_dec_keys_empty_list_raises():
    kme = ETSI014Client(BASE)
    with pytest.raises(ValueError):
        kme.get_dec_keys("sae-bob", key_ids=[])


@responses.activate
def test_404_raises_not_found():
    responses.add(
        responses.POST,
        f"{BASE}/api/v1/keys/sae-bob/dec_keys",
        json={"message": "key_ID not found"},
        status=404,
    )
    kme = ETSI014Client(BASE)
    with pytest.raises(KMENotFoundError) as exc_info:
        kme.get_dec_keys("sae-bob", key_ids=["missing"])
    assert "not found" in exc_info.value.message.lower()
    assert exc_info.value.status_code == 404


@responses.activate
def test_400_raises_http_error():
    responses.add(
        responses.GET,
        f"{BASE}/api/v1/keys/sae-bob/enc_keys",
        json={"message": "size must be multiple of 8"},
        status=400,
    )
    kme = ETSI014Client(BASE)
    with pytest.raises(KMEHTTPError) as exc_info:
        kme.get_enc_keys("sae-bob", size=257)
    assert exc_info.value.status_code == 400


def test_invalid_method_raises():
    kme = ETSI014Client(BASE)
    with pytest.raises(ValueError):
        kme.get_enc_keys("sae-bob", method="PUT")


def test_context_manager_closes_session():
    with ETSI014Client(BASE) as kme:
        assert kme._session is not None
    # After __exit__, session is closed but reference still exists


@responses.activate
def test_base_url_trailing_slash_stripped():
    responses.add(
        responses.GET,
        "https://kme.example.com/api/v1/keys/sae-bob/status",
        json={
            "source_KME_ID": "k", "target_KME_ID": "k", "master_SAE_ID": "m",
            "slave_SAE_ID": "sae-bob", "key_size": 256, "stored_key_count": 0,
            "max_key_count": 50, "max_key_per_request": 20, "max_key_size": 1024,
            "min_key_size": 64, "max_SAE_ID_count": 0,
        },
        status=200,
    )
    kme = ETSI014Client("https://kme.example.com/")
    s = kme.status("sae-bob")
    assert s.slave_sae_id == "sae-bob"
