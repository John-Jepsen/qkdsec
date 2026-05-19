"""Top-level ``qkdsec`` command-line interface.

Requires the ``cli`` (or ``doctor``) extra: ``pip install qkdsec[cli]``.

Subcommands::

    qkdsec doctor <base_url> [--slave-sae-id SAE] [--cert PATH] [--key PATH]
        [--ca-cert PATH] [--format text|json|html] [--output FILE]
        [--no-consume] [--samples N]

    qkdsec status <base_url> <slave_sae_id> [--cert ...] [--key ...] [--ca-cert ...]

    qkdsec keys get <base_url> <slave_sae_id>
        [--number N] [--size S] [--cert ...] [--key ...] [--ca-cert ...]

    qkdsec keys retrieve <base_url> <slave_sae_id> <key_id>...
        [--cert ...] [--key ...] [--ca-cert ...]

    qkdsec version
"""

import json
import sys
from pathlib import Path
from typing import Optional

try:
    import typer
    from rich.console import Console
except ImportError as e:
    raise ImportError(
        "qkdsec CLI requires extra dependencies. "
        "Install with: pip install qkdsec[cli]"
    ) from e

from . import __version__
from .client import ETSI014Client
from .client.errors import KMEError

app = typer.Typer(
    name="qkdsec",
    help="ETSI GS QKD 014 toolkit — KME probe, status, and key fetch.",
    no_args_is_help=True,
    add_completion=False,
)
keys_app = typer.Typer(
    help="Fetch keys from a KME (enc_keys / dec_keys).",
    no_args_is_help=True,
)
app.add_typer(keys_app, name="keys")

console = Console()
err_console = Console(stderr=True)


# ── Shared options ────────────────────────────────────────────────────────


def _build_client(
    base_url: str,
    cert: Optional[Path],
    key: Optional[Path],
    ca_cert: Optional[Path],
    insecure: bool,
    timeout: float,
) -> ETSI014Client:
    if insecure:
        verify: bool | str = False
    elif ca_cert is not None:
        verify = str(ca_cert)
    else:
        verify = True

    client_cert: str | tuple[str, str] | None
    if cert and key:
        client_cert = (str(cert), str(key))
    elif cert:
        client_cert = str(cert)
    else:
        client_cert = None

    return ETSI014Client(
        base_url,
        client_cert=client_cert,
        verify=verify,
        timeout=timeout,
    )


# ── doctor ────────────────────────────────────────────────────────────────


@app.command(help="Probe a KME for ETSI GS QKD 014 conformance.")
def doctor(
    base_url: str = typer.Argument(..., help="KME base URL (e.g., https://kme.example.com)."),
    slave_sae_id: str = typer.Option(
        "sae-bob", "--slave-sae-id", "-s",
        help="The slave SAE ID to probe against.",
    ),
    cert: Optional[Path] = typer.Option(
        None, "--cert", help="Client certificate (PEM)."),
    key: Optional[Path] = typer.Option(
        None, "--key", help="Client private key (PEM)."),
    ca_cert: Optional[Path] = typer.Option(
        None, "--ca-cert", help="Path to CA certificate for TLS verification."),
    insecure: bool = typer.Option(
        False, "--insecure", help="Disable TLS verification (NOT for production)."),
    fmt: str = typer.Option(
        "text", "--format", "-f",
        help="Output format: text, json, html.",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write report to file instead of stdout."),
    no_consume: bool = typer.Option(
        False, "--no-consume",
        help="Skip probes that consume real keys.",
    ),
    samples: int = typer.Option(
        5, "--samples", help="Latency probe sample count."),
    timeout: float = typer.Option(
        30.0, "--timeout", help="Per-request HTTP timeout in seconds."),
) -> None:
    from .doctor import format_html, format_json, format_text, run_all

    if fmt not in ("text", "json", "html"):
        err_console.print(f"[red]Invalid format: {fmt}[/]")
        raise typer.Exit(2)

    client = _build_client(base_url, cert, key, ca_cert, insecure, timeout)
    try:
        report = run_all(
            client,
            slave_sae_id=slave_sae_id,
            consume_keys=not no_consume,
            latency_samples=samples,
        )
    finally:
        client.close()

    if fmt == "text":
        rendered = format_text(report)
    elif fmt == "json":
        rendered = format_json(report)
    else:
        rendered = format_html(report)

    if output:
        output.write_text(rendered)
        err_console.print(f"[dim]Report written to {output}[/]")
    else:
        # For text format we already have terminal control codes; print raw.
        # For json/html, write plainly via sys.stdout.
        if fmt == "text":
            sys.stdout.write(rendered)
            if not rendered.endswith("\n"):
                sys.stdout.write("\n")
        else:
            print(rendered)

    raise typer.Exit(0 if report.passed else 1)


# ── status ────────────────────────────────────────────────────────────────


@app.command(help="Fetch KME status for a slave SAE.")
def status(
    base_url: str = typer.Argument(...),
    slave_sae_id: str = typer.Argument(...),
    cert: Optional[Path] = typer.Option(None, "--cert"),
    key: Optional[Path] = typer.Option(None, "--key"),
    ca_cert: Optional[Path] = typer.Option(None, "--ca-cert"),
    insecure: bool = typer.Option(False, "--insecure"),
    timeout: float = typer.Option(30.0, "--timeout"),
    as_json: bool = typer.Option(False, "--json", help="Emit raw JSON."),
) -> None:
    client = _build_client(base_url, cert, key, ca_cert, insecure, timeout)
    try:
        s = client.status(slave_sae_id)
    except KMEError as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)
    finally:
        client.close()

    payload = {
        "source_kme_id": s.source_kme_id,
        "target_kme_id": s.target_kme_id,
        "master_sae_id": s.master_sae_id,
        "slave_sae_id": s.slave_sae_id,
        "key_size": s.key_size,
        "stored_key_count": s.stored_key_count,
        "max_key_count": s.max_key_count,
        "max_key_per_request": s.max_key_per_request,
        "max_key_size": s.max_key_size,
        "min_key_size": s.min_key_size,
        "max_sae_id_count": s.max_sae_id_count,
        "status_extension": s.status_extension,
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        for k, v in payload.items():
            console.print(f"  [bold]{k}[/]: {v}")


# ── keys get / retrieve ───────────────────────────────────────────────────


@keys_app.command("get", help="Master SAE: fetch fresh keys via enc_keys.")
def keys_get(
    base_url: str = typer.Argument(...),
    slave_sae_id: str = typer.Argument(...),
    number: int = typer.Option(1, "--number", "-n"),
    size: int = typer.Option(256, "--size"),
    method: str = typer.Option("GET", "--method"),
    cert: Optional[Path] = typer.Option(None, "--cert"),
    key: Optional[Path] = typer.Option(None, "--key"),
    ca_cert: Optional[Path] = typer.Option(None, "--ca-cert"),
    insecure: bool = typer.Option(False, "--insecure"),
    timeout: float = typer.Option(30.0, "--timeout"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    client = _build_client(base_url, cert, key, ca_cert, insecure, timeout)
    try:
        keys = client.get_enc_keys(
            slave_sae_id, number=number, size=size, method=method.upper()
        )
    except KMEError as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)
    finally:
        client.close()

    if as_json:
        print(json.dumps(
            [{"key_id": k.key_id, "key_hex": k.key.hex(), "size_bits": k.size_bits}
             for k in keys],
            indent=2,
        ))
    else:
        for k in keys:
            console.print(f"  [cyan]{k.key_id}[/]  {k.key.hex()}  ({k.size_bits}b)")


@keys_app.command("retrieve", help="Slave SAE: retrieve keys by key_ID via dec_keys.")
def keys_retrieve(
    base_url: str = typer.Argument(...),
    slave_sae_id: str = typer.Argument(...),
    key_ids: list[str] = typer.Argument(..., help="One or more key_IDs."),
    cert: Optional[Path] = typer.Option(None, "--cert"),
    key: Optional[Path] = typer.Option(None, "--key"),
    ca_cert: Optional[Path] = typer.Option(None, "--ca-cert"),
    insecure: bool = typer.Option(False, "--insecure"),
    timeout: float = typer.Option(30.0, "--timeout"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    client = _build_client(base_url, cert, key, ca_cert, insecure, timeout)
    try:
        keys = client.get_dec_keys(slave_sae_id, key_ids=key_ids)
    except KMEError as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)
    finally:
        client.close()

    if as_json:
        print(json.dumps(
            [{"key_id": k.key_id, "key_hex": k.key.hex(), "size_bits": k.size_bits}
             for k in keys],
            indent=2,
        ))
    else:
        for k in keys:
            console.print(f"  [cyan]{k.key_id}[/]  {k.key.hex()}  ({k.size_bits}b)")


# ── version ───────────────────────────────────────────────────────────────


@app.command(help="Print the qkdsec version.")
def version() -> None:
    print(__version__)


if __name__ == "__main__":
    app()
