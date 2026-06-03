<!--
Thanks for opening a pull request! Please fill out this template so reviewers
can land your change quickly.

For larger changes, please open an issue first to discuss the design.
-->

## Summary

<!-- One or two sentences describing the change and why it is needed. -->

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (would change existing API or behavior)
- [ ] Documentation only
- [ ] Internal refactor / tests / tooling

## Affected subpackage(s)

- [ ] `qkdsec.client`
- [ ] `qkdsec.client.aio`
- [ ] `qkdsec.doctor`
- [ ] `qkdsec.proofs`
- [ ] `qkdsec.sim`
- [ ] CLI
- [ ] Packaging
- [ ] Docs

## Standards reference

<!-- If this PR touches the ETSI 014 client or doctor, cite the clause:
     e.g., "ETSI GS QKD 014 v1.1.1 §5.3.2". -->

## Test plan

- [ ] `pytest -v` passes locally on Python 3.12
- [ ] New tests cover the change (or the change is doc-only)
- [ ] Existing tests still pass

<!-- Describe any manual verification, e.g. ran `qkdsec doctor` against a
     real or stub KME. -->

## Checklist

- [ ] I have read [CONTRIBUTING.md](../CONTRIBUTING.md).
- [ ] `CHANGELOG.md` has an entry under `## [Unreleased]`.
- [ ] Public API changes are reflected in `docs/` and the README.
- [ ] The PR contains one logical change (no unrelated formatting churn).

## Related issues

<!-- e.g., Fixes #123, Refs #456 -->
