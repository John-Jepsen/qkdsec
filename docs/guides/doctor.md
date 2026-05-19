# Doctor — KME conformance probe

`qkdsec doctor` runs a battery of probes against any ETSI GS QKD 014 KME and emits a conformance report. Use it when you stand up a new KME, when you switch vendors, or as a smoke test in CI before promoting a build.

## What it probes

The doctor exercises every endpoint in ETSI GS QKD 014 v1.1.1 §5 and checks that the KME behaves as the spec requires.

| Probe | Spec | What it checks |
|---|---|---|
| `reachability` | §5.2 | TLS handshake, authentication, the KME answers. |
| `status_fields` | §5.2.2 | All required fields present with correct types; non-standard fields flagged as warnings. |
| `enc_keys_get` | §5.3 | GET returns a valid key of the requested size; base64 decoding works. |
| `enc_keys_post` | §5.3 | POST works as an alternative to GET (warn if KME rejects). |
| `enc_keys_caps` | §5.3 | Requesting more than `max_key_per_request` is rejected with HTTP 400. |
| `extensions_accepted` | §5.3.2 | KME tolerates an `extension_optional` field (must not cause rejection). |
| `dec_keys_roundtrip` | §5.4 | enc_keys → dec_keys returns the same bytes. |
| `error_contract_404` | §5.4 | Unknown key_ID returns HTTP 404. |
| `error_contract_400` | §5.3 | Non-multiple-of-8 key size returns HTTP 400. |
| `latency` | — | p50/p99 latency over N status calls. Informational. |

Each probe returns one of four statuses: `pass`, `warn`, `fail`, `skip`.

- **`fail`** means the KME violates a MUST in the spec.
- **`warn`** means the KME violates a SHOULD, or returns extra fields the spec does not name.
- **`pass`** means the probe was satisfied.
- **`skip`** means the probe was suppressed (for example, `--no-consume` skips probes that draw keys).

The overall verdict is **`CONFORMANT`** if every probe is `pass`/`warn`/`skip`. A single `fail` makes the verdict **`NON-CONFORMANT`** and the CLI exits with status 1.

## Usage

### Basic

```bash
qkdsec doctor https://kme.example.com \
    --slave-sae-id sae-bob \
    --cert alice.crt --key alice.key \
    --ca-cert ca.crt
```

### Without consuming keys

In production you may not want the doctor to draw real key material. Add `--no-consume` and the doctor only exercises the read-only probes (reachability, status, latency, error contracts).

```bash
qkdsec doctor https://kme.example.com --no-consume \
    --cert alice.crt --key alice.key
```

### JSON output for CI

```bash
qkdsec doctor https://kme.example.com \
    --cert alice.crt --key alice.key \
    --format json --output report.json
```

`report.json` is stable for diffing and easy to parse from CI:

```json
{
  "base_url": "https://kme.example.com",
  "slave_sae_id": "sae-bob",
  "counts": {"pass": 9, "warn": 1, "fail": 0, "skip": 0},
  "passed": true,
  "total_latency_ms": 482.1,
  "results": [
    {"name": "reachability", "status": "pass", "spec_section": "§5.2", ...},
    ...
  ]
}
```

### HTML report for sharing

```bash
qkdsec doctor https://kme.example.com \
    --cert alice.crt --key alice.key \
    --format html --output report.html
```

The HTML is self-contained — no external CSS, no JavaScript. Drop it in a PR description, a Slack message, or a compliance audit folder.

## Programmatic use

You do not have to go through the CLI. The Python API gives you the same probes:

```python
from qkdsec.client import ETSI014Client
from qkdsec.doctor import run_all, format_text, format_json

client = ETSI014Client(
    "https://kme.example.com",
    client_cert=("alice.crt", "alice.key"),
)

report = run_all(client, slave_sae_id="sae-bob", consume_keys=False)

print(format_text(report))            # colored terminal output
with open("report.json", "w") as f:
    f.write(format_json(report))

if not report.passed:
    raise SystemExit("KME failed conformance probe")
```

You can also call individual probes directly — see [`qkdsec.doctor.probes`](../api/doctor.rst).

## Interpreting common warnings

- **`status_fields: WARN` with `unknown_fields`** — the KME returns a field that ETSI 014 does not define. This is almost always a vendor extension and is fine. Note the field name; you may want to consume it via the `status_extension` attribute.
- **`extensions_accepted: WARN`** — the KME returns 400 when the request contains an `extension_optional` field. ETSI 014 §5.3.2 says optional extensions MUST NOT cause rejection. Report to your vendor.
- **`error_contract_404: WARN`** — the KME returns 200 OK with an empty key list for an unknown `key_ID`. Spec requires 404. Application code that relies on the 404 will silently misbehave.
- **`enc_keys_caps: WARN`** — the KME does not enforce `max_key_per_request`. Not a security failure, but suggests the rate-limiting story is weaker than the status response implies.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | All probes `pass`, `warn`, or `skip`. KME is conformant. |
| 1 | At least one probe `fail`. KME is non-conformant. |
| 2 | Invalid CLI arguments. |
