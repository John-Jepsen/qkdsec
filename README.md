# qkdsec

[![PyPI](https://img.shields.io/pypi/v/qkdsec.svg)](https://pypi.org/project/qkdsec/)
[![Python](https://img.shields.io/pypi/pyversions/qkdsec.svg)](https://pypi.org/project/qkdsec/)
[![CI](https://github.com/John-Jepsen/qkdsec/actions/workflows/ci.yml/badge.svg)](https://github.com/John-Jepsen/qkdsec/actions/workflows/ci.yml)
[![Docs](https://readthedocs.org/projects/qkdsec/badge/?version=latest)](https://qkdsec.readthedocs.io/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**The developer toolkit for Quantum Key Distribution.** Pull keys from any
ETSI-compliant KME, prove your vendor actually implements the spec, compute
provable key-rate bounds, and simulate BB84 — all from one `pip install`.

## Why qkdsec

Most ETSI GS QKD 014 client libraries implement the happy path and stop there.
`qkdsec` ships the only **runnable conformance probe** for the standard:

```bash
qkdsec doctor https://kme.your-vendor.com --slave-sae-id sae-bob \
    --cert alice.crt --key alice.key
```

```
qkdsec doctor — https://kme.your-vendor.com
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

Exit code 0 if conformant, 1 if not — drops straight into CI. Text output for
humans, JSON for pipelines, HTML for sharing with your vendor.

The rest of the library is built around the same idea: give developers the
pieces they actually need, with each subpackage installable on its own.

## Who this is for

`qkdsec` is built for three kinds of developer. Pick the one that sounds like
you — that tells you which subpackage and extras to install.

### Ops engineers integrating a real KME

You bought a QKD box from Toshiba, ID Quantique, QuantumCTek, LuxQuanta, or
similar. The vendor handed you an ETSI GS QKD 014 endpoint and a client cert.
Now you need to pull keys from it and pipe them into TLS / IPsec / your own
service.

Use `qkdsec.client` + `qkdsec doctor`:

- Pull keys from your KME with a few lines of Python — sync for scripts, async
  for FastAPI / asyncio services.
- Run `qkdsec doctor` against your KME in CI to catch spec regressions before
  they hit production.
- Audit a vendor *before* signing the PO — point doctor at their demo KME and
  see what they actually implement vs. claim.

```bash
pip install "qkdsec[doctor]"   # CLI + doctor + async client
```

```python
from qkdsec.client import ETSI014Client

with ETSI014Client(
    "https://kme.example.com",
    client_cert=("alice.crt", "alice.key"),
) as kme:
    keys = kme.get_enc_keys("sae-bob", number=1, size=256)
    psk = keys[0].key   # 32 bytes — feed straight to your TLS/IPsec stack
```

Async — same surface, sharing parsers:

```python
from qkdsec.client.aio import AsyncETSI014Client

async with AsyncETSI014Client(
    "https://kme.example.com",
    client_cert=("alice.crt", "alice.key"),
) as kme:
    keys = await kme.get_enc_keys("sae-bob", number=1, size=256)
```

Full ETSI GS QKD 014 v1.1.1 coverage — including multicast key delivery
(`additional_slave_SAE_IDs`), mandatory and optional vendor extensions, and
container-level metadata. Read the [doctor guide](https://qkdsec.readthedocs.io/)
to see every probe and the clause it tests.

### Researchers and cryptography students

You are writing a paper, thesis, or course assignment that needs a *provable*
secret-key-rate lower bound — not a hand-waving estimate. You want to plot rate
vs. QBER or rate vs. distance for BB84 under realistic channel models without
rolling your own SDP.

Use `qkdsec.proofs`:

- Shor–Preskill asymptotic bound, two-decoy-state estimation, and Tomamichel
  et al. finite-key correction — all behind one function.
- Swap channel models without rewriting your code.
- Cite the result with confidence: it is a lower bound, not an
  order-of-magnitude guess.

```bash
pip install "qkdsec[proofs]"
```

```python
from qkdsec.proofs import key_rate, BB84, DepolarizingChannel

result = key_rate(BB84(), DepolarizingChannel(qber=0.03))
print(f"Lower bound: {result.r_lower:.4f} bits/pulse")
```

### Educators and engineers learning QKD

You want to *see* BB84 work end-to-end without buying single-photon detectors.
You are teaching a class, building intuition for the protocol, or
demonstrating to a stakeholder why QBER > 11 % means abort.

Use `qkdsec.sim`:

- Run the full protocol — basis preparation, transmission, sifting, error
  correction, privacy amplification — and get the final key plus per-stage
  stats.
- Backend-switch between a fast classical numpy simulator (for parameter
  sweeps) and Qiskit Aer (for the actual quantum circuits, when you want to
  teach the underlying physics).
- Inject controlled eavesdropper noise to show *why* the QBER threshold
  matters.

```bash
pip install "qkdsec[sim]"
```

```python
from qkdsec.sim import BB84Protocol

result = BB84Protocol(error_rate=0.01).run(n_bits=4096)
if result.secure:
    print(result.final_key.hex())
else:
    print(f"aborted — QBER {result.qber:.3f} above threshold")
```

The keys produced by the simulator are pedagogical — **never** use them as a
real shared secret. For that, you need real quantum hardware and the
`qkdsec.client` path above.

## Install

Pick the extra that matches your role above. Default install is intentionally
lightweight (only `requests`).

```bash
# ETSI 014 client only (sync, lightweight)
pip install qkdsec

# + async client
pip install "qkdsec[async]"

# + qkdsec CLI and doctor (recommended for ops)
pip install "qkdsec[doctor]"

# + numerical security proofs (researchers)
pip install "qkdsec[proofs]"

# + BB84 simulator (educators)
pip install "qkdsec[sim]"

# Everything
pip install "qkdsec[all]"
```

Heavy dependencies (CVXPY, Qiskit, httpx, typer) live behind extras, so
ops users do not pay for the simulator stack and educators do not pay for
the SDP solver.

## What sets it apart

- **`qkdsec doctor`** — the only runnable ETSI GS QKD 014 v1.1.1 conformance
  probe for Python. Catches vendor spec violations before they reach
  production.
- **Full spec coverage** — multicast key delivery, vendor extensions, and
  container-level metadata, not just the happy path.
- **Sync and async** — `ETSI014Client` for scripts; `AsyncETSI014Client` for
  FastAPI / asyncio services. Same surface, shared parsers.
- **Lightweight default** — heavy deps behind extras; pay only for what you
  use.
- **One library, three audiences** — ops, researchers, educators each get a
  first-class subpackage.

## Standards

- **ETSI GS QKD 014 v1.1.1** — REST API for key delivery (full coverage)
- **BB84** (Bennett & Brassard, 1984)
- **Shor–Preskill** asymptotic key rate
- **Tomamichel et al.** finite-key correction
- **Two-decoy state** estimation

## Documentation

Full docs at [qkdsec.readthedocs.io](https://qkdsec.readthedocs.io/) —
quickstart, doctor guide, async guide, spec coverage walk-through, and API
reference.

## Scope and non-goals

- **What this is:** a developer-facing library for the three roles above.
- **What this is not:** a complete QKD network, a hybrid QKD+PQC system, or a
  vendor-specific SDK. QKD itself requires quantum hardware (single-photon
  sources and detectors over an optical channel). `qkdsec` helps you build
  *around* that hardware, not replace it.

## Development

Clone, install with all extras + test deps, and run the suite:

```bash
git clone https://github.com/John-Jepsen/qkdsec.git
cd qkdsec
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[all,test]"
pytest -v
```

Build the docs:

```bash
pip install -e ".[docs]"
sphinx-build -b html docs docs/_build/html
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for branching, PRs, and release process,
and [SECURITY.md](SECURITY.md) for vulnerability reporting.

## Contributing

Issues and pull requests are welcome on the canonical repo,
[github.com/John-Jepsen/qkdsec](https://github.com/John-Jepsen/qkdsec). See
[CONTRIBUTING.md](CONTRIBUTING.md) to get started.

## License

Apache-2.0
