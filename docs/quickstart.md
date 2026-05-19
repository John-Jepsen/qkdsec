# Quickstart

This page gets you from `pip install` to a working KME interaction in under five minutes.

## Install

```bash
pip install "qkdsec[doctor]"
```

The `doctor` extra pulls in everything needed for the CLI and the conformance probe (async client, typer, rich). For the lightest possible install — just the sync REST client — `pip install qkdsec` is enough.

## Verify the install

```bash
qkdsec version
```

## 30-second tour

### Probe a KME for ETSI 014 conformance

```bash
qkdsec doctor https://kme.example.com \
    --slave-sae-id sae-bob \
    --cert alice.crt --key alice.key
```

This runs the full conformance battery (status, enc_keys GET, enc_keys POST, caps enforcement, extension passthrough, dec_keys round-trip, error contracts, latency) and prints a colored verdict. Exit code is 0 if conformant, 1 otherwise — drop it in CI.

### Fetch a key (master SAE)

```bash
qkdsec keys get https://kme.example.com sae-bob \
    --cert alice.crt --key alice.key \
    --size 256
```

### Retrieve a key by ID (slave SAE)

```bash
qkdsec keys retrieve https://kme.example.com sae-bob <key_id> \
    --cert bob.crt --key bob.key
```

## In Python

### Sync

```python
from qkdsec.client import ETSI014Client

with ETSI014Client(
    "https://kme.example.com",
    client_cert=("alice.crt", "alice.key"),
) as kme:
    status = kme.status("sae-bob")
    keys = kme.get_enc_keys("sae-bob", number=1, size=256)
    print(keys[0].key.hex())
```

### Async

```python
from qkdsec.client.aio import AsyncETSI014Client

async with AsyncETSI014Client(
    "https://kme.example.com",
    client_cert=("alice.crt", "alice.key"),
) as kme:
    keys = await kme.get_enc_keys("sae-bob", number=1, size=256)
```

## Next steps

- [Doctor guide](guides/doctor.md) — full details on each probe and how to read the report.
- [Async guide](guides/async.md) — concurrency patterns and lifecycle.
- [Spec coverage guide](guides/spec-coverage.md) — multicast, extensions, container responses.
