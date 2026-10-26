"""Passkey (WebAuthn) sign-in for the single EmailApp user, next to the existing password login.

- Sign-in uses discoverable credentials, so no username is typed.
- A passkey can only be added by someone already signed in (password or passkey).
- User verification (Face ID / Touch ID / PIN) is required. Challenges are single use and expire after 5 minutes.
- Challenges live in the signed Flask session, so this works across Gunicorn workers.
- Passkeys are disabled unless PASSKEY_ORIGINS lists the exact https origin(s) the app is served from.
"""
import os
import secrets
import sqlite3
import time
from contextlib import closing
from urllib.parse import urlsplit

from flask import Blueprint, abort, jsonify, request, session
from werkzeug.exceptions import HTTPException
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from email_app.config import MY_USER
from email_app.services.rules import login_required

CHALLENGE_TTL = 300
MAX_PASSKEYS = 10
DB_PATH = os.environ.get("PASSKEY_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "passkeys.db"))
ALLOWED_ORIGINS = {o.strip().rstrip("/") for o in os.environ.get("PASSKEY_ORIGINS", "").split(",") if o.strip()}

bp = Blueprint("passkeys", __name__)


@bp.errorhandler(HTTPException)
def _json_error(exc):
    return jsonify(error=exc.description), exc.code


def _db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS passkeys (credential_id TEXT PRIMARY KEY, public_key BLOB NOT NULL, "
        "sign_count INTEGER NOT NULL, label TEXT NOT NULL, created_at INTEGER NOT NULL, last_used INTEGER)"
    )
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value BLOB NOT NULL)")
    return conn


def _user_handle(conn):
    row = conn.execute("SELECT value FROM meta WHERE key='user_handle'").fetchone()
    if row:
        return bytes(row["value"])
    handle = secrets.token_bytes(16)
    conn.execute("INSERT INTO meta (key, value) VALUES ('user_handle', ?)", (handle,))
    conn.commit()
    return handle


def passkeys_enabled():
    return bool(ALLOWED_ORIGINS)


def has_passkey():
    if not passkeys_enabled():
        return False
    with closing(_db()) as conn:
        return conn.execute("SELECT 1 FROM passkeys LIMIT 1").fetchone() is not None


def _site():
    """(RP ID, origin) of the allow-listed origin this request came from."""
    parts = urlsplit(request.headers.get("Origin") or "")
    origin = f"{parts.scheme}://{parts.netloc}"
    if not passkeys_enabled() or origin not in ALLOWED_ORIGINS or not parts.hostname:
        abort(403)
    return parts.hostname, origin


def _issue(purpose, options, **extra):
    session["wa"] = {"c": bytes_to_base64url(options.challenge), "p": purpose, "e": time.time() + CHALLENGE_TTL, **extra}
    return options_to_json(options), 200, {"Content-Type": "application/json"}


def _take(purpose):
    """Single use: the challenge is removed from the session the moment it is looked up."""
    entry = session.pop("wa", None)
    if not entry or entry["p"] != purpose or entry["e"] < time.time():
        abort(400, "That attempt expired. Try again.")
    return base64url_to_bytes(entry["c"]), entry


@bp.post("/passkey/login/options")
def login_options():
    rp_id, _ = _site()
    options = generate_authentication_options(rp_id=rp_id, user_verification=UserVerificationRequirement.REQUIRED)
    return _issue("login", options)


@bp.post("/passkey/login/verify")
def login_verify():
    body = request.get_json(silent=True) or {}
    rp_id, origin = _site()
    challenge, _ = _take("login")
    try:
        credential = body["credential"]
        with closing(_db()) as conn:
            row = conn.execute("SELECT * FROM passkeys WHERE credential_id=?", (credential["id"],)).fetchone()
            if not row:
                raise ValueError("unknown credential")
            handle = (credential.get("response") or {}).get("userHandle")
            if handle and base64url_to_bytes(handle) != _user_handle(conn):
                raise ValueError("user handle mismatch")
            verified = verify_authentication_response(
                credential=credential,
                expected_challenge=challenge,
                expected_rp_id=rp_id,
                expected_origin=origin,
                credential_public_key=bytes(row["public_key"]),
                credential_current_sign_count=row["sign_count"],
                require_user_verification=True,
            )
            conn.execute(
                "UPDATE passkeys SET sign_count=?, last_used=? WHERE credential_id=?",
                (verified.new_sign_count, int(time.time()), row["credential_id"]),
            )
            conn.commit()
    except Exception:
        time.sleep(0.8)
        return jsonify(error="Passkey sign-in failed"), 401
    session.clear()
    session["user"] = MY_USER
    # Without "remember me" the cookie expires when the browser closes.
    session.permanent = bool(body.get("remember"))
    return jsonify(ok=True)


@bp.get("/passkeys")
@login_required
def list_passkeys():
    with closing(_db()) as conn:
        rows = conn.execute(
            "SELECT credential_id, label, created_at, last_used FROM passkeys ORDER BY created_at"
        ).fetchall()
    return jsonify(enabled=passkeys_enabled(), max=MAX_PASSKEYS, passkeys=[dict(r) for r in rows])


@bp.post("/passkeys/options")
@login_required
def register_options():
    rp_id, _ = _site()
    with closing(_db()) as conn:
        ids = [r["credential_id"] for r in conn.execute("SELECT credential_id FROM passkeys")]
        if len(ids) >= MAX_PASSKEYS:
            abort(409, f"At most {MAX_PASSKEYS} passkeys. Remove one first.")
        handle = _user_handle(conn)
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name="Email Routing",
        user_id=handle,
        user_name=MY_USER,
        user_display_name=MY_USER,
        exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(i)) for i in ids],
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )
    return _issue("register", options)


@bp.post("/passkeys/verify")
@login_required
def register_verify():
    body = request.get_json(silent=True) or {}
    rp_id, origin = _site()
    challenge, _ = _take("register")
    try:
        verified = verify_registration_response(
            credential=body["credential"],
            expected_challenge=challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
            require_user_verification=True,
        )
    except Exception as exc:
        abort(400, f"The passkey could not be verified ({type(exc).__name__}).")
    label = (str(body.get("label") or "").strip() or "This device")[:60]
    with closing(_db()) as conn:
        if conn.execute("SELECT COUNT(*) n FROM passkeys").fetchone()["n"] >= MAX_PASSKEYS:
            abort(409, f"At most {MAX_PASSKEYS} passkeys. Remove one first.")
        conn.execute(
            "INSERT INTO passkeys (credential_id, public_key, sign_count, label, created_at) VALUES (?,?,?,?,?)",
            (bytes_to_base64url(verified.credential_id), verified.credential_public_key, verified.sign_count, label, int(time.time())),
        )
        conn.commit()
    return jsonify(ok=True)


@bp.delete("/passkeys/<credential_id>")
@login_required
def delete_passkey(credential_id):
    with closing(_db()) as conn:
        removed = conn.execute("DELETE FROM passkeys WHERE credential_id=?", (credential_id,)).rowcount
        conn.commit()
    if not removed:
        abort(404)
    return jsonify(ok=True)
