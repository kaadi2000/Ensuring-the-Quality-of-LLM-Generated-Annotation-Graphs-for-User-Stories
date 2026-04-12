from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REQUIRED_KEYS = ["PID", "Text", "Persona", "Action", "Entity", "Benefit", "Triggers", "Targets", "Contains",]


@dataclass
class StoryReport:
    index: int
    pid: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


def is_list_of_strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def add_duplicate_warnings(values: list[str], label: str, report: StoryReport) -> None:
    exact_seen: set[str] = set()
    exact_dupes: set[str] = set()

    lower_map: dict[str, set[str]] = {}
    for item in values:
        if item in exact_seen:
            exact_dupes.add(item)
        exact_seen.add(item)
        lower_map.setdefault(item.lower(), set()).add(item)

        if len(item.strip()) <= 2:
            report.warnings.append(f"{label} contains a very short label: {item!r}")
        if item.strip().lower() in {"when", "it", "thing", "stuff"}:
            report.warnings.append(f"{label} contains a suspicious label: {item!r}")

    for item in sorted(exact_dupes):
        report.warnings.append(f"{label} has an exact duplicate label: {item!r}")

    for lowered, variants in sorted(lower_map.items()):
        if len(variants) > 1:
            report.warnings.append(
                f"{label} has case-inconsistent duplicates: {sorted(variants)}"
            )


def validate_relation_list(rel_name: str, value: Any, allowed_sources: set[str], allowed_targets: set[str],source_kind: str, target_kind: str, report: StoryReport) -> None:
    if not isinstance(value, list):
        report.errors.append(f"{rel_name} must be a list")
        return

    seen_pairs: set[tuple[str, str]] = set()
    for idx, item in enumerate(value):
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not all(isinstance(x, str) for x in item)
        ):
            report.errors.append(
                f"{rel_name}[{idx}] must be a 2-element list of strings"
            )
            continue

        src, dst = item
        if src not in allowed_sources:
            report.errors.append(
                f"{rel_name}[{idx}] source {src!r} is not a known {source_kind}"
            )
        if dst not in allowed_targets:
            report.errors.append(
                f"{rel_name}[{idx}] target {dst!r} is not a known {target_kind}"
            )

        pair = (src, dst)
        if pair in seen_pairs:
            report.warnings.append(f"{rel_name} contains duplicate pair {pair!r}")
        seen_pairs.add(pair)


def validate_story(story: Any, index: int) -> StoryReport:
    report = StoryReport(index=index)

    if not isinstance(story, dict):
        report.errors.append("Story entry must be a JSON object")
        return report

    report.pid = story.get("PID") if isinstance(story.get("PID"), str) else None

    for key in REQUIRED_KEYS:
        if key not in story:
            report.errors.append(f"Missing required key: {key}")

    if report.errors:
        return report

    if not isinstance(story["PID"], str):
        report.errors.append("PID must be a string")

    if not isinstance(story["Text"], str):
        report.errors.append("Text must be a string")

    if not isinstance(story["Benefit"], str):
        report.errors.append("Benefit must be a string")

    if not is_list_of_strings(story["Persona"]):
        report.errors.append("Persona must be a list of strings")

    action = story["Action"]
    entity = story["Entity"]

    if not isinstance(action, dict):
        report.errors.append("Action must be an object")
        action = {}

    if not isinstance(entity, dict):
        report.errors.append("Entity must be an object")
        entity = {}

    primary_actions = action.get("Primary Action", [])
    secondary_actions = action.get("Secondary Action", [])
    primary_entities = entity.get("Primary Entity", [])
    secondary_entities = entity.get("Secondary Entity", [])

    if not is_list_of_strings(primary_actions):
        report.errors.append("Action['Primary Action'] must be a list of strings")
        primary_actions = []

    if not is_list_of_strings(secondary_actions):
        report.errors.append("Action['Secondary Action'] must be a list of strings")
        secondary_actions = []

    if not is_list_of_strings(primary_entities):
        report.errors.append("Entity['Primary Entity'] must be a list of strings")
        primary_entities = []

    if not is_list_of_strings(secondary_entities):
        report.errors.append("Entity['Secondary Entity'] must be a list of strings")
        secondary_entities = []

    personas = story["Persona"] if is_list_of_strings(story["Persona"]) else []
    activities = list(primary_actions) + list(secondary_actions)
    entities = list(primary_entities) + list(secondary_entities)

    if not personas:
        report.warnings.append("Persona list is empty")

    if not primary_actions:
        report.warnings.append("Primary Action list is empty")

    if not primary_entities:
        report.warnings.append("Primary Entity list is empty")

    add_duplicate_warnings(personas, "Persona", report)
    add_duplicate_warnings(activities, "Action", report)
    add_duplicate_warnings(entities, "Entity", report)

    validate_relation_list("Triggers", story["Triggers"], allowed_sources=set(personas), allowed_targets=set(activities), source_kind="persona", target_kind="activity", report=report,)
    
    validate_relation_list(
        "Targets",
        story["Targets"],
        allowed_sources=set(activities),
        allowed_targets=set(entities),
        source_kind="activity",
        target_kind="entity",
        report=report,
    )
    validate_relation_list(
        "Contains",
        story["Contains"],
        allowed_sources=set(entities),
        allowed_targets=set(entities),
        source_kind="entity",
        target_kind="entity",
        report=report,
    )

    return report


def validate_file(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "file": str(path),
            "valid": False,
            "errors": [f"Invalid JSON: {exc}"],
            "warnings": [],
            "stories": [],
            "summary": {
                "story_count": 0,
                "invalid_story_count": 0,
                "error_count": 1,
                "warning_count": 0,
            },
        }

    if not isinstance(raw, list):
        return {
            "file": str(path),
            "valid": False,
            "errors": ["Top-level JSON value must be a list"],
            "warnings": [],
            "stories": [],
            "summary": {
                "story_count": 0,
                "invalid_story_count": 0,
                "error_count": 1,
                "warning_count": 0,
            },
        }

    reports = [validate_story(story, idx) for idx, story in enumerate(raw)]

    error_count = sum(len(r.errors) for r in reports)
    warning_count = sum(len(r.warnings) for r in reports)
    invalid_story_count = sum(1 for r in reports if not r.valid)

    return {
        "file": str(path),
        "valid": error_count == 0,
        "errors": [],
        "warnings": [],
        "stories": [
            {
                "index": r.index,
                "pid": r.pid,
                "valid": r.valid,
                "errors": r.errors,
                "warnings": r.warnings,
            }
            for r in reports
        ],
        "summary": {
            "story_count": len(reports),
            "invalid_story_count": invalid_story_count,
            "error_count": error_count,
            "warning_count": warning_count,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate annotated user-story graphs.")
    parser.add_argument("json_file", type=Path, help="Path to the JSON file to validate")
    args = parser.parse_args()

    report = validate_file(args.json_file)

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
