"""
Flask implementation of the ETSI GS QKD 014 v1.1.1 mock KME server.

Matches John's kme_server.py style: Flask, plain request.get_json(),
abort() for errors, jsonify() for responses.
"""

from __future__ import annotations

from flask import Flask, abort, jsonify, request

from ._pool import (
    DEFAULT_KEY_SIZE,
    MAX_KEY_SIZE,
    MAX_KEYS_PER_REQUEST,
    MIN_KEY_SIZE,
    POOL_TARGET,
    KeyPool,
    key_to_dict,
)

KME_ID         = "mock-kme-source"
PARTNER_KME_ID = "mock-kme-target"


def create_app(pool: KeyPool | None = None) -> Flask:
    """
    Create and return the Flask app.

    Accepts an optional pre-built KeyPool so tests can inject one.
    If none is provided, creates one with the classical backend.
    """
    if pool is None:
        pool = KeyPool(backend="classical")

    app = Flask(__name__)

    # ── §5.2 Status ───────────────────────────────────────────────────────

    @app.get("/api/v1/keys/<slave_sae_id>/status")
    def route_status(slave_sae_id: str):
        return jsonify({
            "source_KME_ID":      KME_ID,
            "target_KME_ID":      PARTNER_KME_ID,
            "master_SAE_ID":      "unknown",
            "slave_SAE_ID":       slave_sae_id,
            "key_size":           DEFAULT_KEY_SIZE,
            "stored_key_count":   pool.available_count,
            "max_key_count":      POOL_TARGET,
            "max_key_per_request": MAX_KEYS_PER_REQUEST,
            "max_key_size":       MAX_KEY_SIZE,
            "min_key_size":       MIN_KEY_SIZE,
            "max_SAE_ID_count":   0,
        })

    # ── §5.3 enc_keys GET ─────────────────────────────────────────────────

    @app.get("/api/v1/keys/<slave_sae_id>/enc_keys")
    def route_enc_keys_get(slave_sae_id: str):
        number = _int_param("number", 1, 1, MAX_KEYS_PER_REQUEST)
        size   = _int_param("size", DEFAULT_KEY_SIZE, MIN_KEY_SIZE, MAX_KEY_SIZE)
        if size % 8 != 0:
            abort(400, description="size must be a multiple of 8 bits")
        keys = pool.get_keys(number, size)
        return jsonify({"keys": [key_to_dict(k) for k in keys]})

    # ── §5.3 enc_keys POST ────────────────────────────────────────────────

    @app.post("/api/v1/keys/<slave_sae_id>/enc_keys")
    def route_enc_keys_post(slave_sae_id: str):
        body   = request.get_json(silent=True) or {}
        number = _int_field(body, "number", 1, 1, MAX_KEYS_PER_REQUEST)
        size   = _int_field(body, "size", DEFAULT_KEY_SIZE, MIN_KEY_SIZE, MAX_KEY_SIZE)
        if size % 8 != 0:
            abort(400, description="size must be a multiple of 8 bits")
        keys = pool.get_keys(number, size)
        return jsonify({"keys": [key_to_dict(k) for k in keys]})

    # ── §5.4 dec_keys ─────────────────────────────────────────────────────

    @app.post("/api/v1/keys/<slave_sae_id>/dec_keys")
    def route_dec_keys(slave_sae_id: str):
        body    = request.get_json(silent=True) or {}
        raw_ids = body.get("key_IDs", [])
        if not raw_ids:
            abort(400, description="Request body must include 'key_IDs'")
        if len(raw_ids) > MAX_KEYS_PER_REQUEST:
            abort(400, description=f"Too many key IDs (max {MAX_KEYS_PER_REQUEST})")

        key_ids = [
            item["key_ID"] for item in raw_ids
            if isinstance(item, dict) and "key_ID" in item
        ]
        if not key_ids:
            abort(400, description="'key_IDs' entries must be objects with a 'key_ID' field")
        found, missing = pool.get_by_ids(key_ids)
        if missing:
            abort(404, description=(
                "Keys not found (may not exist or already retrieved): "
                + ", ".join(missing)
            ))
        return jsonify({"keys": [key_to_dict(k) for k in found]})

    # ── Error handlers ────────────────────────────────────────────────────

    @app.errorhandler(400)
    @app.errorhandler(404)
    def handle_error(e):
        return jsonify({"message": str(e.description)}), e.code

    return app


# ── Query param helper ────────────────────────────────────────────────────

def _int_param(name: str, default: int, lo: int, hi: int) -> int:
    """Parse and validate an integer query parameter."""
    raw = request.args.get(name, str(default))
    try:
        val = int(raw)
    except ValueError:
        abort(400, description=f"'{name}' must be an integer")
    if not lo <= val <= hi:
        abort(400, description=f"'{name}' must be between {lo} and {hi}")
    return val


def _int_field(body: dict, name: str, default: int, lo: int, hi: int) -> int:
    """Parse and validate an integer field from a JSON body."""
    raw = body.get(name, default)
    if isinstance(raw, bool) or not isinstance(raw, int):
        try:
            raw = int(raw)
        except (TypeError, ValueError):
            abort(400, description=f"'{name}' must be an integer")
    if not lo <= raw <= hi:
        abort(400, description=f"'{name}' must be between {lo} and {hi}")
    return raw