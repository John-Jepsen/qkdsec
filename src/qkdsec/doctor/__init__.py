"""KME conformance probe.

The ``qkdsec.doctor`` package runs a battery of probes against a Key
Management Entity (KME) and emits a conformance report against ETSI GS QKD
014 v1.1.1. It is the recommended first tool to point at any new KME, whether
it is hardware, a vendor simulator, or your own implementation.

Programmatic example::

    from qkdsec.client import ETSI014Client
    from qkdsec.doctor import run_all, format_text

    client = ETSI014Client("https://kme.example.com",
                           client_cert=("alice.crt", "alice.key"))
    report = run_all(client, slave_sae_id="sae-bob")
    print(format_text(report))

Or use the CLI::

    qkdsec doctor https://kme.example.com --slave-sae-id sae-bob

For full options see :doc:`/guides/doctor`.
"""

from .probes import (
    ProbeResult,
    ProbeStatus,
    Report,
    run_all,
)
from .report import format_html, format_json, format_text

__all__ = [
    "ProbeResult",
    "ProbeStatus",
    "Report",
    "run_all",
    "format_text",
    "format_json",
    "format_html",
]
