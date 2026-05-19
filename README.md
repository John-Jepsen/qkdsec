# qkdsec

[![PyPI](https://img.shields.io/pypi/v/qkdsec.svg)](https://pypi.org/project/qkdsec/)
[![Python](https://img.shields.io/pypi/pyversions/qkdsec.svg)](https://pypi.org/project/qkdsec/)
[![CI](https://github.com/John-Jepsen/qkdsec/actions/workflows/ci.yml/badge.svg)](https://github.com/John-Jepsen/qkdsec/actions/workflows/ci.yml)
[![Docs](https://readthedocs.org/projects/qkdsec/badge/?version=latest)](https://qkdsec.readthedocs.io/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

A developer toolkit for Quantum Key Distribution: numerical security proofs, BB84 simulation, and an ETSI GS QKD 014 client with a built-in KME conformance probe.

`qkdsec` is one library with three subpackages, each addressing a different need:

- **`qkdsec.proofs`** — Provable secret-key-rate lower bounds for QKD protocols under given channel models.
- **`qkdsec.sim`** — Working BB84 simulator (Qiskit and classical backends).
- **`qkdsec.client`** — Full ETSI GS QKD 014 v1.1.1 client (sync **and** async), plus a `qkdsec doctor` conformance probe that audits any KME.

## What sets it apart

- **`qkdsec doctor`** — point it at any KME and get a colored conformance report against ETSI GS QKD 014 v1.1.1. Catches spec violations before they bite production. JSON output for CI; HTML output for sharing.
- **Full spec coverage** — multicast key delivery (`additional_slave_SAE_IDs`), mandatory/optional vendor extensions, and container-level metadata. Most KME clients only implement the happy path.
- **Sync and async** — `ETSI014Client` for scripts and `AsyncETSI014Client` for FastAPI / asyncio services. Same surface, share parsers.
- **Lightweight default** — `pip install qkdsec` brings only `requests`. Heavy deps (CVXPY, Qiskit, httpx, typer) are behind extras.

## Install

```bash
# ETSI 014 client only (sync, lightweight)
pip install qkdsec

# + async client
pip install "qkdsec[async]"

# + qkdsec CLI and doctor (recommended for ops)
pip install "qkdsec[doctor]"

# + numerical security proofs
pip install "qkdsec[proofs]"

# + BB84 simulator (Qiskit backend)
pip install "qkdsec[sim]"

# Everything
pip install "qkdsec[all]"
```

## Quick start

### Audit a KME in 30 seconds

```bash
qkdsec doctor https://kme.example.com \
    --slave-sae-id sae-bob \
    --cert alice.crt --key alice.key
```

```
qkdsec doctor — https://kme.example.com
slave SAE: sae-bob

  PASS  reachability         [§5.2]      45 ms
  PASS  status_fields        [§5.2.2]    12 ms
  PASS  enc_keys_get         [§5.3]     108 ms
  PASS  enc_keys_post        [§5.3]      94 ms
  PASS  enc_keys_caps        [§5.3]      31 ms
  WARN  extensions_accepted  [§5.3.2]    28 ms
        KME returned HTTP 400 with extension_optional present.
  PASS  dec_keys_roundtrip   [§5.4]     142 ms
  PASS  error_contract_404   [§5.4]      19 ms
  PASS  error_contract_400   [§5.3]      18 ms
  PASS  latency                          14 ms

  Summary: 9 pass, 1 warn, 0 fail, 0 skip
  Verdict: CONFORMANT  (511 ms total)
```

Exit code 0 if conformant, 1 if not — drop in CI directly.

### Fetch a key (sync)

```python
from qkdsec.client import ETSI014Client

with ETSI014Client(
    "https://kme.example.com",
    client_cert=("alice.crt", "alice.key"),
) as kme:
    keys = kme.get_enc_keys("sae-bob", number=1, size=256)
    print(keys[0].key.hex())
```

### Fetch a key (async)

```python
from qkdsec.client.aio import AsyncETSI014Client

async with AsyncETSI014Client(
    "https://kme.example.com",
    client_cert=("alice.crt", "alice.key"),
) as kme:
    keys = await kme.get_enc_keys("sae-bob", number=1, size=256)
```

### Compute a provable key rate

```python
from qkdsec.proofs import key_rate, BB84, DepolarizingChannel

result = key_rate(BB84(), DepolarizingChannel(qber=0.03))
print(f"Lower bound: {result.r_lower:.4f} bits/pulse")
```

### Simulate a BB84 exchange

```python
from qkdsec.sim import BB84Protocol

result = BB84Protocol(error_rate=0.01).run(n_bits=4096)
if result.secure:
    print(result.final_key.hex())
```

## Standards

- **ETSI GS QKD 014 v1.1.1** — REST API for key delivery (full coverage)
- **BB84** (Bennett & Brassard, 1984)
- **Shor–Preskill** asymptotic key rate
- **Tomamichel et al.** finite-key correction
- **Two-decoy state** estimation

## Documentation

Full docs at [qkdsec.readthedocs.io](https://qkdsec.readthedocs.io/) — quickstart, doctor guide, async guide, spec coverage walk-through, and API reference.

## Scope and non-goals

- **What this is:** a developer-facing library for the three roles above.
- **What this is not:** a complete QKD network, a hybrid QKD+PQC system, or a vendor-specific SDK. QKD itself requires quantum hardware (single-photon sources and detectors over an optical channel). This library helps you build *around* that hardware.

## License

Apache-2.0
