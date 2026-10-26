import hashlib
import importlib
import json
import os
import re
import struct

import bcrypt
import cbor2
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url

ORIGIN = "https://mail.example.test"
RP_ID = "mail.example.test"


class SoftAuthenticator:
    """Minimal software authenticator: 'none' attestation, ES256, user verified."""

    def __init__(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.cred_id = os.urandom(16)
        self.user_handle = None
        self.counter = 0

    def _client_data(self, kind, challenge, origin):
        return json.dumps({"type": kind, "challenge": challenge, "origin": origin}).encode()

    def register(self, options, origin=ORIGIN):
        self.user_handle = base64url_to_bytes(options["user"]["id"])
        nums = self.key.public_key().public_numbers()
        cose = cbor2.dumps({1: 2, 3: -7, -1: 1, -2: nums.x.to_bytes(32, "big"), -3: nums.y.to_bytes(32, "big")})
        auth_data = (
            hashlib.sha256(RP_ID.encode()).digest() + bytes([0x45]) + struct.pack(">I", 0)
            + bytes(16) + struct.pack(">H", len(self.cred_id)) + self.cred_id + cose
        )
        client = self._client_data("webauthn.create", options["challenge"], origin)
        return {
            "id": bytes_to_base64url(self.cred_id),
            "rawId": bytes_to_base64url(self.cred_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": bytes_to_base64url(client),
                "attestationObject": bytes_to_base64url(
                    cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})
                ),
            },
            "clientExtensionResults": {},
        }

    def assert_(self, options, origin=ORIGIN):
        self.counter += 1
        auth_data = hashlib.sha256(RP_ID.encode()).digest() + bytes([0x05]) + struct.pack(">I", self.counter)
        client = self._client_data("webauthn.get", options["challenge"], origin)
        signature = self.key.sign(auth_data + hashlib.sha256(client).digest(), ec.ECDSA(hashes.SHA256()))
        return {
            "id": bytes_to_base64url(self.cred_id),
            "rawId": bytes_to_base64url(self.cred_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": bytes_to_base64url(client),
                "authenticatorData": bytes_to_base64url(auth_data),
                "signature": bytes_to_base64url(signature),
                "userHandle": bytes_to_base64url(self.user_handle),
            },
            "clientExtensionResults": {},
        }


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("MY_USER", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", bcrypt.hashpw(b"correct password", bcrypt.gensalt()).decode())
    monkeypatch.setenv("EMAIL_LIST", "admin@example.test")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    monkeypatch.setenv("PASSKEY_ORIGINS", ORIGIN)
    monkeypatch.setenv("PASSKEY_DB_PATH", str(tmp_path / "passkeys.db"))
    import app
    import email_app.config as constants
    import email_app.passkeys as passkeys

    importlib.reload(constants)
    importlib.reload(passkeys)
    application = importlib.reload(app).app
    application.config.update(TESTING=True, WTF_CSRF_TIME_LIMIT=None)
    importlib.import_module("app").limiter.enabled = False
    return application.test_client()


def csrf(client):
    page = client.get("/login").data
    return re.search(rb'name="csrf-token" content="([^"]+)"', page).group(1).decode()


def post(client, url, token, payload=None, origin=ORIGIN, method="post"):
    return getattr(client, method)(
        url, json=payload, headers={"X-CSRFToken": token, "Origin": origin} if origin else {"X-CSRFToken": token}
    )


def password_login(client):
    token = csrf(client)
    response = client.post(
        "/login", data={"username": "admin", "password": "correct password", "csrf_token": token}
    )
    assert response.status_code == 302
    return token


def enroll(client, authenticator):
    token = password_login(client)
    options = post(client, "/passkeys/options", token).get_json()
    response = post(client, "/passkeys/verify", token, {"credential": authenticator.register(options), "label": "Test"})
    assert response.status_code == 200, response.get_json()
    return token


def logout(client):
    client.post("/logout", data={"csrf_token": csrf(client)})
    assert client.get("/").status_code == 302


def test_login_page_offers_passkeys_only_when_enabled(client):
    assert b"Sign in with a passkey" in client.get("/login").data


def test_password_is_refused_once_a_passkey_exists(client):
    assert b'id="loginForm"' in client.get("/login").data
    token = enroll(client, SoftAuthenticator())
    logout(client)
    page = client.get("/login").data
    assert b'id="loginForm"' not in page and b"Sign in with a passkey" in page
    token = csrf(client)
    response = client.post(
        "/login", data={"username": "admin", "password": "correct password", "csrf_token": token}, follow_redirects=True
    )
    assert b"Password sign-in is off" in response.data
    assert client.get("/").status_code == 302


def test_reset_brings_the_password_back(client, monkeypatch):
    enroll(client, SoftAuthenticator())
    logout(client)
    monkeypatch.setattr("builtins.input", lambda *_: "yes")
    import runpy

    runpy.run_module("email_app.reset_passkeys", run_name="__main__")
    assert b'id="loginForm"' in client.get("/login").data
    token = csrf(client)
    assert client.post(
        "/login", data={"username": "admin", "password": "correct password", "csrf_token": token}
    ).status_code == 302


def test_password_stays_when_passkeys_are_disabled(client, monkeypatch):
    enroll(client, SoftAuthenticator())
    logout(client)
    monkeypatch.setattr("email_app.passkeys.ALLOWED_ORIGINS", set())
    assert b'id="loginForm"' in client.get("/login").data


def test_registration_requires_login(client):
    token = csrf(client)
    response = post(client, "/passkeys/options", token)
    assert response.status_code == 302 and "/login" in response.headers["Location"]


def test_register_then_sign_in_with_passkey(client):
    authenticator = SoftAuthenticator()
    enroll(client, authenticator)
    logout(client)

    token = csrf(client)
    options = post(client, "/passkey/login/options", token).get_json()
    response = post(client, "/passkey/login/verify", token, {"credential": authenticator.assert_(options)})
    assert response.status_code == 200
    assert client.get("/", follow_redirects=False).status_code != 302


def test_challenge_is_single_use(client):
    authenticator = SoftAuthenticator()
    enroll(client, authenticator)
    logout(client)

    token = csrf(client)
    options = post(client, "/passkey/login/options", token).get_json()
    assertion = authenticator.assert_(options)
    assert post(client, "/passkey/login/verify", token, {"credential": assertion}).status_code == 200
    logout(client)
    token = csrf(client)
    assert post(client, "/passkey/login/verify", token, {"credential": assertion}).status_code == 400


def test_wrong_origin_is_rejected(client):
    token = csrf(client)
    assert post(client, "/passkey/login/options", token, origin="https://evil.example").status_code == 403
    assert post(client, "/passkey/login/options", token, origin=None).status_code == 403


def test_assertion_from_unknown_key_is_rejected(client):
    enroll(client, SoftAuthenticator())
    logout(client)
    stranger = SoftAuthenticator()
    stranger.user_handle = b"x" * 16

    token = csrf(client)
    options = post(client, "/passkey/login/options", token).get_json()
    response = post(client, "/passkey/login/verify", token, {"credential": stranger.assert_(options)})
    assert response.status_code == 401
    assert client.get("/").status_code == 302


def test_assertion_with_forged_signature_is_rejected(client):
    authenticator = SoftAuthenticator()
    enroll(client, authenticator)
    logout(client)

    token = csrf(client)
    options = post(client, "/passkey/login/options", token).get_json()
    forged = SoftAuthenticator()
    forged.cred_id, forged.user_handle = authenticator.cred_id, authenticator.user_handle
    assert post(client, "/passkey/login/verify", token, {"credential": forged.assert_(options)}).status_code == 401


def test_list_and_remove_passkey(client):
    authenticator = SoftAuthenticator()
    token = enroll(client, authenticator)
    listing = client.get("/passkeys").get_json()
    assert [p["label"] for p in listing["passkeys"]] == ["Test"]
    cred_id = listing["passkeys"][0]["credential_id"]
    assert post(client, f"/passkeys/{cred_id}", token, method="delete").status_code == 200
    assert client.get("/passkeys").get_json()["passkeys"] == []
    assert post(client, f"/passkeys/{cred_id}", token, method="delete").status_code == 404


def test_passkey_endpoints_need_csrf(client):
    password_login(client)
    assert client.post("/passkeys/options", headers={"Origin": ORIGIN}).status_code == 400


def test_disabled_without_origins(client, monkeypatch):
    monkeypatch.setenv("PASSKEY_ORIGINS", "")
    import app
    import email_app.passkeys as passkeys

    importlib.reload(passkeys)
    application = importlib.reload(app).app
    application.config.update(TESTING=True, WTF_CSRF_TIME_LIMIT=None, RATELIMIT_ENABLED=False)
    disabled = application.test_client()
    assert b"Sign in with a passkey" not in disabled.get("/login").data
    token = re.search(rb'name="csrf_token" value="([^"]+)"', disabled.get("/login").data).group(1).decode()
    assert disabled.post("/passkey/login/options", headers={"X-CSRFToken": token, "Origin": ORIGIN}).status_code == 403
