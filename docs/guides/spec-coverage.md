# ETSI GS QKD 014 spec coverage

`qkdsec.client` implements the full ETSI GS QKD 014 v1.1.1 request and response surface, including the parts that most KME clients skip — multicast key delivery, mandatory and optional extensions, and container-level metadata.

This guide walks through each spec feature with a code sample.

## Endpoint summary

| Endpoint | Method | Spec | Sync method | Async method |
|---|---|---|---|---|
| `/api/v1/keys/{slave_SAE_ID}/status` | GET | §5.2 | `status` | `status` |
| `/api/v1/keys/{slave_SAE_ID}/enc_keys` | GET / POST | §5.3 | `get_enc_keys` / `get_enc_keys_container` | same |
| `/api/v1/keys/{slave_SAE_ID}/dec_keys` | POST | §5.4 | `get_dec_keys` / `get_dec_keys_container` | same |

Each list-returning method has a `_container` sibling that returns the full `KeysContainer` (including `key_container_extension`).

## Multicast — `additional_slave_SAE_IDs`

ETSI 014 §5.3 lets a master SAE deliver the **same key** to multiple slave SAEs. Pass `additional_slave_sae_ids` to `get_enc_keys`. The client automatically promotes the request to POST (GET cannot carry the list).

```python
keys = kme.get_enc_keys(
    "sae-bob",                                  # primary slave
    number=1,
    size=256,
    additional_slave_sae_ids=["sae-charlie", "sae-dave"],
)
# All three of sae-bob, sae-charlie, sae-dave can now retrieve the same
# key by key_ID via their respective KME's dec_keys endpoint.
```

Use this for one-to-many encrypted channels (group multicast, cluster heartbeat, etc.) where every receiver needs the identical symmetric key.

## Vendor extensions

ETSI 014 §5.3.2 defines two extension fields for the request body:

- **`extension_mandatory`** — vendor parameters the KME **must** honor. If it cannot satisfy them, it returns 400.
- **`extension_optional`** — vendor parameters the KME **may** honor. Best-effort; the spec forbids rejection on these alone.

Passing either to `get_enc_keys` automatically forces a POST.

```python
keys = kme.get_enc_keys(
    "sae-bob",
    number=1,
    size=256,
    extension_mandatory=[{"route_type": "primary"}],
    extension_optional=[{"preferred_qber": 0.02}],
)
```

The exact field names and semantics inside each dict are **vendor-defined**. Consult your KME documentation.

## Per-key extensions on the response

ETSI 014 §5.3.3 lets the KME attach extension data to each returned key:

- `key_ID_extension` — extra metadata about the identifier (e.g., epoch, ttl).
- `key_extension` — extra metadata about the key material (e.g., observed QBER at generation time).

These come through on `KeyResponse`:

```python
keys = kme.get_enc_keys("sae-bob", number=1, size=256)
print(keys[0].key_id_extension)  # dict or None
print(keys[0].key_extension)     # dict or None
```

## Container-level extensions

For metadata that applies to the entire response — batch IDs, audit tokens, vendor health hints — ETSI 014 defines `key_container_extension` on the response and `key_IDs_extension` on the request.

To read `key_container_extension`, use the `_container` form:

```python
container = kme.get_enc_keys_container("sae-bob", number=2, size=256)
print(container.key_container_extension)  # dict or None
for key in container:                      # iterates over .keys
    print(key.key_id)
```

To send `key_IDs_extension` on a dec_keys request:

```python
kme.get_dec_keys(
    "sae-bob",
    key_ids=["k-1", "k-2"],
    key_ids_extension={"audit_id": "audit-2026-001"},
)
```

Per-key extensions on dec_keys requests work the same way:

```python
kme.get_dec_keys(
    "sae-bob",
    key_ids=["k-1"],
    key_id_extensions={"k-1": {"hint": "use_in_session_2"}},
)
```

## Status extensions

Some KMEs include vendor-specific health or capacity hints in the status response (`status_extension`):

```python
status = kme.status("sae-bob")
print(status.status_extension)  # dict or None — e.g., {"vendor_health": "GREEN"}
```

## Conformance verification

Want to know which of these your specific KME actually supports? Run [`qkdsec doctor`](doctor.md) — the `extensions_accepted` probe will flag vendors that incorrectly reject `extension_optional`, and the `unknown_fields` warnings in `status_fields` will surface vendor extensions you may want to consume.

## Backwards compatibility

All extension parameters are optional. Existing v0.1 code that calls `get_enc_keys(slave_sae_id, number=N, size=S)` keeps working without changes — the new keyword arguments default to `None` and the list-returning methods still return `list[KeyResponse]`.
