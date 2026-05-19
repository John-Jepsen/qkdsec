"""Synchronous ETSI GS QKD 014 client.

The ETSI 014 REST API defines three endpoints for KME ↔ SAE interaction:

    GET  /api/v1/keys/{slave_SAE_ID}/status
    GET  /api/v1/keys/{slave_SAE_ID}/enc_keys?number=N&size=S
    POST /api/v1/keys/{slave_SAE_ID}/enc_keys   {"number": N, "size": S}
    POST /api/v1/keys/{slave_SAE_ID}/dec_keys   {"key_IDs": [{"key_ID": "..."}]}

Typical flow (point-to-point, master = Alice, slave = Bob):

    1. Alice's app calls ``get_enc_keys`` against Alice's KME — receives one
       or more ``KeyResponse`` with key bytes + key_id.
    2. Alice sends the key_id (over a classical channel) to Bob.
    3. Bob's app calls ``get_dec_keys`` against Bob's KME with the same
       key_id — receives the matching key bytes.

Both KMEs hold the same key material (synchronized via the quantum channel).
"""

import base64
from typing import Optional, Union

import requests

from ._types import KeyResponse, StatusResponse
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

    # ── Public API ─────────────────────────────────────────────────────────

    def status(self, slave_sae_id: str) -> StatusResponse:
        """Fetch KME status for the given slave SAE (ETSI 014 §5.2)."""
        url = f"{self.base_url}{_API_PREFIX}/{slave_sae_id}/status"
        data = self._get_json(url)
        return self._parse_status(data)

    def get_enc_keys(
        self,
        slave_sae_id: str,
        *,
        number: int = 1,
        size: int = 256,
        method: str = "GET",
    ) -> list[KeyResponse]:
        """Fetch encryption keys for the master SAE (ETSI 014 §5.3).

        Parameters
        ----------
        slave_sae_id : str
            The SAE ID of the intended decrypting peer.
        number : int
            Number of keys to request (KMEs typically cap this at 20).
        size : int
            Key size in bits. Must be a multiple of 8.
        method : str
            ``"GET"`` (query params) or ``"POST"`` (JSON body). Both are
            valid per ETSI 014; some KMEs only accept one.
        """
        url = f"{self.base_url}{_API_PREFIX}/{slave_sae_id}/enc_keys"
        if method.upper() == "GET":
            data = self._get_json(url, params={"number": number, "size": size})
        elif method.upper() == "POST":
            data = self._post_json(url, json={"number": number, "size": size})
        else:
            raise ValueError(f"method must be 'GET' or 'POST', got {method!r}")
        return self._parse_keys(data)

    def get_dec_keys(
        self,
        slave_sae_id: str,
        *,
        key_ids: list[str],
    ) -> list[KeyResponse]:
        """Fetch specific keys by key_ID for the slave SAE (ETSI 014 §5.4)."""
        if not key_ids:
            raise ValueError("key_ids must be a non-empty list")
        url = f"{self.base_url}{_API_PREFIX}/{slave_sae_id}/dec_keys"
        body = {"key_IDs": [{"key_ID": kid} for kid in key_ids]}
        data = self._post_json(url, json=body)
        return self._parse_keys(data)

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
        )

    @staticmethod
    def _parse_keys(data: dict) -> list[KeyResponse]:
        return [
            KeyResponse(
                key_id=item["key_ID"],
                key=base64.b64decode(item["key"]),
            )
            for item in data.get("keys", [])
        ]
