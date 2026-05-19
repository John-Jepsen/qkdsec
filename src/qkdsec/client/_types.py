"""Response types for the ETSI GS QKD 014 client."""

from dataclasses import dataclass


@dataclass(frozen=True)
class KeyResponse:
    """A single key fetched from the KME.

    Attributes
    ----------
    key_id : str
        The KME-assigned key identifier (UUID). Used to retrieve the matching
        key on the slave SAE via ``get_dec_keys``.
    key : bytes
        The raw key material. The wire format is base64; this field is
        already decoded.
    """

    key_id: str
    key: bytes

    @property
    def size_bits(self) -> int:
        return len(self.key) * 8


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
