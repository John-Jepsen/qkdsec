# qkdsec

A developer toolkit for Quantum Key Distribution: numerical security proofs, BB84 simulation, and an ETSI GS QKD 014 client.

`qkdsec` is one library with three subpackages, each addressing a different need around QKD:

- **`qkdsec.proofs`** — Compute provable secret-key-rate lower bounds for QKD protocols under a given channel model. Useful for protocol selection, due diligence, and parameter tuning.
- **`qkdsec.sim`** — A working BB84 simulator (Qiskit and classical backends). Useful for development, testing, and education when you do not have QKD hardware.
- **`qkdsec.client`** — A synchronous REST client for the ETSI GS QKD 014 Key Management Entity (KME) API. Useful for fetching real quantum keys from QKD hardware (Toshiba, IDQ, QuantumCTek, etc.) and plugging them into your application.

## Install

```bash
# ETSI 014 client only (lightweight default)
pip install qkdsec

# + numerical security proofs
pip install "qkdsec[proofs]"

# + BB84 simulator (Qiskit backend)
pip install "qkdsec[sim]"

# Everything
pip install "qkdsec[all]"
```

## Quick start

### 1. Compute a provable key rate

```python
from qkdsec.proofs import key_rate, BB84, DepolarizingChannel

result = key_rate(BB84(), DepolarizingChannel(qber=0.03))
print(f"Lower bound: {result.r_lower:.4f} bits/pulse")
print(f"Secure: {result.secure}")
```

### 2. Simulate a BB84 key exchange

```python
from qkdsec.sim import BB84Protocol

result = BB84Protocol(error_rate=0.01).run(n_bits=4096)
if result.secure:
    print(f"Shared key: {result.final_key.hex()}")
```

### 3. Fetch keys from a real KME (ETSI GS QKD 014)

```python
from qkdsec.client import ETSI014Client

kme = ETSI014Client(
    base_url="https://kme.example.com",
    client_cert=("alice.crt", "alice.key"),
    verify="ca.crt",
)

status = kme.status(slave_sae_id="sae-bob")
print(f"Available keys: {status.stored_key_count}")

# Master SAE (Alice) — fetch a fresh 256-bit key
keys = kme.get_enc_keys(slave_sae_id="sae-bob", number=1, size=256)
print(f"Key {keys[0].key_id}: {keys[0].key.hex()}")

# Slave SAE (Bob) — fetch by key_ID
mirror = kme.get_dec_keys(slave_sae_id="sae-bob", key_ids=[keys[0].key_id])
assert mirror[0].key == keys[0].key
```

## Scope and non-goals

- **What this is:** a developer-facing library for the three roles above.
- **What this is not:** a complete QKD network, a hybrid QKD+PQC system, or a vendor-specific SDK. QKD itself requires quantum hardware (single-photon sources and detectors over an optical channel). This library helps you build *around* that hardware.

## Standards

- ETSI GS QKD 014 (REST API for key delivery)
- BB84 (Bennett & Brassard, 1984)
- Shor–Preskill key rate bound (asymptotic regime)
- Tomamichel et al. finite-key correction
- Two-decoy state estimation

## License

Apache-2.0
