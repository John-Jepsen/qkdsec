"""Shared request-building and response-parsing logic for the ETSI 014 clients.

The sync (``requests``) and async (``httpx``) clients differ only in
transport. Everything about *what* is sent and *how* responses are
interpreted lives here so the two clients cannot drift apart.
"""

import base64
from typing import Any, NoReturn, Optional, Union

from ._types import KeyResponse, KeysContainer, StatusResponse
from .errors import KMEHTTPError, KMENotFoundError

API_PREFIX = "/api/v1/keys"

CertType = Union[str, tuple[str, str], None]
VerifyType = Union[bool, str]


# ── URL builders ──────────────────────────────────────────────────────────


def status_url(base_url: str, slave_sae_id: str) -> str:
    return f"{base_url}{API_PREFIX}/{slave_sae_id}/status"


def enc_keys_url(base_url: str, slave_sae_id: str) -> str:
    return f"{base_url}{API_PREFIX}/{slave_sae_id}/enc_keys"


def dec_keys_url(base_url: str, slave_sae_id: str) -> str:
    return f"{base_url}{API_PREFIX}/{slave_sae_id}/dec_keys"


# ── Request builders ──────────────────────────────────────────────────────


def build_enc_keys_request(
    *,
    number: int,
    size: int,
    method: str,
    additional_slave_sae_ids: Optional[list[str]] = None,
    extension_mandatory: Optional[list[dict[str, Any]]] = None,
    extension_optional: Optional[list[dict[str, Any]]] = None,
) -> tuple[str, Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    """Return ``(method, query_params, json_body)`` for an enc_keys request.

    Multicast and extension fields force POST since GET cannot carry them
    (ETSI 014 §5.3.2). Exactly one of ``query_params`` / ``json_body`` is
    non-None depending on the resolved method.
    """
    force_post = bool(
        additional_slave_sae_ids or extension_mandatory or extension_optional
    )
    actual_method = "POST" if force_post else method.upper()

    if actual_method == "GET":
        return "GET", {"number": number, "size": size}, None
    if actual_method == "POST":
        body: dict[str, Any] = {"number": number, "size": size}
        if additional_slave_sae_ids:
            body["additional_slave_SAE_IDs"] = list(additional_slave_sae_ids)
        if extension_mandatory:
            body["extension_mandatory"] = list(extension_mandatory)
        if extension_optional:
            body["extension_optional"] = list(extension_optional)
        return "POST", None, body
    raise ValueError(f"method must be 'GET' or 'POST', got {method!r}")


def build_dec_keys_body(
    key_ids: list[str],
    key_id_extensions: Optional[dict[str, dict[str, Any]]] = None,
    key_ids_extension: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build the JSON body for a dec_keys request (ETSI 014 §5.4.2)."""
    if not key_ids:
        raise ValueError("key_ids must be a non-empty list")
    ext_map = key_id_extensions or {}
    items: list[dict[str, Any]] = []
    for kid in key_ids:
        entry: dict[str, Any] = {"key_ID": kid}
        if kid in ext_map:
            entry["key_ID_extension"] = ext_map[kid]
        items.append(entry)
    body: dict[str, Any] = {"key_IDs": items}
    if key_ids_extension:
        body["key_IDs_extension"] = key_ids_extension
    return body


# ── Error handling ────────────────────────────────────────────────────────


def raise_kme_error(status_code: int, parsed_body: Any, text: str) -> NoReturn:
    """Raise the appropriate KME exception for a non-2xx response.

    ``parsed_body`` is the JSON-decoded body if decoding succeeded (may be
    any JSON type — some KMEs return arrays or bare strings on error), else
    None. ``text`` is the raw response text used as the fallback message.
    """
    if isinstance(parsed_body, dict):
        message = parsed_body.get("message", text)
    else:
        message = text
    if status_code == 404:
        raise KMENotFoundError(message)
    raise KMEHTTPError(status_code, message)


# ── Response parsers ──────────────────────────────────────────────────────


def parse_status(data: dict) -> StatusResponse:
    return StatusResponse(
        source_kme_id=data["source_KME_ID"],
        target_kme_id=data["target_KME_ID"],
        master_sae_id=data["master_SAE_ID"],
        slave_sae_id=data["slave_SAE_ID"],
        key_size=data["key_size"],
        stored_key_count=data["stored_key_count"],
        max_key_count=data["max_key_count"],
        max_key_per_request=data["max_key_per_request"],
        max_key_size=data["max_key_size"],
        min_key_size=data["min_key_size"],
        max_sae_id_count=data["max_SAE_ID_count"],
        status_extension=data.get("status_extension"),
    )


def parse_keys_container(data: dict) -> KeysContainer:
    keys = [
        KeyResponse(
            key_id=item["key_ID"],
            key=base64.b64decode(item["key"]),
            key_id_extension=item.get("key_ID_extension"),
            key_extension=item.get("key_extension"),
        )
        for item in data.get("keys", [])
    ]
    return KeysContainer(
        keys=keys,
        key_container_extension=data.get("key_container_extension"),
    )
