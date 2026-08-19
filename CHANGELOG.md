# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

While `qkdsec` is pre-1.0, minor version bumps may include breaking changes.
Breaking changes are called out under a **Changed** or **Removed** heading.

## [Unreleased]

### Added
- `BB84Protocol` accepts a `seed` parameter for reproducible simulation runs
  (unseeded runs keep using OS entropy). `BB84Result` gains
  `reconciliation_verified` and `leaked_bits` fields.
- `proofs.BB84` accepts an error-correction inefficiency factor `f_ec`
  (default 1.16, matching practical reconciliation codes; pass 1.0 for
  ideal-reconciliation literature values).
- Public `status_raw()` on both clients returns the §5.2 response as the raw
  JSON dict.
- `py.typed` marker — the package's type hints are now visible to mypy/pyright.
- Qiskit backend test coverage (smoke + eavesdrop-detection tests).
- Ruff lint configuration and CI lint job; coverage reporting in CI; CI now
  tests Python 3.13; the publish workflow runs the test suite before building.
-  qkdsec mock serve (mentions the ETSI 014 routes and that it passes doctor)

### Changed
- **Simulator security semantics.** BB84 error correction is now Cascade-style
  parity reconciliation that consults Alice's bits only through announced
  parities (the old code read her bits directly and silently produced
  divergent Alice/Bob keys when a block held an even number of errors). A
  hash-verification step marks unreconciled runs insecure, and privacy
  amplification output is capped by the entropy budget
  `n − n·h(QBER) − leaked_bits` instead of always emitting 256 bits.
  QBER estimation now samples random sifted positions, and probabilities are
  no longer quantized to 1/1000 granularity.
- **Conservative decoy clamping.** `two_decoy_bounds` clamps a negative raw
  `e_1` upper bound to the pessimistic 0.5 instead of 0 (which certified zero
  single-photon errors from inconsistent statistics).
- The sync client no longer closes a `requests.Session` you passed in,
  matching the async client's ownership contract. The async client now
  applies `extra_headers`/`timeout` per-request (so they work with injected
  clients) and raises `ValueError` if `client_cert`/`verify` are combined
  with an injected client instead of silently ignoring them.
- KME error responses whose JSON body is not an object (arrays, bare strings)
  no longer raise `AttributeError`; they are reported via `KMEHTTPError`.
- Doctor: the latency probe reports a true nearest-rank percentile (the old
  p99 formula returned an interior sample); the caps probe drops its unused
  `max_size` parameter and skips when the stored pool is too small to
  distinguish cap enforcement from exhaustion; `Report`/`ProbeResult`/
  `ProbeStatus` moved to `qkdsec.doctor.report` (re-exported from `probes`
  for backwards compatibility).
- `solve_key_rate_sdp` returns a failed `KeyRateResult` on `SolverError`
  instead of raising.
- CLI: `--format` is enum-validated; `keys get`/`keys retrieve` print a
  stderr warning that key material is going to stdout.
- Extras `all` and `doctor` are now self-referential
  (`qkdsec[proofs,sim,async,cli]` / `qkdsec[cli]`); `doctor` no longer pulls
  in `httpx`, which it never used.

## [0.3.0] — 2026-07-02

### Added
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, and GitHub issue / PR
  templates.
- Development section in README; README restructured around three audience
  personas (ops engineers, researchers, educators).

### Changed
- The package version is now derived from git tags via `setuptools-scm`
  instead of being hardcoded in `pyproject.toml` and `qkdsec/__init__.py`.
  Tagged releases build as the tag version (`v0.2.0` → `0.2.0`); untagged
  commits build as dev versions (e.g., `0.2.1.dev3+g2d48e42`). Cutting a
  release is now just tagging: `git tag v0.x.y && git push --tags`.
- The `qkd-avantheir` research monorepo now consumes this repository as a git
  submodule instead of a vendored copy with a sync script. No user-facing
  change; mentioned for archaeological clarity.

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

[Unreleased]: https://github.com/John-Jepsen/qkdsec/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/John-Jepsen/qkdsec/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/John-Jepsen/qkdsec/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/John-Jepsen/qkdsec/releases/tag/v0.1.0
