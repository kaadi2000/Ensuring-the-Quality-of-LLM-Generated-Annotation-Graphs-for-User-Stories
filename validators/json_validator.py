from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "annotation_graph.schema.json"


class JsonValidator:
    def __init__(self, schema_path: Path | None = None) -> None:
        path = schema_path or SCHEMA_PATH
        schema = json.loads(path.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(schema)

    def validate(self, annotations: Any) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        invalid_story_indexes: set[int] = set()

        errors = sorted(
            self.validator.iter_errors(annotations),
            key=lambda error: [str(part) for part in error.absolute_path],
        )

        for error in errors:
            location = "$"
            story_index: int | None = None

            for position, part in enumerate(error.absolute_path):
                if isinstance(part, int):
                    location += f"[{part}]"
                    if position == 0:
                        story_index = part
                        invalid_story_indexes.add(part)
                else:
                    location += f".{part}"

            issue: dict[str, Any] = {
                "severity": "error",
                "source": "json-schema",
                "location": location,
                "message": error.message,
                "validator": error.validator,
            }

            if story_index is not None:
                issue["story_index"] = story_index

            issues.append(issue)

        story_count = len(annotations) if isinstance(annotations, list) else 0

        return {
            "valid": not issues,
            "story_count": story_count,
            "invalid_story_count": len(invalid_story_indexes),
            "invalid_story_indexes": sorted(invalid_story_indexes),
            "error_count": len(issues),
            "warning_count": 0,
            "issues": issues,
        }