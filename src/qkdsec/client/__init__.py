"""ETSI GS QKD 014 REST client for Key Management Entity (KME) systems.

Use this to fetch quantum keys from real QKD hardware (Toshiba, ID Quantique,
QuantumCTek, etc.) or from a local KME simulator. Both synchronous and
asynchronous clients are provided.

Sync example:
    >>> from qkdsec.client import ETSI014Client
    >>> kme = ETSI014Client("https://kme.example.com",
    ...                     client_cert=("alice.crt", "alice.key"))
    >>> status = kme.status("sae-bob")
    >>> keys = kme.get_enc_keys("sae-bob", number=1, size=256)

Async example (requires ``pip install qkdsec[async]``)::

    from qkdsec.client.aio import AsyncETSI014Client

    async with AsyncETSI014Client("https://kme.example.com",
                                  client_cert=("alice.crt", "alice.key")) as kme:
        keys = await kme.get_enc_keys("sae-bob", number=1, size=256)
"""

from ._types import KeyResponse, KeysContainer, StatusResponse
from .errors import KMEError, KMEHTTPError, KMENotFoundError
from .etsi014 import ETSI014Client

__all__ = [
    "ETSI014Client",
    "KeyResponse",
    "KeysContainer",
    "StatusResponse",
    "KMEError",
    "KMEHTTPError",
    "KMENotFoundError",
]
