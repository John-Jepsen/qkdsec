"""Formatters for doctor reports — text, JSON, and HTML."""

import datetime as _dt
import html
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .probes import ProbeResult, Report

_STATUS_GLYPH = {
    "pass": "PASS",
    "warn": "WARN",
    "fail": "FAIL",
    "skip": "SKIP",
}

_STATUS_COLOR = {
    "pass": "green",
    "warn": "yellow",
    "fail": "red",
    "skip": "dim",
}


# ── JSON ──────────────────────────────────────────────────────────────────


def format_json(report: "Report", *, indent: int = 2) -> str:
    """Serialize the report as JSON. Stable field ordering for diffing."""
    return json.dumps(report.to_dict(), indent=indent, sort_keys=False)


# ── Text ──────────────────────────────────────────────────────────────────


def format_text(report: "Report", *, use_rich: bool = True) -> str:
    """Format the report as terminal text. Uses Rich if available.

    Set ``use_rich=False`` to force plain ASCII output (useful for log files).
    """
    if use_rich:
        try:
            return _format_text_rich(report)
        except ImportError:
            pass
    return _format_text_plain(report)


def _format_text_plain(report: "Report") -> str:
    lines = []
    lines.append("=" * 72)
    lines.append(f"qkdsec doctor — {report.base_url}")
    lines.append(f"slave SAE: {report.slave_sae_id}")
    lines.append("=" * 72)

    for r in report.results:
        glyph = _STATUS_GLYPH[r.status.value]
        section = f" [{r.spec_section}]" if r.spec_section else ""
        latency = f"  ({r.latency_ms:.0f}ms)" if r.latency_ms is not None else ""
        lines.append(f"  {glyph}  {r.name}{section}{latency}")
        lines.append(f"        {r.summary}")
        if r.details:
            for k, v in r.details.items():
                lines.append(f"        - {k}: {v}")

    counts = report.counts
    lines.append("-" * 72)
    lines.append(
        f"  Summary: {counts['pass']} pass, {counts['warn']} warn, "
        f"{counts['fail']} fail, {counts['skip']} skip"
    )
    lines.append(
        f"  Verdict: {'CONFORMANT' if report.passed else 'NON-CONFORMANT'}  "
        f"({report.total_latency_ms:.0f}ms total)"
    )
    lines.append("=" * 72)
    return "\n".join(lines)


def _format_text_rich(report: "Report") -> str:
    from io import StringIO

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=100)

    header = (
        f"[bold]qkdsec doctor[/]   {report.base_url}\n"
        f"slave SAE: [cyan]{report.slave_sae_id}[/]"
    )
    console.print(Panel(header, expand=False))

    table = Table(show_header=True, header_style="bold")
    table.add_column("Status", width=7)
    table.add_column("Probe", min_width=22)
    table.add_column("Spec", width=10)
    table.add_column("Latency", width=10, justify="right")
    table.add_column("Summary", overflow="fold")

    for r in report.results:
        sval = r.status.value
        status_text = f"[{_STATUS_COLOR[sval]}]{_STATUS_GLYPH[sval]}[/]"
        latency = f"{r.latency_ms:.0f} ms" if r.latency_ms is not None else "—"
        table.add_row(
            status_text,
            r.name,
            r.spec_section or "—",
            latency,
            r.summary,
        )
    console.print(table)

    counts = report.counts
    summary = (
        f"[green]{counts['pass']} pass[/]   "
        f"[yellow]{counts['warn']} warn[/]   "
        f"[red]{counts['fail']} fail[/]   "
        f"[dim]{counts['skip']} skip[/]"
    )
    verdict_style = "green" if report.passed else "red"
    verdict_text = "CONFORMANT" if report.passed else "NON-CONFORMANT"
    console.print(
        Panel(
            f"{summary}\n\n"
            f"[bold {verdict_style}]{verdict_text}[/]   "
            f"({report.total_latency_ms:.0f} ms total)",
            expand=False,
        )
    )
    return buf.getvalue()


# ── HTML ──────────────────────────────────────────────────────────────────


_HTML_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       max-width: 960px; margin: 2rem auto; padding: 0 1rem; color: #222; }
h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
.meta { color: #666; font-size: 0.9rem; margin-bottom: 1.5rem; }
.summary { display: flex; gap: 1.5rem; margin: 1rem 0; font-weight: 600; }
.summary span { padding: 0.25rem 0.75rem; border-radius: 4px; }
.s-pass { background: #d4f1d4; color: #1d6b1d; }
.s-warn { background: #fff3cd; color: #856404; }
.s-fail { background: #f8d7da; color: #721c24; }
.s-skip { background: #e9ecef; color: #6c757d; }
.verdict { font-size: 1.2rem; font-weight: 700; padding: 0.5rem 1rem;
           border-radius: 6px; display: inline-block; margin: 1rem 0; }
.v-pass { background: #28a745; color: white; }
.v-fail { background: #dc3545; color: white; }
table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
th, td { text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid #eee;
         vertical-align: top; }
th { background: #f8f9fa; font-weight: 600; }
.status { font-weight: 700; font-size: 0.8rem; letter-spacing: 0.05em; }
.status.pass { color: #1d6b1d; }
.status.warn { color: #856404; }
.status.fail { color: #721c24; }
.status.skip { color: #6c757d; }
.details { color: #555; font-size: 0.85rem; font-family: monospace;
           margin-top: 0.25rem; }
.footer { color: #999; font-size: 0.8rem; margin-top: 2rem; text-align: center; }
"""


def format_html(report: "Report") -> str:
    """Render the report as a standalone single-file HTML document."""
    counts = report.counts
    verdict_class = "v-pass" if report.passed else "v-fail"
    verdict_text = "CONFORMANT" if report.passed else "NON-CONFORMANT"
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    rows = []
    for r in report.results:
        latency = f"{r.latency_ms:.0f} ms" if r.latency_ms is not None else "—"
        details_html = ""
        if r.details:
            items = "".join(
                f"<div>{html.escape(k)}: {html.escape(str(v))}</div>"
                for k, v in r.details.items()
            )
            details_html = f'<div class="details">{items}</div>'
        rows.append(
            f"""
            <tr>
              <td><span class="status {r.status.value}">{_STATUS_GLYPH[r.status.value]}</span></td>
              <td><strong>{html.escape(r.name)}</strong></td>
              <td>{html.escape(r.spec_section or "—")}</td>
              <td>{latency}</td>
              <td>{html.escape(r.summary)}{details_html}</td>
            </tr>
            """
        )
    rows_html = "\n".join(rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>qkdsec doctor — {html.escape(report.base_url)}</title>
  <style>{_HTML_CSS}</style>
</head>
<body>
  <h1>qkdsec doctor report</h1>
  <div class="meta">
    KME: <code>{html.escape(report.base_url)}</code><br>
    Slave SAE: <code>{html.escape(report.slave_sae_id)}</code><br>
    Generated: {now}
  </div>

  <div class="summary">
    <span class="s-pass">{counts['pass']} pass</span>
    <span class="s-warn">{counts['warn']} warn</span>
    <span class="s-fail">{counts['fail']} fail</span>
    <span class="s-skip">{counts['skip']} skip</span>
  </div>

  <div class="verdict {verdict_class}">{verdict_text}</div>

  <table>
    <thead>
      <tr>
        <th>Status</th>
        <th>Probe</th>
        <th>Spec</th>
        <th>Latency</th>
        <th>Summary</th>
      </tr>
    </thead>
    <tbody>
{rows_html}
    </tbody>
  </table>

  <div class="footer">
    Generated by qkdsec — ETSI GS QKD 014 v1.1.1 conformance probe
  </div>
</body>
</html>
"""
