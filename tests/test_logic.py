import email_app.services.rules as rules_service
from email_app.services.rules import identify_and_split, normalize_generated_email, parse_json


def test_identify_and_split_uses_detected_separator():
    assert identify_and_split("one-two") == (["one", "two"], "-")


def test_normalize_generated_email_preserves_existing_local_part(monkeypatch):
    monkeypatch.setattr("email_app.services.rules.PLACEHOLDER_EMAIL_DOMAIN", "example.test")

    assert normalize_generated_email("one-two") == "one-two@example.test"
    assert normalize_generated_email("one@example.test") == "one@example.test"


def test_add_rule_leaves_success_message_to_route(monkeypatch):
    monkeypatch.setattr(rules_service.cloudflare_client, "create_rule", lambda payload: None)
    flashes = []
    monkeypatch.setattr(rules_service, "flash", lambda *args: flashes.append(args))

    assert rules_service.add_email_routing_rule(
        "alias@example.test",
        "admin@example.test",
        "forward",
        "Service",
    )
    assert flashes == []


def test_parse_json_ignores_worker_rules_and_extracts_forwarding_data():
    rules = [
        {"actions": [{"type": "worker"}]},
        {
            "id": "rule-1",
            "name": "Mail@Rule created at 2026-01-01 12:00:00",
            "matchers": [{"field": "to", "value": "alias@example.test"}],
            "actions": [{"type": "forward", "value": ["admin@example.test"]}],
        },
    ]

    assert parse_json(rules) == [
        {
            "id": "rule-1",
            "name": "Mail",
            "creation_time": "01.01.2026 12:00",
            "generated_email": "alias@example.test",
            "destination_email": "admin@example.test",
        }
    ]
