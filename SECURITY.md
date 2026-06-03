# Security Policy

## Scope

`qkdsec` is a developer toolkit. It does **not** itself transport quantum keys
over a quantum channel. The relevant security surface is:

- `qkdsec.client` — talks to a Key Management Entity (KME) over TLS. Bugs that
  could leak key material, mishandle certificates, or accept malformed server
  responses are in scope.
- `qkdsec.doctor` — probes external KMEs. Bugs that could expose credentials or
  produce misleading "conformant" verdicts are in scope.
- `qkdsec.proofs` — numerical key-rate lower bounds. A bug that reports a
  **higher** rate than the true bound is a security issue.
- `qkdsec.sim` — pedagogical BB84 simulator. Not intended for production key
  derivation; results from `sim` should never be used as a real shared secret.

## Supported versions

Security fixes target the most recent minor release on PyPI. We may backport on
request for the previous minor release for up to 6 months.

| Version | Supported           |
| ------- | ------------------- |
| 0.2.x   | :white_check_mark:  |
| 0.1.x   | best-effort         |
| < 0.1   | :x:                 |

`qkdsec` is pre-1.0 (alpha). APIs may still change, but security fixes are a
priority regardless.

## Reporting a vulnerability

**Please do not open a public GitHub issue for security reports.**

Use GitHub's private vulnerability reporting:

  https://github.com/John-Jepsen/qkdsec/security/advisories/new

If that is unavailable, email **jjepsen15@protonmail.com** with subject line
`qkdsec security:` followed by a short description.

Please include:

- Affected version(s) and install extras (e.g. `qkdsec[doctor]==0.2.0`).
- A minimal reproduction or proof-of-concept.
- The impact you believe the issue has.
- Whether you intend to disclose publicly, and on what timeline.

## What to expect

- **Acknowledgement:** within 5 business days.
- **Triage update:** within 10 business days, including a severity assessment.
- **Fix or mitigation:** target 30 days for high-severity, 90 days for lower
  severity. Complex issues may take longer; we will keep you updated.
- **Credit:** with your permission, your name and a link will be included in
  the release notes for the fixing version.

We coordinate on disclosure. Please give us a reasonable window to publish a
fix before public disclosure.

## Out of scope

- Vulnerabilities in upstream dependencies (`requests`, `httpx`, `cvxpy`,
  `qiskit`, etc.) — please report those to the relevant project. We will
  bump pinned versions as part of triage.
- Attacks that require a malicious local user on the same host as the
  `qkdsec` process.
- Denial-of-service via deliberately oversized inputs to local APIs.
- Issues in third-party KMEs that `qkdsec doctor` correctly reports. The
  probe identifying non-conformant behavior is the intended outcome, not a
  bug.
