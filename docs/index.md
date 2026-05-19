# qkdsec

A developer toolkit for Quantum Key Distribution: numerical security proofs, BB84 simulation, and an ETSI GS QKD 014 client with a built-in KME conformance probe.

`qkdsec` is one library with three subpackages, each addressing a different need:

- **`qkdsec.proofs`** — Compute provable secret-key-rate lower bounds for QKD protocols under a given channel model. Useful for protocol selection and due diligence.
- **`qkdsec.sim`** — A working BB84 simulator (Qiskit and classical backends). Useful for development and testing without QKD hardware.
- **`qkdsec.client`** — A synchronous and asynchronous REST client for the ETSI GS QKD 014 Key Management Entity (KME) API. The package also ships a conformance probe ([`qkdsec doctor`](guides/doctor.md)) that audits any KME against ETSI GS QKD 014 v1.1.1.

## Install

```bash
# ETSI 014 client only (lightweight default)
pip install qkdsec

# + numerical security proofs
pip install "qkdsec[proofs]"

# + BB84 simulator (Qiskit backend)
pip install "qkdsec[sim]"

# + async client and CLI (includes the qkdsec doctor)
pip install "qkdsec[doctor]"

# Everything
pip install "qkdsec[all]"
```

## At a glance

```{toctree}
:maxdepth: 1
:caption: Getting started

quickstart
```

```{toctree}
:maxdepth: 1
:caption: Guides

guides/doctor
guides/async
guides/spec-coverage
```

```{toctree}
:maxdepth: 1
:caption: API reference

api/client
api/doctor
api/proofs
api/sim
```

## Standards

- **ETSI GS QKD 014 v1.1.1** — REST API for key delivery (full coverage)
- **BB84** (Bennett & Brassard, 1984)
- **Shor–Preskill** asymptotic key rate
- **Tomamichel et al.** finite-key correction
- **Two-decoy state** estimation

## License

Apache-2.0
