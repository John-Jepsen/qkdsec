"""Asynchronous ETSI GS QKD 014 client (httpx-based).

Requires the ``async`` extra: ``pip install qkdsec[async]``.

The async client mirrors the sync ``ETSI014Client`` API one-for-one.
Request-building and response-parsing are shared with the sync client
(see ``qkdsec.client._common``) so the two cannot drift apart.

Example::

    from qkdsec.client.aio import AsyncETSI014Client

    async with AsyncETSI014Client(
        "https://kme.example.com",
        client_cert=("alice.crt", "alice.key"),
    ) as kme:
        status = await kme.status("sae-bob")
        keys = await kme.get_enc_keys("sae-bob", number=1, size=256)
"""

from typing import Any, Optional

try:
    import httpx
except ImportError as e:
    raise ImportError(
        "qkdsec.client.aio requires extra dependencies. "
        "Install with: pip install qkdsec[async]"
    ) from e

from . import _common
from ._common import CertType, VerifyType
from ._types import KeyResponse, KeysContainer, StatusResponse


class AsyncETSI014Client:
    """Asynchronous client for an ETSI GS QKD 014 KME.

    Parameters mirror :class:`qkdsec.client.ETSI014Client`, plus:

    client : httpx.AsyncClient, optional
        Reuse an existing httpx client. A client you pass in is *not*
        closed by :meth:`aclose` — you own it. Note that ``client_cert``
        and ``verify`` cannot be applied per-request by httpx, so they are
        ignored when you supply your own client (configure TLS on the
        client you pass in instead); ``ValueError`` is raised if you try
        to combine them. ``extra_headers`` and ``timeout`` are applied on
        every request and work with injected clients.

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
            )
            self._owns_client = True
        else:
            if client_cert is not None or verify is not True:
                raise ValueError(
                    "client_cert/verify cannot be applied to an injected "
                    "httpx client; configure TLS on the client you pass in."
                )
            self._client = client
            self._owns_client = False

    # ── Status ─────────────────────────────────────────────────────────────

    async def status(self, slave_sae_id: str) -> StatusResponse:
        """Fetch KME status for the given slave SAE (ETSI 014 §5.2)."""
        return _common.parse_status(await self.status_raw(slave_sae_id))

    async def status_raw(self, slave_sae_id: str) -> dict:
        """Fetch the §5.2 status response as the raw JSON dict."""
        return await self._get_json(
            _common.status_url(self.base_url, slave_sae_id)
        )

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
        actual_method, params, body = _common.build_enc_keys_request(
            number=number,
            size=size,
            method=method,
            additional_slave_sae_ids=additional_slave_sae_ids,
            extension_mandatory=extension_mandatory,
            extension_optional=extension_optional,
        )
        url = _common.enc_keys_url(self.base_url, slave_sae_id)
        if actual_method == "GET":
            data = await self._get_json(url, params=params)
        else:
            data = await self._post_json(url, json=body)
        return _common.parse_keys_container(data)

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
        body = _common.build_dec_keys_body(
            key_ids, key_id_extensions, key_ids_extension
        )
        url = _common.dec_keys_url(self.base_url, slave_sae_id)
        data = await self._post_json(url, json=body)
        return _common.parse_keys_container(data)

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
        response = await self._client.get(
            url,
            params=params,
            headers=self.extra_headers,
            timeout=self.timeout,
        )
        return self._handle_response(response)

    async def _post_json(self, url: str, json: dict) -> dict:
        response = await self._client.post(
            url,
            json=json,
            headers={**self.extra_headers, "Content-Type": "application/json"},
            timeout=self.timeout,
        )
        return self._handle_response(response)

    @staticmethod
    def _handle_response(response: "httpx.Response") -> dict:
        if response.is_success:
            return response.json()
        try:
            parsed = response.json()
        except ValueError:
            parsed = None
        _common.raise_kme_error(response.status_code, parsed, response.text)
