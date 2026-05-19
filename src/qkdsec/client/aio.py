"""Asynchronous ETSI GS QKD 014 client (httpx-based).

Requires the ``async`` extra: ``pip install qkdsec[async]``.

The async client mirrors the sync ``ETSI014Client`` API one-for-one. Parsers
are shared with the sync client to keep response handling consistent.

Example::

    from qkdsec.client.aio import AsyncETSI014Client

    async with AsyncETSI014Client(
        "https://kme.example.com",
        client_cert=("alice.crt", "alice.key"),
    ) as kme:
        status = await kme.status("sae-bob")
        keys = await kme.get_enc_keys("sae-bob", number=1, size=256)
"""

from typing import Any, Optional, Union

try:
    import httpx
except ImportError as e:
    raise ImportError(
        "qkdsec.client.aio requires extra dependencies. "
        "Install with: pip install qkdsec[async]"
    ) from e

from ._types import KeyResponse, KeysContainer, StatusResponse
from .errors import KMEHTTPError, KMENotFoundError
from .etsi014 import ETSI014Client

_API_PREFIX = "/api/v1/keys"


CertType = Union[str, tuple[str, str], None]
VerifyType = Union[bool, str]


class AsyncETSI014Client:
    """Asynchronous client for an ETSI GS QKD 014 KME.

    Parameters mirror :class:`qkdsec.client.ETSI014Client` exactly.

    Use as an async context manager to ensure the underlying httpx client
    is closed::

        async with AsyncETSI014Client(...) as kme:
            await kme.status("sae-bob")
    """

    def __init__(
        self,
        base_url: str,
        *,
        client_cert: CertType = None,
        verify: VerifyType = True,
        timeout: float = 30.0,
        extra_headers: Optional[dict] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.client_cert = client_cert
        self.verify = verify
        self.timeout = timeout
        self.extra_headers = dict(extra_headers or {})

        if client is None:
            self._client = httpx.AsyncClient(
                cert=client_cert,
                verify=verify,
                timeout=timeout,
                headers=self.extra_headers,
            )
            self._owns_client = True
        else:
            self._client = client
            self._owns_client = False

    # ── Status ─────────────────────────────────────────────────────────────

    async def status(self, slave_sae_id: str) -> StatusResponse:
        """Fetch KME status for the given slave SAE (ETSI 014 §5.2)."""
        url = f"{self.base_url}{_API_PREFIX}/{slave_sae_id}/status"
        data = await self._get_json(url)
        return ETSI014Client._parse_status(data)

    # ── enc_keys (master SAE) ──────────────────────────────────────────────

    async def get_enc_keys(
        self,
        slave_sae_id: str,
        *,
        number: int = 1,
        size: int = 256,
        method: str = "GET",
        additional_slave_sae_ids: Optional[list[str]] = None,
        extension_mandatory: Optional[list[dict[str, Any]]] = None,
        extension_optional: Optional[list[dict[str, Any]]] = None,
    ) -> list[KeyResponse]:
        """Fetch encryption keys for the master SAE (ETSI 014 §5.3)."""
        container = await self.get_enc_keys_container(
            slave_sae_id,
            number=number,
            size=size,
            method=method,
            additional_slave_sae_ids=additional_slave_sae_ids,
            extension_mandatory=extension_mandatory,
            extension_optional=extension_optional,
        )
        return container.keys

    async def get_enc_keys_container(
        self,
        slave_sae_id: str,
        *,
        number: int = 1,
        size: int = 256,
        method: str = "GET",
        additional_slave_sae_ids: Optional[list[str]] = None,
        extension_mandatory: Optional[list[dict[str, Any]]] = None,
        extension_optional: Optional[list[dict[str, Any]]] = None,
    ) -> KeysContainer:
        """Fetch encryption keys and return the full ETSI 014 §5.3 container."""
        force_post = bool(
            additional_slave_sae_ids
            or extension_mandatory
            or extension_optional
        )
        actual_method = "POST" if force_post else method.upper()

        url = f"{self.base_url}{_API_PREFIX}/{slave_sae_id}/enc_keys"
        if actual_method == "GET":
            data = await self._get_json(
                url, params={"number": number, "size": size}
            )
        elif actual_method == "POST":
            body: dict[str, Any] = {"number": number, "size": size}
            if additional_slave_sae_ids:
                body["additional_slave_SAE_IDs"] = list(additional_slave_sae_ids)
            if extension_mandatory:
                body["extension_mandatory"] = list(extension_mandatory)
            if extension_optional:
                body["extension_optional"] = list(extension_optional)
            data = await self._post_json(url, json=body)
        else:
            raise ValueError(
                f"method must be 'GET' or 'POST', got {method!r}"
            )
        return ETSI014Client._parse_keys_container(data)

    # ── dec_keys (slave SAE) ───────────────────────────────────────────────

    async def get_dec_keys(
        self,
        slave_sae_id: str,
        *,
        key_ids: list[str],
        key_id_extensions: Optional[dict[str, dict[str, Any]]] = None,
        key_ids_extension: Optional[dict[str, Any]] = None,
    ) -> list[KeyResponse]:
        """Fetch specific keys by key_ID for the slave SAE (ETSI 014 §5.4)."""
        container = await self.get_dec_keys_container(
            slave_sae_id,
            key_ids=key_ids,
            key_id_extensions=key_id_extensions,
            key_ids_extension=key_ids_extension,
        )
        return container.keys

    async def get_dec_keys_container(
        self,
        slave_sae_id: str,
        *,
        key_ids: list[str],
        key_id_extensions: Optional[dict[str, dict[str, Any]]] = None,
        key_ids_extension: Optional[dict[str, Any]] = None,
    ) -> KeysContainer:
        """Fetch keys by key_ID and return the full ETSI 014 §5.4 container."""
        if not key_ids:
            raise ValueError("key_ids must be a non-empty list")
        url = f"{self.base_url}{_API_PREFIX}/{slave_sae_id}/dec_keys"
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
        data = await self._post_json(url, json=body)
        return ETSI014Client._parse_keys_container(data)

    # ── Lifecycle ──────────────────────────────────────────────────────────

    async def aclose(self) -> None:
        """Close the underlying HTTP client (if owned by this instance)."""
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "AsyncETSI014Client":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.aclose()

    # ── HTTP helpers ───────────────────────────────────────────────────────

    async def _get_json(self, url: str, params: Optional[dict] = None) -> dict:
        response = await self._client.get(url, params=params)
        return self._handle_response(response)

    async def _post_json(self, url: str, json: dict) -> dict:
        response = await self._client.post(
            url,
            json=json,
            headers={"Content-Type": "application/json"},
        )
        return self._handle_response(response)

    @staticmethod
    def _handle_response(response: "httpx.Response") -> dict:
        if response.is_success:
            return response.json()

        try:
            message = response.json().get("message", response.text)
        except ValueError:
            message = response.text

        if response.status_code == 404:
            raise KMENotFoundError(message)
        raise KMEHTTPError(response.status_code, message)
