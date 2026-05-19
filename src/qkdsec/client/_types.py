"""Response types for the ETSI GS QKD 014 client.

The types here cover the full ETSI GS QKD 014 v1.1.1 spec, including vendor
extensions. All extension fields are optional; the client populates them when
present in the KME response and leaves them as ``None`` otherwise.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class KeyResponse:
    """A single key fetched from the KME (ETSI 014 §5.3.3 / §5.4.3).

    Attributes
    ----------
    key_id : str
        The KME-assigned key identifier (UUID). Used to retrieve the matching
        key on the slave SAE via ``get_dec_keys``.
    key : bytes
        The raw key material. The wire format is base64; this field is
        already decoded.
    key_id_extension : dict, optional
        Vendor-specific or non-standard extension data attached to the key
        identifier (ETSI 014 §5.3.3 ``key_ID_extension``).
    key_extension : dict, optional
        Vendor-specific or non-standard extension data attached to the key
        itself (ETSI 014 §5.3.3 ``key_extension``).
    """

    key_id: str
    key: bytes
    key_id_extension: Optional[dict[str, Any]] = None
    key_extension: Optional[dict[str, Any]] = None

    @property
    def size_bits(self) -> int:
        return len(self.key) * 8


@dataclass(frozen=True)
class KeysContainer:
    """A container of keys returned by enc_keys / dec_keys (ETSI 014 §5.3.3).

    Wraps ``list[KeyResponse]`` to also surface the optional container-level
    extension. Iterating over a ``KeysContainer`` yields its keys, so most
    callers can treat it like a list.

    Attributes
    ----------
    keys : list[KeyResponse]
    key_container_extension : dict, optional
        Vendor-specific extension data attached to the container as a whole
        (ETSI 014 §5.3.3 ``key_container_extension``).
    """

    keys: list[KeyResponse] = field(default_factory=list)
    key_container_extension: Optional[dict[str, Any]] = None

    def __iter__(self):
        return iter(self.keys)

    def __len__(self) -> int:
        return len(self.keys)

    def __getitem__(self, idx: int) -> KeyResponse:
        return self.keys[idx]


@dataclass(frozen=True)
class StatusResponse:
    """KME status for a given slave SAE (ETSI GS QKD 014 §5.2)."""

    source_kme_id: str
    target_kme_id: str
    master_sae_id: str
    slave_sae_id: str
    key_size: int
    stored_key_count: int
    max_key_count: int
    max_key_per_request: int
    max_key_size: int
    min_key_size: int
    max_sae_id_count: int
    status_extension: Optional[dict[str, Any]] = None
