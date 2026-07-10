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

from typing import Any, Optional

import requests

from . import _common
from ._common import CertType, VerifyType
from ._types import KeyResponse, KeysContainer, StatusResponse


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
        A session you pass in is *not* closed by :meth:`close` — you own it.
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
        self._owns_session = session is None
        self._session = session or requests.Session()

    # ── Status ─────────────────────────────────────────────────────────────

    def status(self, slave_sae_id: str) -> StatusResponse:
        """Fetch KME status for the given slave SAE (ETSI 014 §5.2)."""
        return _common.parse_status(self.status_raw(slave_sae_id))

    def status_raw(self, slave_sae_id: str) -> dict:
        """Fetch the §5.2 status response as the raw JSON dict.

        Useful for conformance tooling that needs to inspect exactly which
        fields the KME returned (see :mod:`qkdsec.doctor`).
        """
        return self._get_json(_common.status_url(self.base_url, slave_sae_id))

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
            data = self._get_json(url, params=params)
        else:
            data = self._post_json(url, json=body)
        return _common.parse_keys_container(data)

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
        body = _common.build_dec_keys_body(
            key_ids, key_id_extensions, key_ids_extension
        )
        url = _common.dec_keys_url(self.base_url, slave_sae_id)
        data = self._post_json(url, json=body)
        return _common.parse_keys_container(data)

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP session (if owned by this instance).

        Sessions passed in via the ``session`` parameter are left open —
        the caller created them and remains responsible for closing them.
        """
        if self._owns_session:
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
            parsed = response.json()
        except ValueError:
            parsed = None
        _common.raise_kme_error(response.status_code, parsed, response.text)

    # ── Parser aliases (kept for backwards compatibility) ─────────────────

    _parse_status = staticmethod(_common.parse_status)
    _parse_keys_container = staticmethod(_common.parse_keys_container)

    @staticmethod
    def _parse_keys(data: dict) -> list[KeyResponse]:
        """Backwards-compatible helper retained from v0.1."""
        return _common.parse_keys_container(data).keys
