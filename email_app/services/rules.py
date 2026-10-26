import datetime
import logging
import re
from functools import wraps
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import flash, redirect, session, url_for

from .cloudflare import CloudflareAPIError, cloudflare_client
from email_app.config import PLACEHOLDER_EMAIL_DOMAIN
from .words import get_random_words

WORD_LENGTH = 5


def _operation_failed(action):
    logging.error("Cloudflare routing operation failed: %s", action)
    flash(f"Failed to {action} routing rule.", "error")
    return False


def delete_email_routing_rule(rule_id):
    try:
        cloudflare_client.delete_rule(rule_id)
    except CloudflareAPIError:
        return _operation_failed("delete")
    flash("Routing rule deleted successfully!", "success")
    return True


def generate_random_email(text=None):
    try:
        text = text.split("@", 1)[0] if text else ""
        words, separator = identify_and_split(text) if text else ([], "-")
        separator = "." if separator == "." else "-"
        missing_words = 3 - len(words)
        if missing_words > 0 and separator != ".":
            words.extend(get_random_words(missing_words, WORD_LENGTH))
        return f"{separator.join(words)}@{PLACEHOLDER_EMAIL_DOMAIN}"
    except (OSError, ValueError) as error:
        logging.error("Email generation failed: %s", error)
        return f"fallback-email@{PLACEHOLDER_EMAIL_DOMAIN}"


def normalize_generated_email(text):
    """Return a submitted local part as an address in the configured domain."""
    local_part = (text or "").strip().split("@", 1)[0]
    if not local_part:
        return None
    return f"{local_part}@{PLACEHOLDER_EMAIL_DOMAIN}"


def identify_and_split(text):
    if not text:
        return [], "-"
    separators = list(set(re.findall(r"[^a-zA-Z0-9]+", text)))
    if len(separators) == 1:
        return text.split(separators[0]), separators[0]
    if separators:
        return re.split("|".join(map(re.escape, separators)), text), separators[0]
    return [text], "-"


def add_email_routing_rule(generated_email, destination_email, action_type, name):
    action = {"type": action_type}
    if action_type == "forward":
        action["value"] = [destination_email]
    payload = {
        "matchers": [{"type": "literal", "field": "to", "value": generated_email}],
        "actions": [action],
        "enabled": True,
        "name": name or "---",
    }
    try:
        cloudflare_client.create_rule(payload)
    except CloudflareAPIError:
        return _operation_failed("add")
    return True


def get_email_routing_addresses():
    page, per_page, rules = 1, 50, []
    try:
        while True:
            result = cloudflare_client.list_rules(page, per_page)
            rules.extend(result if isinstance(result, list) else [])
            # Cloudflare supplies pagination metadata at the response top level; a short page ends safely.
            if len(result) < per_page:
                break
            page += 1
    except CloudflareAPIError:
        logging.error("Could not fetch routing rules")
        return None
    return parse_json(rules)


def get_email_routing_rule(rule_id):
    try:
        return cloudflare_client.get_rule(rule_id)
    except CloudflareAPIError:
        logging.error("Could not fetch routing rule")
        return None


def update_rule(email_data):
    rule_id = email_data.get("id")
    if not rule_id:
        logging.error("Routing rule update missing id")
        return False
    actions = email_data.get("actions", [])
    for action in actions:
        if action.get("type") == "drop":
            action.pop("value", None)
    payload = {key: email_data[key] for key in {"actions", "matchers", "enabled", "name"} if key in email_data}
    try:
        cloudflare_client.update_rule(rule_id, payload)
        return True
    except CloudflareAPIError:
        return _operation_failed("update")


def get_rule_id_by_generated_email(generated_email):
    rules = get_email_routing_addresses() or []
    return next((rule["id"] for rule in rules if rule.get("generated_email") == generated_email), None)


def format_creation_time(value):
    """Return a compact local timestamp, or an empty value if it is unavailable."""
    if not value:
        return ""
    try:
        return datetime.datetime.fromisoformat(value).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return value


def parse_json(rules):
    parsed_rules = []
    for rule in rules:
        actions = rule.get("actions", [])
        if not actions or actions[0].get("type") == "worker":
            continue
        name = rule.get("name", "---@No creation time available")
        name_and_date = name.split("@", 1) if "@" in name else ["---", name]
        rule_data = {
            "creation_time": format_creation_time(
                name_and_date[1].removeprefix("Rule created at ")
            ),
            "name": name_and_date[0],
            "id": rule.get("id"),
            "generated_email": "",
            "destination_email": "Drop",
        }
        for matcher in rule.get("matchers", []):
            if matcher.get("field") == "to":
                rule_data["generated_email"] = matcher.get("value", "Unknown")
        for action in actions:
            if action.get("type") == "forward":
                rule_data["destination_email"] = action.get("value", ["Unknown"])[0]
        if rule_data["generated_email"]:
            parsed_rules.append(rule_data)
    return parsed_rules


def login_required(view):
    @wraps(view)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("You need to be logged in to access this page.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return decorated_function


def append_timestamp_to_name(name):
    try:
        current_time = datetime.datetime.now(ZoneInfo("Europe/Bucharest"))
    except ZoneInfoNotFoundError:
        logging.warning("Europe/Bucharest timezone unavailable; using UTC")
        current_time = datetime.datetime.now(datetime.timezone.utc)
    return f"{name}@Rule created at {current_time}"


def process_rule(rule_id, generated_email, destination_email, action_type, name):
    if not rule_id:
        return add_email_routing_rule(generated_email, destination_email, action_type, name)
    data = {
        "id": rule_id,
        "actions": [{"type": action_type}],
        "matchers": [{"field": "to", "type": "literal", "value": generated_email}],
        "enabled": True,
        "name": name,
    }
    if action_type != "drop":
        data["actions"][0]["value"] = [destination_email]
    return update_rule(data)
