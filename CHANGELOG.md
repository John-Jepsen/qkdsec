# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

While `qkdsec` is pre-1.0, minor version bumps may include breaking changes.
Breaking changes are called out under a **Changed** or **Removed** heading.

## [Unreleased]

### Added
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, and GitHub issue / PR
  templates.
- `scripts/sync-to-standalone.sh` for syncing the in-monorepo copy to the
  standalone PyPI source repo.
- Development section in README.

## [0.2.0] — 2025-05-19

### Added
- `qkdsec.client` — full ETSI GS QKD 014 v1.1.1 spec coverage, including
  multicast key delivery (`additional_slave_SAE_IDs`), mandatory and optional
  vendor extensions, and container-level metadata.
- `qkdsec.client.aio.AsyncETSI014Client` — async client built on `httpx`,
  sharing parsers with the sync client.
- `qkdsec.doctor` — KME conformance probe with 10 probes covering §5.2 / §5.3 /
  §5.4. Text (rich), JSON, and HTML reports.
- `qkdsec` CLI — `typer`-based command exposing `doctor`, `status`, `keys get`,
  `keys retrieve`, and `version`.
- Sphinx documentation scaffold (`docs/`) with `furo` theme, `myst-parser`,
  Read the Docs config, and badges in the README.
- Extras: `[async]`, `[cli]`, `[doctor]`, `[docs]`, plus rollups in `[all]`.

### Changed
- README rewritten around the three subpackages and the doctor probe.

## [0.1.0] — 2025-05-19

### Added
- Initial release: pip-installable `qkdsec` package skeleton.
- `qkdsec.proofs` — Shor–Preskill asymptotic bound, two-decoy-state estimator,
  Tomamichel finite-key correction.
- `qkdsec.sim` — BB84 simulator with classical and Qiskit backends.
- Apache-2.0 license.
- GitHub Actions CI matrix (Python 3.10 / 3.11 / 3.12) and PyPI Trusted
  Publishing release workflow.

[Unreleased]: https://github.com/John-Jepsen/qkdsec/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/John-Jepsen/qkdsec/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/John-Jepsen/qkdsec/releases/tag/v0.1.0
