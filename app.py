import os
from datetime import timedelta

import bcrypt
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from email_app.config import EMAIL_LIST, USER_CREDENTIALS
from email_app import passkeys
from email_app.services.rules import (
    generate_random_email,
    normalize_generated_email,
    append_timestamp_to_name,
    get_rule_id_by_generated_email,
    process_rule,
    get_email_routing_addresses,
    delete_email_routing_rule,
    get_email_routing_rule,
    update_rule,
    login_required
)
REMEMBER_ME_DAYS = 30

app = Flask(__name__)
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError("SECRET_KEY must be set before starting EmailApp.")

app.config.update(
    SECRET_KEY=secret_key,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=REMEMBER_ME_DAYS),
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "true").lower()
    in {"1", "true", "yes"},
)
csrf = CSRFProtect(app)
default_rate_limits = [
    limit.strip()
    for limit in os.environ.get(
        "RATELIMIT_DEFAULTS", "5000 per day,500 per hour"
    ).split(",")
    if limit.strip()
]
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=default_rate_limits,
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
)

app.register_blueprint(passkeys.bp)
limiter.limit("10 per minute")(app.view_functions["passkeys.login_options"])
limiter.limit("10 per minute")(app.view_functions["passkeys.login_verify"])


@app.context_processor
def inject_passkey_flag():
    return {
        "passkeys_enabled": passkeys.passkeys_enabled(),
        # While a passkey is registered the password is refused (use reset_passkeys.sh if every passkey is lost).
        "password_login": not passkeys.has_passkey(),
    }


ALLOWED_DESTINATIONS = {email.strip() for email in EMAIL_LIST.split(",") if email.strip()}


@app.after_request
def set_security_headers(response):
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' https://cdn.jsdelivr.net; "
        "script-src 'self' https://cdn.jsdelivr.net; font-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    if "user" in session:
        response.headers["Cache-Control"] = "private, no-store"
    return response


@app.errorhandler(429)
def rate_limited(error):
    if request.endpoint == "login":
        return render_template("login.html", rate_limited=True), 429
    return error


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if request.method == "POST":
        if passkeys.has_passkey():
            flash("Password sign-in is off while a passkey is registered. Use your passkey.", "danger")
            return redirect(url_for("login"))
        username = request.form["username"]
        password = request.form["password"].encode("utf-8")

        if username in USER_CREDENTIALS:
            stored_password_hash = USER_CREDENTIALS[username].encode("utf-8")
            if bcrypt.checkpw(password, stored_password_hash):
                session["user"] = username
                # Without "remember me" the cookie expires when the browser closes.
                session.permanent = request.form.get("remember") == "1"
                flash("Login successful!", "success")
                return redirect(url_for("index"))
            else:
                flash("Invalid username or password", "danger")
        else:
            flash("Invalid username or password", "danger")

        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    if request.method == "POST":
        session.pop("user", None)
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))
    return None


@app.route("/api/emails", methods=["GET"])
@login_required
def get_emails():
    # Get the emails list from the environment variable
    emails_list = EMAIL_LIST
    # Convert the comma-separated string to a list of dictionaries
    emails = [
        {"value": email, "label": email} for email in emails_list.split(",") if email
    ]

    return jsonify(emails)


@app.route("/")
@login_required
def index():
    """Render the index page with the list of email addresses."""
    email_addresses = get_email_routing_addresses()
    email_addresses = email_addresses or []
    selected_destination = request.args.get("destination", "non_drop")
    if selected_destination == "non_drop":
        email_addresses = [
            rule for rule in email_addresses if rule["destination_email"] != "Drop"
        ]
    elif selected_destination:
        email_addresses = [
            rule
            for rule in email_addresses
            if rule["destination_email"] == selected_destination
        ]
    email_addresses.sort(
        key=lambda rule: (rule["destination_email"] == "Drop", rule["destination_email"])
    )
    if not email_addresses:
        flash("No matching email routing rules found.", "info")
    return render_template(
        "index.html",
        email_addresses=email_addresses,
        destination_emails=sorted(ALLOWED_DESTINATIONS),
        selected_destination=selected_destination,
    )


@app.route("/add-rule", methods=["POST"])
@login_required
def add_rule():
    if request.method == "POST":
        generated_email = request.form.get("generated_email")
        destination_email = request.form.get("destination_email")
        name = request.form.get("app_name")
        action_type = request.form.get("action_type")

        if action_type not in {"forward", "drop"}:
            abort(400, "Invalid action type")

        if action_type == "forward" and destination_email not in ALLOWED_DESTINATIONS:
            abort(400, "Destination email is not allowed")

        destination_email = "Drop" if action_type == "drop" else destination_email
        existing_email = normalize_generated_email(generated_email)
        rule_id = (
            get_rule_id_by_generated_email(existing_email) if existing_email else None
        )
        if rule_id:
            generated_email = existing_email
        else:
            generated_email = generate_random_email(generated_email)
            rule_id = get_rule_id_by_generated_email(generated_email)
        name = append_timestamp_to_name(name)

        if generated_email and destination_email:
            success = process_rule(
                rule_id, generated_email, destination_email, action_type, name
            )

            if success:
                flash("Rule added or updated successfully.", "success")
            else:
                flash("Failed to add or update the rule.", "danger")

        return redirect(url_for("index"))
    return None


@app.route("/delete-rule/<rule_id>", methods=["POST"])
@login_required
def delete_rule(rule_id):
    success = delete_email_routing_rule(rule_id)
    return redirect(url_for("index"))


@app.route("/drop-rule/<rule_id>", methods=["POST"])
@login_required
def drop_rule(rule_id):
    """
    Drops an email routing rule by updating its action type to 'drop'.
    :param rule_id: The ID of the rule to drop.
    :return: Redirects to the index page.
    """
    email_data = get_email_routing_rule(rule_id)

    if not email_data:
        # Handle case where the rule could not be fetched
        flash("Failed to retrieve the email routing rule.", "error")
        return redirect(url_for("index"))

    # Update the action type to 'drop'
    if "actions" in email_data:
        for action in email_data["actions"]:
            action["type"] = "drop"
    else:
        flash("Invalid rule data structure: 'actions' missing.", "error")
        return redirect(url_for("index"))

    # Attempt to update the rule
    success = update_rule(email_data)

    if success:
        flash("Rule updated successfully to drop.", "success")
    else:
        flash("Failed to update the rule.", "error")

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run()
