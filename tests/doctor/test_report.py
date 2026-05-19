"""Tests for the report formatters."""

import json

from qkdsec.doctor import (
    ProbeResult,
    ProbeStatus,
    Report,
    format_html,
    format_json,
    format_text,
)


def _sample_report() -> Report:
    r = Report(base_url="https://kme.test", slave_sae_id="sae-bob", total_latency_ms=123.4)
    r.results = [
        ProbeResult(
            name="reachability", status=ProbeStatus.PASS,
            summary="OK", spec_section="§5.2", latency_ms=45.2,
        ),
        ProbeResult(
            name="extensions_accepted", status=ProbeStatus.WARN,
            summary="KME returned 400 with extensions",
            spec_section="§5.3.2", latency_ms=30.0,
        ),
        ProbeResult(
            name="latency", status=ProbeStatus.PASS, summary="avg 12ms",
            details={"avg_ms": 12.0, "p99_ms": 18.5},
        ),
    ]
    return r


def test_format_json_is_valid_json():
    out = format_json(_sample_report())
    data = json.loads(out)
    assert data["base_url"] == "https://kme.test"
    assert data["counts"]["pass"] == 2
    assert data["counts"]["warn"] == 1
    assert data["passed"] is True
    assert len(data["results"]) == 3


def test_format_text_plain_contains_key_info():
    out = format_text(_sample_report(), use_rich=False)
    assert "qkdsec doctor" in out
    assert "https://kme.test" in out
    assert "PASS" in out and "WARN" in out
    assert "CONFORMANT" in out


def test_format_text_rich_does_not_crash():
    # Just verify it runs and produces non-empty output
    out = format_text(_sample_report(), use_rich=True)
    assert len(out) > 100


def test_format_html_is_self_contained():
    out = format_html(_sample_report())
    assert out.startswith("<!DOCTYPE html>")
    assert "</html>" in out.rstrip()
    assert "https://kme.test" in out
    assert "CONFORMANT" in out
    # No external resource references
    assert "http://" not in out.replace("http://www.w3.org", "")  # allow xmlns


def test_failed_report_marked_non_conformant():
    r = _sample_report()
    r.results.append(
        ProbeResult(name="enc_keys_get", status=ProbeStatus.FAIL, summary="boom")
    )
    assert not r.passed
    assert "NON-CONFORMANT" in format_text(r, use_rich=False)
    assert "NON-CONFORMANT" in format_html(r)
