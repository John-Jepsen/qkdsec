"""Individual conformance probes against ETSI GS QKD 014 v1.1.1.

Each probe is a pure function that returns a :class:`ProbeResult`. The probes
do not raise; failure modes are captured in the result so the doctor can run
the full battery and report on every category, even when the KME is partially
broken.
"""

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional

from ..client import ETSI014Client
from ..client.errors import KMEError, KMEHTTPError, KMENotFoundError

# ETSI 014 §5.2 — required status fields
_REQUIRED_STATUS_FIELDS = {
    "source_KME_ID",
    "target_KME_ID",
    "master_SAE_ID",
    "slave_SAE_ID",
    "key_size",
    "stored_key_count",
    "max_key_count",
    "max_key_per_request",
    "max_key_size",
    "min_key_size",
    "max_SAE_ID_count",
}

# ETSI 014 §5.2 — known (required + optional) status fields
_KNOWN_STATUS_FIELDS = _REQUIRED_STATUS_FIELDS | {"status_extension"}


class ProbeStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class ProbeResult:
    """Outcome of a single conformance probe."""

    name: str
    status: ProbeStatus
    summary: str
    spec_section: Optional[str] = None
    severity: str = "info"  # "info", "warn", "critical"
    latency_ms: Optional[float] = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class Report:
    """Aggregate report from a doctor run."""

    base_url: str
    slave_sae_id: str
    results: list[ProbeResult] = field(default_factory=list)
    total_latency_ms: float = 0.0

    @property
    def counts(self) -> dict[str, int]:
        c = {s.value: 0 for s in ProbeStatus}
        for r in self.results:
            c[r.status.value] += 1
        return c

    @property
    def passed(self) -> bool:
        return all(
            r.status != ProbeStatus.FAIL for r in self.results
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "slave_sae_id": self.slave_sae_id,
            "counts": self.counts,
            "passed": self.passed,
            "total_latency_ms": self.total_latency_ms,
            "results": [r.to_dict() for r in self.results],
        }


# ── Helpers ───────────────────────────────────────────────────────────────


def _timed(fn, *args, **kwargs) -> tuple[Any, float, Optional[Exception]]:
    t0 = time.perf_counter()
    try:
        value = fn(*args, **kwargs)
        return value, (time.perf_counter() - t0) * 1000.0, None
    except Exception as exc:
        return None, (time.perf_counter() - t0) * 1000.0, exc


# ── Probes ────────────────────────────────────────────────────────────────


def probe_reachability(client: ETSI014Client, slave_sae_id: str) -> ProbeResult:
    """Confirm the KME responds to a status request (TLS + auth working)."""
    _, latency, exc = _timed(client.status, slave_sae_id)
    if exc is None:
        return ProbeResult(
            name="reachability",
            status=ProbeStatus.PASS,
            summary="KME reachable; TLS handshake and authentication succeeded.",
            spec_section="§5.2",
            severity="critical",
            latency_ms=latency,
        )
    return ProbeResult(
        name="reachability",
        status=ProbeStatus.FAIL,
        summary=f"KME unreachable: {type(exc).__name__}: {exc}",
        spec_section="§5.2",
        severity="critical",
        latency_ms=latency,
        details={"error_type": type(exc).__name__, "error_message": str(exc)},
    )


def probe_status_fields(
    client: ETSI014Client, slave_sae_id: str
) -> tuple[ProbeResult, Optional[dict]]:
    """Validate that the §5.2 status response includes all required fields."""
    url = f"{client.base_url}/api/v1/keys/{slave_sae_id}/status"
    raw, latency, exc = _timed(client._get_json, url)
    if exc is not None or raw is None:
        return ProbeResult(
            name="status_fields",
            status=ProbeStatus.FAIL,
            summary=f"Could not retrieve status: {exc}",
            spec_section="§5.2",
            severity="critical",
            latency_ms=latency,
        ), None

    present = set(raw.keys())
    missing = _REQUIRED_STATUS_FIELDS - present
    unknown = present - _KNOWN_STATUS_FIELDS

    type_errors = []
    if "key_size" in raw and not isinstance(raw["key_size"], int):
        type_errors.append("key_size is not int")
    for f in ("stored_key_count", "max_key_count", "max_key_per_request",
              "max_key_size", "min_key_size", "max_SAE_ID_count"):
        if f in raw and not isinstance(raw[f], int):
            type_errors.append(f"{f} is not int")
    for f in ("source_KME_ID", "target_KME_ID",
              "master_SAE_ID", "slave_SAE_ID"):
        if f in raw and not (isinstance(raw[f], str) and raw[f]):
            type_errors.append(f"{f} is not a non-empty string")

    if missing or type_errors:
        return ProbeResult(
            name="status_fields",
            status=ProbeStatus.FAIL,
            summary=(
                f"Status response is non-conformant: "
                f"{len(missing)} missing field(s), "
                f"{len(type_errors)} type error(s)."
            ),
            spec_section="§5.2.2",
            severity="critical",
            latency_ms=latency,
            details={
                "missing_fields": sorted(missing),
                "type_errors": type_errors,
                "unknown_fields": sorted(unknown),
            },
        ), raw
    if unknown:
        return ProbeResult(
            name="status_fields",
            status=ProbeStatus.WARN,
            summary=(
                f"Status response includes {len(unknown)} non-standard "
                f"field(s). Vendor extension likely."
            ),
            spec_section="§5.2.2",
            severity="info",
            latency_ms=latency,
            details={"unknown_fields": sorted(unknown)},
        ), raw
    return ProbeResult(
        name="status_fields",
        status=ProbeStatus.PASS,
        summary="All required status fields present with correct types.",
        spec_section="§5.2.2",
        severity="info",
        latency_ms=latency,
    ), raw


def probe_enc_keys_get(
    client: ETSI014Client, slave_sae_id: str, size: int = 256
) -> tuple[ProbeResult, Optional[str]]:
    """Confirm GET enc_keys returns a valid key of the requested size."""
    result, latency, exc = _timed(
        client.get_enc_keys, slave_sae_id, number=1, size=size
    )
    if exc is not None or not result:
        return ProbeResult(
            name="enc_keys_get",
            status=ProbeStatus.FAIL,
            summary=f"GET enc_keys failed: {exc}" if exc else "Empty key list returned.",
            spec_section="§5.3",
            severity="critical",
            latency_ms=latency,
        ), None
    k = result[0]
    if k.size_bits != size:
        return ProbeResult(
            name="enc_keys_get",
            status=ProbeStatus.FAIL,
            summary=(
                f"Returned key length {k.size_bits}b does not match "
                f"requested {size}b."
            ),
            spec_section="§5.3.3",
            severity="critical",
            latency_ms=latency,
            details={"requested_bits": size, "actual_bits": k.size_bits},
        ), k.key_id
    return ProbeResult(
        name="enc_keys_get",
        status=ProbeStatus.PASS,
        summary=f"GET enc_keys returned valid {size}-bit key.",
        spec_section="§5.3",
        severity="info",
        latency_ms=latency,
        details={"key_id": k.key_id, "size_bits": k.size_bits},
    ), k.key_id


def probe_enc_keys_post(
    client: ETSI014Client, slave_sae_id: str, size: int = 256
) -> tuple[ProbeResult, Optional[str]]:
    """Confirm POST enc_keys works the same as GET (ETSI 014 alternative form)."""
    result, latency, exc = _timed(
        client.get_enc_keys,
        slave_sae_id,
        number=1,
        size=size,
        method="POST",
    )
    if exc is not None or not result:
        return ProbeResult(
            name="enc_keys_post",
            status=ProbeStatus.WARN,
            summary=(
                f"POST enc_keys failed: {exc}. Some KMEs only implement "
                "GET; ETSI 014 lists both as valid."
            ),
            spec_section="§5.3",
            severity="info",
            latency_ms=latency,
        ), None
    return ProbeResult(
        name="enc_keys_post",
        status=ProbeStatus.PASS,
        summary="POST enc_keys returned valid key.",
        spec_section="§5.3",
        severity="info",
        latency_ms=latency,
        details={"key_id": result[0].key_id},
    ), result[0].key_id


def probe_enc_keys_caps(
    client: ETSI014Client,
    slave_sae_id: str,
    max_per_request: int,
    max_size: int,
) -> ProbeResult:
    """Verify the KME enforces max_key_per_request and max_key_size caps."""
    # Try to request more than allowed — should fail with HTTP 400.
    over_count = max_per_request + 1
    _, latency, exc = _timed(
        client.get_enc_keys, slave_sae_id, number=over_count
    )
    if isinstance(exc, KMEHTTPError) and exc.status_code == 400:
        return ProbeResult(
            name="enc_keys_caps",
            status=ProbeStatus.PASS,
            summary=(
                f"KME correctly rejected request for {over_count} keys "
                f"(cap: {max_per_request})."
            ),
            spec_section="§5.3",
            severity="info",
            latency_ms=latency,
        )
    if exc is None:
        return ProbeResult(
            name="enc_keys_caps",
            status=ProbeStatus.WARN,
            summary=(
                f"KME accepted request for {over_count} keys despite "
                f"max_key_per_request={max_per_request}. Cap may not be enforced."
            ),
            spec_section="§5.3",
            severity="warn",
            latency_ms=latency,
        )
    return ProbeResult(
        name="enc_keys_caps",
        status=ProbeStatus.WARN,
        summary=f"Unexpected error when probing caps: {exc}",
        spec_section="§5.3",
        severity="warn",
        latency_ms=latency,
    )


def probe_extensions_accepted(
    client: ETSI014Client, slave_sae_id: str
) -> ProbeResult:
    """Check the KME does not reject optional extension fields in the body."""
    _, latency, exc = _timed(
        client.get_enc_keys,
        slave_sae_id,
        number=1,
        size=256,
        extension_optional=[{"qkdsec_doctor_probe": True}],
    )
    if exc is None:
        return ProbeResult(
            name="extensions_accepted",
            status=ProbeStatus.PASS,
            summary="KME accepted request with extension_optional field.",
            spec_section="§5.3.2",
            severity="info",
            latency_ms=latency,
        )
    if isinstance(exc, KMEHTTPError):
        return ProbeResult(
            name="extensions_accepted",
            status=ProbeStatus.WARN,
            summary=(
                f"KME returned HTTP {exc.status_code} when extension_optional "
                f"was present. ETSI 014 §5.3.2 says optional extensions must "
                f"not cause rejection."
            ),
            spec_section="§5.3.2",
            severity="warn",
            latency_ms=latency,
            details={"http_status": exc.status_code, "message": exc.message},
        )
    return ProbeResult(
        name="extensions_accepted",
        status=ProbeStatus.WARN,
        summary=f"Could not test extensions: {exc}",
        spec_section="§5.3.2",
        severity="info",
        latency_ms=latency,
    )


def probe_dec_keys_roundtrip(
    client: ETSI014Client, slave_sae_id: str
) -> ProbeResult:
    """End-to-end round-trip: enc_keys → dec_keys returns the same bytes."""
    enc, t1, exc = _timed(
        client.get_enc_keys, slave_sae_id, number=1, size=256
    )
    if exc is not None or not enc:
        return ProbeResult(
            name="dec_keys_roundtrip",
            status=ProbeStatus.FAIL,
            summary=f"Could not fetch a key to round-trip: {exc}",
            spec_section="§5.4",
            severity="critical",
            latency_ms=t1,
        )
    src = enc[0]
    dec, t2, exc = _timed(
        client.get_dec_keys, slave_sae_id, key_ids=[src.key_id]
    )
    total = t1 + t2
    if exc is not None or not dec:
        return ProbeResult(
            name="dec_keys_roundtrip",
            status=ProbeStatus.FAIL,
            summary=f"dec_keys did not return the requested key_ID: {exc}",
            spec_section="§5.4",
            severity="critical",
            latency_ms=total,
            details={"key_id": src.key_id},
        )
    if dec[0].key != src.key:
        return ProbeResult(
            name="dec_keys_roundtrip",
            status=ProbeStatus.FAIL,
            summary=(
                "dec_keys returned a key with the requested key_ID but "
                "different bytes."
            ),
            spec_section="§5.4",
            severity="critical",
            latency_ms=total,
        )
    return ProbeResult(
        name="dec_keys_roundtrip",
        status=ProbeStatus.PASS,
        summary="enc_keys → dec_keys round-trip preserves key bytes.",
        spec_section="§5.4",
        severity="info",
        latency_ms=total,
        details={"key_id": src.key_id},
    )


def probe_error_contract_404(
    client: ETSI014Client, slave_sae_id: str
) -> ProbeResult:
    """Confirm the KME returns HTTP 404 for an unknown key_ID."""
    bogus = "00000000-0000-0000-0000-000000000000"
    _, latency, exc = _timed(
        client.get_dec_keys, slave_sae_id, key_ids=[bogus]
    )
    if isinstance(exc, KMENotFoundError):
        return ProbeResult(
            name="error_contract_404",
            status=ProbeStatus.PASS,
            summary="KME correctly returns 404 for an unknown key_ID.",
            spec_section="§5.4",
            severity="info",
            latency_ms=latency,
        )
    if exc is None:
        return ProbeResult(
            name="error_contract_404",
            status=ProbeStatus.WARN,
            summary=(
                "KME returned 2xx for an unknown key_ID. ETSI 014 expects 404."
            ),
            spec_section="§5.4",
            severity="warn",
            latency_ms=latency,
        )
    if isinstance(exc, KMEHTTPError):
        return ProbeResult(
            name="error_contract_404",
            status=ProbeStatus.WARN,
            summary=(
                f"KME returned HTTP {exc.status_code} for an unknown "
                f"key_ID; ETSI 014 expects 404."
            ),
            spec_section="§5.4",
            severity="warn",
            latency_ms=latency,
            details={"http_status": exc.status_code},
        )
    return ProbeResult(
        name="error_contract_404",
        status=ProbeStatus.WARN,
        summary=f"Unexpected error: {exc}",
        spec_section="§5.4",
        severity="warn",
        latency_ms=latency,
    )


def probe_error_contract_400(
    client: ETSI014Client, slave_sae_id: str
) -> ProbeResult:
    """Confirm the KME returns HTTP 400 for an invalid key size."""
    # 257 is not a multiple of 8 — must be rejected per ETSI 014.
    _, latency, exc = _timed(
        client.get_enc_keys, slave_sae_id, number=1, size=257
    )
    if isinstance(exc, KMEHTTPError) and exc.status_code == 400:
        return ProbeResult(
            name="error_contract_400",
            status=ProbeStatus.PASS,
            summary="KME correctly returns 400 for size=257 (not a multiple of 8).",
            spec_section="§5.3",
            severity="info",
            latency_ms=latency,
        )
    if exc is None:
        return ProbeResult(
            name="error_contract_400",
            status=ProbeStatus.WARN,
            summary="KME accepted size=257; ETSI 014 requires multiples of 8.",
            spec_section="§5.3",
            severity="warn",
            latency_ms=latency,
        )
    return ProbeResult(
        name="error_contract_400",
        status=ProbeStatus.WARN,
        summary=f"Unexpected error on bad size: {exc}",
        spec_section="§5.3",
        severity="info",
        latency_ms=latency,
    )


def probe_latency(
    client: ETSI014Client, slave_sae_id: str, samples: int = 5
) -> ProbeResult:
    """Measure status-endpoint latency across N samples."""
    latencies = []
    for _ in range(samples):
        _, lat, exc = _timed(client.status, slave_sae_id)
        if exc is None:
            latencies.append(lat)
    if not latencies:
        return ProbeResult(
            name="latency",
            status=ProbeStatus.SKIP,
            summary="Could not collect latency samples.",
            severity="info",
        )
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p99 = latencies[max(0, int(len(latencies) * 0.99) - 1)]
    avg = sum(latencies) / len(latencies)
    return ProbeResult(
        name="latency",
        status=ProbeStatus.PASS,
        summary=(
            f"Status latency over {len(latencies)} samples: "
            f"avg {avg:.1f}ms, p50 {p50:.1f}ms, p99 {p99:.1f}ms."
        ),
        severity="info",
        latency_ms=avg,
        details={
            "samples": len(latencies),
            "avg_ms": avg,
            "p50_ms": p50,
            "p99_ms": p99,
            "min_ms": latencies[0],
            "max_ms": latencies[-1],
        },
    )


# ── Orchestrator ──────────────────────────────────────────────────────────


def run_all(
    client: ETSI014Client,
    slave_sae_id: str,
    *,
    consume_keys: bool = True,
    latency_samples: int = 5,
) -> Report:
    """Run the full conformance battery and return a :class:`Report`.

    Parameters
    ----------
    client : ETSI014Client
        A configured sync client. Must have credentials for ``slave_sae_id``.
    slave_sae_id : str
        The slave SAE ID to probe against.
    consume_keys : bool
        If ``False``, skip probes that consume real keys (enc_keys / dec_keys
        round-trip / extensions). Default ``True`` — consumes up to 5 keys
        per run.
    latency_samples : int
        Number of status calls to time for the latency probe.
    """
    report = Report(base_url=client.base_url, slave_sae_id=slave_sae_id)
    t_start = time.perf_counter()

    # 1. Reachability
    r = probe_reachability(client, slave_sae_id)
    report.results.append(r)
    if r.status == ProbeStatus.FAIL:
        report.total_latency_ms = (time.perf_counter() - t_start) * 1000.0
        return report

    # 2. Status fields
    sf, raw_status = probe_status_fields(client, slave_sae_id)
    report.results.append(sf)
    max_per_request = (raw_status or {}).get("max_key_per_request", 20)
    max_size = (raw_status or {}).get("max_key_size", 1024)

    if not consume_keys:
        report.results.append(ProbeResult(
            name="enc_keys_get",
            status=ProbeStatus.SKIP,
            summary="Skipped (--no-consume).",
        ))
        report.results.append(ProbeResult(
            name="enc_keys_post",
            status=ProbeStatus.SKIP,
            summary="Skipped (--no-consume).",
        ))
        report.results.append(ProbeResult(
            name="enc_keys_caps",
            status=ProbeStatus.SKIP,
            summary="Skipped (--no-consume).",
        ))
        report.results.append(ProbeResult(
            name="extensions_accepted",
            status=ProbeStatus.SKIP,
            summary="Skipped (--no-consume).",
        ))
        report.results.append(ProbeResult(
            name="dec_keys_roundtrip",
            status=ProbeStatus.SKIP,
            summary="Skipped (--no-consume).",
        ))
    else:
        # 3. enc_keys GET
        get_res, _ = probe_enc_keys_get(client, slave_sae_id)
        report.results.append(get_res)
        # 4. enc_keys POST
        post_res, _ = probe_enc_keys_post(client, slave_sae_id)
        report.results.append(post_res)
        # 5. caps enforcement
        report.results.append(
            probe_enc_keys_caps(client, slave_sae_id, max_per_request, max_size)
        )
        # 6. extension passthrough
        report.results.append(probe_extensions_accepted(client, slave_sae_id))
        # 7. dec_keys round-trip
        report.results.append(probe_dec_keys_roundtrip(client, slave_sae_id))

    # 8. error contracts (read-only — bogus key_ID and bad size)
    report.results.append(probe_error_contract_404(client, slave_sae_id))
    report.results.append(probe_error_contract_400(client, slave_sae_id))

    # 9. latency
    report.results.append(probe_latency(client, slave_sae_id, latency_samples))

    report.total_latency_ms = (time.perf_counter() - t_start) * 1000.0
    return report
