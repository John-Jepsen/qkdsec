"""Async client tests using respx to mock httpx."""

import base64
import json

import httpx
import pytest
import respx

from qkdsec.client import KeysContainer, KMEHTTPError, KMENotFoundError, StatusResponse
from qkdsec.client.aio import AsyncETSI014Client

BASE = "https://kme.example.com"


def _key_payload(key_id: str, key_bytes: bytes, **extras) -> dict:
    payload = {"key_ID": key_id, "key": base64.b64encode(key_bytes).decode()}
    payload.update(extras)
    return payload


# ── Status ────────────────────────────────────────────────────────────────


@respx.mock
async def test_async_status():
    respx.get(f"{BASE}/api/v1/keys/sae-bob/status").mock(
        return_value=httpx.Response(
            200,
            json={
                "source_KME_ID": "kme-01",
                "target_KME_ID": "kme-02",
                "master_SAE_ID": "sae-alice",
                "slave_SAE_ID": "sae-bob",
                "key_size": 256,
                "stored_key_count": 7,
                "max_key_count": 50,
                "max_key_per_request": 20,
                "max_key_size": 1024,
                "min_key_size": 64,
                "max_SAE_ID_count": 0,
            },
        )
    )
    async with AsyncETSI014Client(BASE) as kme:
        s = await kme.status("sae-bob")
    assert isinstance(s, StatusResponse)
    assert s.stored_key_count == 7


# ── enc_keys ──────────────────────────────────────────────────────────────


@respx.mock
async def test_async_get_enc_keys_get():
    respx.get(f"{BASE}/api/v1/keys/sae-bob/enc_keys").mock(
        return_value=httpx.Response(
            200, json={"keys": [_key_payload("k-1", b"x" * 32)]}
        )
    )
    async with AsyncETSI014Client(BASE) as kme:
        keys = await kme.get_enc_keys("sae-bob", number=1, size=256)
    assert keys[0].key_id == "k-1"
    assert keys[0].key == b"x" * 32


@respx.mock
async def test_async_get_enc_keys_post():
    route = respx.post(f"{BASE}/api/v1/keys/sae-bob/enc_keys").mock(
        return_value=httpx.Response(
            200, json={"keys": [_key_payload("k-1", b"y" * 32)]}
        )
    )
    async with AsyncETSI014Client(BASE) as kme:
        await kme.get_enc_keys("sae-bob", number=2, size=256, method="POST")
    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body["number"] == 2


# ── Spec coverage on async ────────────────────────────────────────────────


@respx.mock
async def test_async_multicast_forces_post():
    route = respx.post(f"{BASE}/api/v1/keys/sae-bob/enc_keys").mock(
        return_value=httpx.Response(
            200, json={"keys": [_key_payload("k-1", b"z" * 32)]}
        )
    )
    async with AsyncETSI014Client(BASE) as kme:
        await kme.get_enc_keys(
            "sae-bob",
            additional_slave_sae_ids=["sae-charlie"],
        )
    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body["additional_slave_SAE_IDs"] == ["sae-charlie"]


@respx.mock
async def test_async_get_enc_keys_container():
    respx.get(f"{BASE}/api/v1/keys/sae-bob/enc_keys").mock(
        return_value=httpx.Response(
            200,
            json={
                "keys": [
                    _key_payload(
                        "k-1",
                        b"a" * 32,
                        key_ID_extension={"epoch": 5},
                    )
                ],
                "key_container_extension": {"batch_id": "B-99"},
            },
        )
    )
    async with AsyncETSI014Client(BASE) as kme:
        c = await kme.get_enc_keys_container("sae-bob", number=1, size=256)
    assert isinstance(c, KeysContainer)
    assert c.key_container_extension == {"batch_id": "B-99"}
    assert c[0].key_id_extension == {"epoch": 5}


# ── dec_keys ──────────────────────────────────────────────────────────────


@respx.mock
async def test_async_get_dec_keys():
    respx.post(f"{BASE}/api/v1/keys/sae-bob/dec_keys").mock(
        return_value=httpx.Response(
            200, json={"keys": [_key_payload("aaa", b"k" * 32)]}
        )
    )
    async with AsyncETSI014Client(BASE) as kme:
        keys = await kme.get_dec_keys("sae-bob", key_ids=["aaa"])
    assert keys[0].key_id == "aaa"


async def test_async_get_dec_keys_empty_raises():
    async with AsyncETSI014Client(BASE) as kme:
        with pytest.raises(ValueError):
            await kme.get_dec_keys("sae-bob", key_ids=[])


# ── Error handling ────────────────────────────────────────────────────────


@respx.mock
async def test_async_404_raises_not_found():
    respx.post(f"{BASE}/api/v1/keys/sae-bob/dec_keys").mock(
        return_value=httpx.Response(404, json={"message": "key_ID not found"})
    )
    async with AsyncETSI014Client(BASE) as kme:
        with pytest.raises(KMENotFoundError):
            await kme.get_dec_keys("sae-bob", key_ids=["missing"])


@respx.mock
async def test_async_400_raises_http_error():
    respx.get(f"{BASE}/api/v1/keys/sae-bob/enc_keys").mock(
        return_value=httpx.Response(400, json={"message": "bad size"})
    )
    async with AsyncETSI014Client(BASE) as kme:
        with pytest.raises(KMEHTTPError) as exc_info:
            await kme.get_enc_keys("sae-bob", size=257)
    assert exc_info.value.status_code == 400


# ── Lifecycle ─────────────────────────────────────────────────────────────


async def test_async_context_manager_closes():
    kme = AsyncETSI014Client(BASE)
    assert kme._client is not None
    await kme.aclose()


@respx.mock
async def test_async_base_url_trailing_slash_stripped():
    respx.get("https://kme.example.com/api/v1/keys/sae-bob/status").mock(
        return_value=httpx.Response(
            200,
            json={
                "source_KME_ID": "k",
                "target_KME_ID": "k",
                "master_SAE_ID": "m",
                "slave_SAE_ID": "sae-bob",
                "key_size": 256,
                "stored_key_count": 0,
                "max_key_count": 50,
                "max_key_per_request": 20,
                "max_key_size": 1024,
                "min_key_size": 64,
                "max_SAE_ID_count": 0,
            },
        )
    )
    async with AsyncETSI014Client("https://kme.example.com/") as kme:
        s = await kme.status("sae-bob")
    assert s.slave_sae_id == "sae-bob"
