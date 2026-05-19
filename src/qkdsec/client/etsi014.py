"""Synchronous ETSI GS QKD 014 client.

Full coverage of ETSI GS QKD 014 v1.1.1, including:
    - All three endpoints (status, enc_keys, dec_keys)
    - GET and POST request methods for enc_keys
    - Multicast key delivery (``additional_slave_SAE_IDs``)
    - Mandatory and optional vendor extensions on request and response
    - Container-level extensions (``key_container_extension``,
      ``status_extension``, etc.)

Typical flow (point-to-point, master = Alice, slave = Bob):

    1. Alice's app calls ``get_enc_keys`` against Alice's KME — receives one
       or more ``KeyResponse`` with key bytes + key_id.
    2. Alice sends the key_id (over a classical channel) to Bob.
    3. Bob's app calls ``get_dec_keys`` against Bob's KME with the same
       key_id — receives the matching key bytes.

For multicast (one-to-many) delivery, pass ``additional_slave_SAE_IDs=[...]``
to ``get_enc_keys``; the same key is then retrievable by each listed SAE.
"""

import base64
from typing import Any, Optional, Union

import requests

from ._types import KeyResponse, KeysContainer, StatusResponse
from .errors import KMEHTTPError, KMENotFoundError

_API_PREFIX = "/api/v1/keys"


CertType = Union[str, tuple[str, str], None]
VerifyType = Union[bool, str]


class ETSI014Client:
    """Synchronous client for an ETSI GS QKD 014 Key Management Entity (KME).

    Parameters
    ----------
    base_url : str
        Base URL of the KME (e.g., ``"https://kme.example.com:8443"``). The
        ``/api/v1/keys`` path is appended automatically.
    client_cert : str, tuple, or None
        Client certificate for mTLS. Pass a path to a combined cert+key PEM
        file, or a ``(cert_path, key_path)`` tuple. Most production KMEs
        require mTLS.
    verify : bool or str
        TLS verification mode. ``True`` (default) uses the system CA bundle.
        Pass a path to a CA certificate file to pin a custom CA. ``False``
        disables verification (do not use in production).
    timeout : float
        Per-request timeout in seconds. Default 30.
    extra_headers : dict, optional
        Additional headers to send on every request.
    session : requests.Session, optional
        Reuse an existing session (useful for connection pooling or testing).
    """

    def __init__(
        self,
        base_url: str,
        *,
        client_cert: CertType = None,
        verify: VerifyType = True,
        timeout: float = 30.0,
        extra_headers: Optional[dict] = None,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.client_cert = client_cert
        self.verify = verify
        self.timeout = timeout
        self.extra_headers = dict(extra_headers or {})
        self._session = session or requests.Session()

    # ── Status ─────────────────────────────────────────────────────────────

    def status(self, slave_sae_id: str) -> StatusResponse:
        """Fetch KME status for the given slave SAE (ETSI 014 §5.2)."""
        url = f"{self.base_url}{_API_PREFIX}/{slave_sae_id}/status"
        data = self._get_json(url)
        return self._parse_status(data)

    # ── enc_keys (master SAE) ──────────────────────────────────────────────

    def get_enc_keys(
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
        """Fetch encryption keys for the master SAE (ETSI 014 §5.3).

        Returns just the list of keys for backwards compatibility. Use
        :meth:`get_enc_keys_container` to access ``key_container_extension``.
        """
        container = self.get_enc_keys_container(
            slave_sae_id,
            number=number,
            size=size,
            method=method,
            additional_slave_sae_ids=additional_slave_sae_ids,
            extension_mandatory=extension_mandatory,
            extension_optional=extension_optional,
        )
        return container.keys

    def get_enc_keys_container(
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
        """Fetch encryption keys and return the full ETSI 014 §5.3 container.

        Parameters
        ----------
        slave_sae_id : str
            The SAE ID of the intended decrypting peer.
        number : int
            Number of keys to request. KMEs typically cap this at 20.
        size : int
            Key size in bits. Must be a multiple of 8.
        method : str
            ``"GET"`` (query params) or ``"POST"`` (JSON body). Multicast and
            extensions force POST automatically since GET cannot carry them.
        additional_slave_sae_ids : list[str], optional
            Additional slave SAEs that should be able to retrieve the same
            key (ETSI 014 multicast). Forces POST.
        extension_mandatory : list[dict], optional
            Vendor-specific parameters the KME MUST honor (ETSI 014 §5.3.2).
            Forces POST. The KME rejects the request if it cannot satisfy.
        extension_optional : list[dict], optional
            Vendor-specific parameters the KME MAY honor (ETSI 014 §5.3.2).
            Forces POST. Best-effort.
        """
        force_post = bool(
            additional_slave_sae_ids
            or extension_mandatory
            or extension_optional
        )
        actual_method = "POST" if force_post else method.upper()

        url = f"{self.base_url}{_API_PREFIX}/{slave_sae_id}/enc_keys"
        if actual_method == "GET":
            data = self._get_json(
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
            data = self._post_json(url, json=body)
        else:
            raise ValueError(
                f"method must be 'GET' or 'POST', got {method!r}"
            )
        return self._parse_keys_container(data)

    # ── dec_keys (slave SAE) ───────────────────────────────────────────────

    def get_dec_keys(
        self,
        slave_sae_id: str,
        *,
        key_ids: list[str],
        key_id_extensions: Optional[dict[str, dict[str, Any]]] = None,
        key_ids_extension: Optional[dict[str, Any]] = None,
    ) -> list[KeyResponse]:
        """Fetch specific keys by key_ID for the slave SAE (ETSI 014 §5.4).

        Returns just the list of keys. Use :meth:`get_dec_keys_container`
        to access ``key_container_extension``.
        """
        return self.get_dec_keys_container(
            slave_sae_id,
            key_ids=key_ids,
            key_id_extensions=key_id_extensions,
            key_ids_extension=key_ids_extension,
        ).keys

    def get_dec_keys_container(
        self,
        slave_sae_id: str,
        *,
        key_ids: list[str],
        key_id_extensions: Optional[dict[str, dict[str, Any]]] = None,
        key_ids_extension: Optional[dict[str, Any]] = None,
    ) -> KeysContainer:
        """Fetch keys by key_ID and return the full ETSI 014 §5.4 container.

        Parameters
        ----------
        slave_sae_id : str
            The SAE ID of the decrypting peer (this client).
        key_ids : list[str]
            The key identifiers to retrieve, previously obtained by the
            master SAE via ``get_enc_keys``.
        key_id_extensions : dict[str, dict], optional
            Per-key extension data, keyed by key_ID (ETSI 014 §5.4.2
            ``key_ID_extension``).
        key_ids_extension : dict, optional
            Container-level extension data for the request
            (ETSI 014 §5.4.2 ``key_IDs_extension``).
        """
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
        data = self._post_json(url, json=body)
        return self._parse_keys_container(data)

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    def __enter__(self) -> "ETSI014Client":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # ── HTTP helpers ───────────────────────────────────────────────────────

    def _get_json(self, url: str, params: Optional[dict] = None) -> dict:
        response = self._session.get(
            url,
            params=params,
            headers=self.extra_headers,
            cert=self.client_cert,
            verify=self.verify,
            timeout=self.timeout,
        )
        return self._handle_response(response)

    def _post_json(self, url: str, json: dict) -> dict:
        response = self._session.post(
            url,
            json=json,
            headers={**self.extra_headers, "Content-Type": "application/json"},
            cert=self.client_cert,
            verify=self.verify,
            timeout=self.timeout,
        )
        return self._handle_response(response)

    @staticmethod
    def _handle_response(response: requests.Response) -> dict:
        if response.ok:
            return response.json()

        try:
            message = response.json().get("message", response.text)
        except ValueError:
            message = response.text

        if response.status_code == 404:
            raise KMENotFoundError(message)
        raise KMEHTTPError(response.status_code, message)

    # ── Parsers (also usable by an async sibling) ──────────────────────────

    @staticmethod
    def _parse_status(data: dict) -> StatusResponse:
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

    @staticmethod
    def _parse_keys_container(data: dict) -> KeysContainer:
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

    @staticmethod
    def _parse_keys(data: dict) -> list[KeyResponse]:
        """Backwards-compatible helper retained from v0.1."""
        return ETSI014Client._parse_keys_container(data).keys
