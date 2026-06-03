# Contributing to qkdsec

Thanks for your interest in contributing! `qkdsec` is a developer toolkit for
Quantum Key Distribution covering numerical security proofs, BB84 simulation, and
the ETSI GS QKD 014 client + conformance probe. Contributions of all sizes are
welcome — bug reports, doc fixes, new tests, and feature work.

## Where this repository lives

The canonical home for external contributors is
[github.com/John-Jepsen/qkdsec](https://github.com/John-Jepsen/qkdsec). That is
where you should:

- File issues
- Open pull requests
- Watch CI results

The package is also developed inside the larger
[`qkd-avantheir`](https://github.com/John-Jepsen/qkd-avantheir) research
monorepo. Internal development may happen there first and is mirrored to the
standalone repo via `scripts/sync-to-standalone.sh`. If you are an external
contributor, you do **not** need to know about the monorepo — work against
`John-Jepsen/qkdsec` as normal.

## Code of Conduct

By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Reporting security issues

Please **do not** open a public issue for security vulnerabilities. See
[SECURITY.md](SECURITY.md) for the private disclosure process.

## Development setup

Requirements:

- Python 3.10, 3.11, or 3.12
- `git`
- A working C/C++ toolchain (needed by some `cvxpy` / `scipy` wheels on certain
  platforms)

Clone and install with all extras plus the test dependencies:

```bash
git clone https://github.com/John-Jepsen/qkdsec.git
cd qkdsec
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -e ".[all,test]"
```

If you only need a subset of subpackages, install the matching extras instead
(see the [Install](README.md#install) section of the README).

## Running the test suite

```bash
pytest -v
```

Subsets:

```bash
pytest tests/client      # ETSI 014 client (sync + async)
pytest tests/doctor      # KME conformance probes + CLI
pytest tests/proofs      # numerical key-rate bounds
pytest tests/sim         # BB84 simulator
```

Async client tests use `respx`; sync client tests use `responses`. Both run
without a real KME.

## Building the docs

```bash
pip install -e ".[docs]"
sphinx-build -b html docs docs/_build/html
open docs/_build/html/index.html
```

## Branching and commits

- Branch from `main`. Use a short descriptive name, e.g.
  `fix/doctor-empty-status`, `feat/etsi014-extension-foo`.
- One logical change per pull request. Refactors and feature work go in
  separate PRs.
- Commit messages: imperative subject under ~72 chars, body wrapped at ~72.
  Reference an issue if applicable (`Fixes #123`).
- Do not add Co-Authored-By trailers or AI-attribution lines.

## Pull request checklist

Before opening a PR, please confirm:

- [ ] `pytest -v` passes locally on at least one supported Python
- [ ] New behavior is covered by tests (unit tests under `tests/<subpackage>/`)
- [ ] Public API changes are reflected in `docs/` and the README
- [ ] `CHANGELOG.md` has an entry under `## [Unreleased]`
- [ ] No unrelated formatting churn in the diff

CI runs `pytest` across Python 3.10–3.12 and builds the sdist + wheel. PRs need
green CI before merge.

## Style

- Keep public APIs typed (`from __future__ import annotations` is fine).
- Prefer composable functions over deep class hierarchies.
- Standards-aligned naming: clause numbers (e.g. `§5.3`) follow ETSI GS QKD 014
  v1.1.1.
- No new runtime dependencies in the base install — heavy deps go behind an
  extra in `pyproject.toml`.

## Where to start

Good first issues are labeled
[`good first issue`](https://github.com/John-Jepsen/qkdsec/issues?q=is%3Aopen+label%3A%22good+first+issue%22).
Areas where help is especially welcome:

- Additional KME conformance probes against real-world vendors
- Decoy-state estimator improvements and tighter finite-key bounds
- More worked examples in `docs/guides/`
- Type-checking coverage (`mypy --strict`)

If you want to propose a larger change, please open an issue first to discuss
the design.

## Releasing (maintainers)

1. Update `CHANGELOG.md`: move `[Unreleased]` entries to a new version section.
2. Bump `version` in `pyproject.toml`.
3. Commit, tag `vX.Y.Z`, push tag.
4. The `publish.yml` workflow builds and publishes to PyPI via Trusted
   Publishing.
