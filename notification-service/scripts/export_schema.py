import json
from pathlib import Path

from notification_service.events import event_adapter

path = Path(__file__).resolve().parents[1] / "contracts" / "events-v1.schema.json"
schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", **event_adapter.json_schema()}
path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
