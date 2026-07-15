"""Tests for the mock ETSI GS QKD 014 KME server.

Skipped automatically when Flask is not installed (the ``mock`` extra).
"""

import threading

import pytest

pytest.importorskip("flask")

from qkdsec.mock import KeyPool, create_app
from qkdsec.mock._pool import (
    DEFAULT_KEY_SIZE,
    MAX_KEYS_PER_REQUEST,
    POOL_TARGET,
)


@pytest.fixture(scope="module")
def pool():
    return KeyPool(backend="classical", error_rate=0.01)


@pytest.fixture(scope="module")
def client(pool):
    return create_app(pool=pool).test_client()


# ── §5.2 Status ────────────────────────────────────────────────────────────


def test_status_reports_pool_state(client):
    resp = client.get("/api/v1/keys/sae-bob/status")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["slave_SAE_ID"] == "sae-bob"
    assert body["key_size"] == DEFAULT_KEY_SIZE
    assert body["max_key_per_request"] == MAX_KEYS_PER_REQUEST
    assert 0 <= body["stored_key_count"] <= POOL_TARGET


# ── §5.3 enc_keys ──────────────────────────────────────────────────────────


def test_enc_keys_get_returns_requested_keys(client):
    resp = client.get("/api/v1/keys/sae-bob/enc_keys?number=3&size=256")
    assert resp.status_code == 200
    keys = resp.get_json()["keys"]
    assert len(keys) == 3
    assert all(k["key_ID"] and k["key"] for k in keys)


def test_enc_keys_post_returns_requested_keys(client):
    resp = client.post(
        "/api/v1/keys/sae-bob/enc_keys", json={"number": 2, "size": 128}
    )
    assert resp.status_code == 200
    assert len(resp.get_json()["keys"]) == 2


@pytest.mark.parametrize("query", [
    "number=0",
    f"number={MAX_KEYS_PER_REQUEST + 1}",
    "number=abc",
    "size=4",       # below minimum
    "size=2048",    # above maximum
    "size=100",     # not a multiple of 8
])
def test_enc_keys_get_rejects_bad_params(client, query):
    resp = client.get(f"/api/v1/keys/sae-bob/enc_keys?{query}")
    assert resp.status_code == 400


@pytest.mark.parametrize("body", [
    {"number": 0},
    {"number": MAX_KEYS_PER_REQUEST + 1},
    {"number": "abc"},
    {"number": None},
    {"size": 4},
    {"size": 2048},
    {"size": 100},
])
def test_enc_keys_post_rejects_bad_body(client, body):
    resp = client.post("/api/v1/keys/sae-bob/enc_keys", json=body)
    assert resp.status_code == 400


# ── §5.4 dec_keys ──────────────────────────────────────────────────────────


def _issue(client, number=1, size=256):
    resp = client.get(
        f"/api/v1/keys/sae-bob/enc_keys?number={number}&size={size}"
    )
    return resp.get_json()["keys"]


def test_dec_keys_round_trip_and_one_time_use(client):
    issued = _issue(client, number=2)
    ids = [{"key_ID": k["key_ID"]} for k in issued]

    resp = client.post("/api/v1/keys/sae-bob/dec_keys", json={"key_IDs": ids})
    assert resp.status_code == 200
    retrieved = resp.get_json()["keys"]
    assert {k["key_ID"]: k["key"] for k in retrieved} == {
        k["key_ID"]: k["key"] for k in issued
    }

    # One-time use: a second retrieval must fail.
    resp = client.post("/api/v1/keys/sae-bob/dec_keys", json={"key_IDs": ids})
    assert resp.status_code == 404


def test_dec_keys_partial_miss_consumes_nothing(client):
    issued = _issue(client, number=1)
    good_id = issued[0]["key_ID"]
    mixed = [{"key_ID": good_id}, {"key_ID": "no-such-key"}]

    resp = client.post("/api/v1/keys/sae-bob/dec_keys", json={"key_IDs": mixed})
    assert resp.status_code == 404
    assert "no-such-key" in resp.get_json()["message"]

    # The known key must still be retrievable afterwards.
    resp = client.post(
        "/api/v1/keys/sae-bob/dec_keys", json={"key_IDs": [{"key_ID": good_id}]}
    )
    assert resp.status_code == 200


@pytest.mark.parametrize("body", [
    None,
    {},
    {"key_IDs": []},
    {"key_IDs": ["not-an-object"]},
    {"key_IDs": [{"wrong_field": "x"}]},
    {"key_IDs": [{"key_ID": f"id-{i}"} for i in range(MAX_KEYS_PER_REQUEST + 1)]},
])
def test_dec_keys_rejects_bad_body(client, body):
    resp = client.post("/api/v1/keys/sae-bob/dec_keys", json=body)
    assert resp.status_code == 400


# ── Key pool ───────────────────────────────────────────────────────────────


def test_public_reexports_match_internal_modules():
    from qkdsec.mock import _pool, _server

    assert KeyPool is _pool.KeyPool
    assert create_app is _server.create_app


def test_pool_survives_concurrent_drain():
    pool = KeyPool(backend="classical", error_rate=0.01)
    errors = []

    def hammer():
        try:
            for _ in range(5):
                assert len(pool.get_keys(2)) == 2
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=hammer) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    # Internal bookkeeping must stay consistent after refills.
    assert len(pool._available_order) == len(pool._available)
    assert len(set(pool._available_order)) == len(pool._available_order)


def test_dec_keys_duplicate_ids_returned_once():
    pool = KeyPool(backend="classical", error_rate=0.01)
    issued = pool.get_keys(1)
    kid = issued[0].key_id
    found, missing = pool.get_by_ids([kid, kid])
    assert len(found) == 1
    assert not missing
