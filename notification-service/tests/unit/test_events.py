import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError

from notification_service.events import event_adapter

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"
EXAMPLES = CONTRACTS / "examples"


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.json")), ids=lambda path: path.stem)
def test_event_examples_match_runtime_and_json_schema(path):
    schema = json.loads((CONTRACTS / "events-v1.schema.json").read_text(encoding="utf-8"))
    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema", **event_adapter.json_schema(),
    }
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    body = path.read_bytes()
    if path.stem.startswith("invalid-"):
        assert not validator.is_valid(json.loads(body))
        with pytest.raises(ValidationError):
            event_adapter.validate_json(body)
    else:
        validator.validate(json.loads(body))
        assert event_adapter.validate_json(body).event_type == path.stem


@pytest.mark.parametrize("field, value", [
    ("occurred_at", "2026-11-27T10:00:00"),
    ("occurred_at", "2026-11-27T10:00:00+03:00"),
    ("schema_version", True),
    ("password", "invalid-extra-field"),
])
def test_contract_rejects_invalid_metadata(field, value):
    event = json.loads((EXAMPLES / "task.created.json").read_bytes())
    event[field] = value
    with pytest.raises(ValidationError):
        event_adapter.validate_json(json.dumps(event))


def test_event_carries_a_normalized_task_title():
    event = json.loads((EXAMPLES / "task.created.json").read_bytes())
    event["payload"]["title"] = " ab "
    with pytest.raises(ValidationError):
        event_adapter.validate_json(json.dumps(event))
