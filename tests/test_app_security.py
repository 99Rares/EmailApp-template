import importlib
import re

import bcrypt
import pytest


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("MY_USER", "admin")
    monkeypatch.setenv(
        "ADMIN_PASSWORD_HASH", bcrypt.hashpw(b"correct password", bcrypt.gensalt()).decode()
    )
    monkeypatch.setenv("EMAIL_LIST", "admin@example.test")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    import email_app.config as constants
    import app

    importlib.reload(constants)
    application = importlib.reload(app).app
    application.config.update(TESTING=True, WTF_CSRF_TIME_LIMIT=None)
    return application.test_client()


def csrf_token(client):
    response = client.get("/login")
    match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    assert match
    return match.group(1).decode()


def test_login_rejects_missing_csrf_token(client):
    response = client.post("/login", data={"username": "admin", "password": "correct password"})
    assert response.status_code == 400


def test_login_sets_security_headers(client):
    response = client.get("/login")
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert b'data-bs-theme="dark"' in response.data
    assert b"theme.js" in response.data
    assert b"snow.js" in response.data
    assert b"easter.js" in response.data
    assert b"season-controls.js" in response.data


def test_default_rate_limits_allow_normal_authenticated_use(client):
    import app

    assert app.default_rate_limits == ["5000 per day", "500 per hour"]


def test_add_rule_rejects_unapproved_forwarding_destination(client, monkeypatch):
    import app

    monkeypatch.setattr(app, "generate_random_email", lambda _: "alias@example.test")
    token = csrf_token(client)
    with client.session_transaction() as current_session:
        current_session["user"] = "admin"
    response = client.post(
        "/add-rule",
        data={
            "csrf_token": token,
            "generated_email": "alias",
            "destination_email": "attacker@example.test",
            "app_name": "test",
            "action_type": "forward",
        },
    )
    assert response.status_code == 400


@pytest.mark.parametrize("local_part", ["one", "one-two"])
def test_add_rule_updates_existing_short_address_without_expanding(
    client, monkeypatch, local_part
):
    import app

    existing_email = f"{local_part}@example.test"
    monkeypatch.setattr(app, "normalize_generated_email", lambda _: existing_email)
    monkeypatch.setattr(
        app,
        "get_rule_id_by_generated_email",
        lambda email: "rule-1" if email == existing_email else None,
    )
    monkeypatch.setattr(
        app,
        "generate_random_email",
        lambda _: pytest.fail("an existing address must not be expanded"),
    )
    processed = {}

    def capture_process_rule(*args):
        processed["args"] = args
        return True

    monkeypatch.setattr(app, "process_rule", capture_process_rule)
    token = csrf_token(client)
    with client.session_transaction() as current_session:
        current_session["user"] = "admin"

    response = client.post(
        "/add-rule",
        data={
            "csrf_token": token,
            "generated_email": local_part,
            "destination_email": "admin@example.test",
            "app_name": "test",
            "action_type": "forward",
        },
    )

    assert response.status_code == 302
    assert processed["args"][:3] == (
        "rule-1", existing_email, "admin@example.test"
    )


def test_destination_filter_is_applied_server_side(client, monkeypatch):
    import app

    monkeypatch.setattr(
        app,
        "get_email_routing_addresses",
        lambda: [
            {"destination_email": "admin@example.test", "generated_email": "keep@example.test"},
            {"destination_email": "other@example.test", "generated_email": "hide@example.test"},
        ],
    )
    with client.session_transaction() as current_session:
        current_session["user"] = "admin"
    response = client.get("/?destination=admin@example.test")
    assert b"keep@example.test" in response.data
    assert b"hide@example.test" not in response.data


def test_table_rows_expose_editable_rule_data(client, monkeypatch):
    import app

    monkeypatch.setattr(
        app,
        "get_email_routing_addresses",
        lambda: [
            {
                "destination_email": "admin@example.test",
                "generated_email": "edit@example.test",
                "name": "Service",
                "creation_time": "01.01.2026 12:00",
                "id": "rule-1",
            }
        ],
    )
    with client.session_transaction() as current_session:
        current_session["user"] = "admin"
    response = client.get("/")
    assert b'data-generated-email="edit@example.test"' in response.data
    assert b"/static/app.js" in response.data
    assert b'class="theme-label">Light mode</span>' in response.data
    assert b"/static/theme.js" in response.data
    assert b"/static/snow.js" in response.data
    assert b"/static/easter.js" in response.data
    assert b"/static/season-controls.js" in response.data
    assert b'data-season="christmas"' in response.data
    assert b'data-season="easter"' in response.data


def test_login_page_has_autofill_attributes_and_password_toggle(client):
    html = client.get("/login").data
    assert b'autocomplete="username"' in html
    assert b'autocomplete="current-password"' in html
    assert b"password-toggle" in html
    assert b"login.js" in html


def sign_in(client, remember):
    data = {"username": "admin", "password": "correct password", "csrf_token": csrf_token(client)}
    if remember:
        data["remember"] = "1"
    return client.post("/login", data=data)


def test_login_without_remember_me_uses_browser_session_cookie(client):
    response = sign_in(client, remember=False)
    assert response.status_code == 302
    assert "Expires=" not in response.headers["Set-Cookie"]


def test_login_with_remember_me_sets_persistent_cookie(client):
    response = sign_in(client, remember=True)
    assert response.status_code == 302
    assert "Expires=" in response.headers["Set-Cookie"]


def test_failed_login_marks_fields_invalid(client):
    data = {"username": "admin", "password": "wrong", "csrf_token": csrf_token(client)}
    client.post("/login", data=data)
    assert b"is-invalid" in client.get("/login").data


def test_login_rate_limit_shows_friendly_message(client):
    for _ in range(5):
        client.get("/login")
    response = client.get("/login")
    assert response.status_code == 429
    assert b"Too many sign-in attempts" in response.data
