from pathlib import Path
import json

base = Path("/mnt/data")
rules_dir = base / "rules"
rules_dir.mkdir(exist_ok=True)

rules = {
  "metadata": {
    "name": "Default JSON validation rules",
    "version": "1.0"
  },
  "settings": {
    "invalid_story_threshold_percent": 2.0
  },
  "node_pools": {
    "personas": ["Persona"],
    "activities": ["Action.Primary Action", "Action.Secondary Action"],
    "entities": ["Entity.Primary Entity", "Entity.Secondary Entity"]
  },
  "rules": [
    {"id": "R001", "name": "PID required", "enabled": True, "severity": "error", "check_type": "required", "path": "PID", "message": "Missing required key: PID"},
    {"id": "R002", "name": "Text required", "enabled": True, "severity": "error", "check_type": "required", "path": "Text", "message": "Missing required key: Text"},
    {"id": "R003", "name": "Persona required", "enabled": True, "severity": "error", "check_type": "required", "path": "Persona", "message": "Missing required key: Persona"},
    {"id": "R004", "name": "Action required", "enabled": True, "severity": "error", "check_type": "required", "path": "Action", "message": "Missing required key: Action"},
    {"id": "R005", "name": "Entity required", "enabled": True, "severity": "error", "check_type": "required", "path": "Entity", "message": "Missing required key: Entity"},
    {"id": "R006", "name": "Benefit required", "enabled": True, "severity": "error", "check_type": "required", "path": "Benefit", "message": "Missing required key: Benefit"},
    {"id": "R007", "name": "Triggers required", "enabled": True, "severity": "error", "check_type": "required", "path": "Triggers", "message": "Missing required key: Triggers"},
    {"id": "R008", "name": "Targets required", "enabled": True, "severity": "error", "check_type": "required", "path": "Targets", "message": "Missing required key: Targets"},
    {"id": "R009", "name": "Contains required", "enabled": True, "severity": "error", "check_type": "required", "path": "Contains", "message": "Missing required key: Contains"},

    {"id": "R010", "name": "PID string", "enabled": True, "severity": "error", "check_type": "type", "path": "PID", "expected_type": "string", "message": "PID must be a string"},
    {"id": "R011", "name": "Text string", "enabled": True, "severity": "error", "check_type": "type", "path": "Text", "expected_type": "string", "message": "Text must be a string"},
    {"id": "R012", "name": "Benefit string", "enabled": True, "severity": "error", "check_type": "type", "path": "Benefit", "expected_type": "string", "message": "Benefit must be a string"},

    {"id": "R013", "name": "Persona list of strings", "enabled": True, "severity": "error", "check_type": "list_of_strings", "path": "Persona", "message": "Persona must be a list of strings"},
    {"id": "R014", "name": "Primary Action list of strings", "enabled": True, "severity": "error", "check_type": "list_of_strings", "path": "Action.Primary Action", "message": "Primary Action must be a list of strings"},
    {"id": "R015", "name": "Secondary Action list of strings", "enabled": True, "severity": "error", "check_type": "list_of_strings", "path": "Action.Secondary Action", "message": "Secondary Action must be a list of strings"},
    {"id": "R016", "name": "Primary Entity list of strings", "enabled": True, "severity": "error", "check_type": "list_of_strings", "path": "Entity.Primary Entity", "message": "Primary Entity must be a list of strings"},
    {"id": "R017", "name": "Secondary Entity list of strings", "enabled": True, "severity": "error", "check_type": "list_of_strings", "path": "Entity.Secondary Entity", "message": "Secondary Entity must be a list of strings"},

    {"id": "R018", "name": "Triggers relation shape", "enabled": True, "severity": "error", "check_type": "relation_shape", "path": "Triggers", "message": "Triggers entries must be 2-element lists of strings"},
    {"id": "R019", "name": "Targets relation shape", "enabled": True, "severity": "error", "check_type": "relation_shape", "path": "Targets", "message": "Targets entries must be 2-element lists of strings"},
    {"id": "R020", "name": "Contains relation shape", "enabled": True, "severity": "error", "check_type": "relation_shape", "path": "Contains", "message": "Contains entries must be 2-element lists of strings"},

    {"id": "R021", "name": "Triggers endpoint check", "enabled": True, "severity": "error", "check_type": "relation_endpoint_check", "path": "Triggers", "source_pool": "personas", "target_pool": "activities", "source_kind": "persona", "target_kind": "activity", "message": "Triggers must connect Persona to Activity"},
    {"id": "R022", "name": "Targets endpoint check", "enabled": True, "severity": "error", "check_type": "relation_endpoint_check", "path": "Targets", "source_pool": "activities", "target_pool": "entities", "source_kind": "activity", "target_kind": "entity", "message": "Targets must connect Activity to Entity"},
    {"id": "R023", "name": "Contains endpoint check", "enabled": True, "severity": "error", "check_type": "relation_endpoint_check", "path": "Contains", "source_pool": "entities", "target_pool": "entities", "source_kind": "entity", "target_kind": "entity", "message": "Contains must connect Entity to Entity"},

    {"id": "W001", "name": "Persona not empty", "enabled": True, "severity": "warning", "check_type": "not_empty", "path": "Persona", "message": "Persona list is empty"},
    {"id": "W002", "name": "Primary Action not empty", "enabled": True, "severity": "warning", "check_type": "not_empty", "path": "Action.Primary Action", "message": "Primary Action list is empty"},
    {"id": "W003", "name": "Primary Entity not empty", "enabled": True, "severity": "warning", "check_type": "not_empty", "path": "Entity.Primary Entity", "message": "Primary Entity list is empty"},
    {"id": "W004", "name": "Benefit no leading so that", "enabled": False, "severity": "warning", "check_type": "regex_not_match", "path": "Benefit", "pattern": "^(?i:so that\\b)", "message": "Benefit still contains leading framing text"}
  ]
}

validator_code = '''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TYPE_MAP = {
    "string": str,
    "list": list,
    "object": dict,
    "dict": dict,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "null": type(None),
}

@dataclass
class StoryReport:
    index: int
    pid: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

def get_path(obj: dict[str, Any], path: str, missing: Any = None) -> Any:
    current: Any = obj
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return missing
        current = current[part]
    return current

def path_exists(obj: dict[str, Any], path: str) -> bool:
    sentinel = object()
    return get_path(obj, path, sentinel) is not sentinel

def is_list_of_strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)

def add_issue(report: StoryReport, severity: str, message: str) -> None:
    if severity == "warning":
        report.warnings.append(message)
    else:
        report.errors.append(message)

def get_pool(story: dict[str, Any], pool_paths: list[str]) -> set[str]:
    values: set[str] = set()
    for path in pool_paths:
        value = get_path(story, path, [])
        if isinstance(value, list):
            values.update(item for item in value if isinstance(item, str))
    return values

def check_relation_shape(value: Any, path: str, report: StoryReport, severity: str) -> None:
    if not isinstance(value, list):
        add_issue(report, severity, f"{path} must be a list")
        return
    for idx, item in enumerate(value):
        if not (isinstance(item, list) and len(item) == 2 and all(isinstance(x, str) for x in item)):
            add_issue(report, severity, f"{path}[{idx}] must be a 2-element list of strings")

def check_relation_endpoints(story: dict[str, Any], rule: dict[str, Any], node_pools: dict[str, list[str]], report: StoryReport) -> None:
    path = rule["path"]
    relation_list = get_path(story, path, [])
    severity = rule.get("severity", "error")
    source_values = get_pool(story, node_pools[rule["source_pool"]])
    target_values = get_pool(story, node_pools[rule["target_pool"]])
    source_kind = rule.get("source_kind", "source")
    target_kind = rule.get("target_kind", "target")

    if not isinstance(relation_list, list):
        add_issue(report, severity, f"{path} must be a list")
        return

    for idx, item in enumerate(relation_list):
        if not (isinstance(item, list) and len(item) == 2 and all(isinstance(x, str) for x in item)):
            continue
        source, target = item
        if source not in source_values:
            add_issue(report, severity, f"{path}[{idx}] source {source!r} is not a known {source_kind}")
        if target not in target_values:
            add_issue(report, severity, f"{path}[{idx}] target {target!r} is not a known {target_kind}")

def apply_rule(story: dict[str, Any], rule: dict[str, Any], node_pools: dict[str, list[str]], report: StoryReport) -> None:
    if not rule.get("enabled", True):
        return

    check_type = rule["check_type"]
    severity = rule.get("severity", "error")
    path = rule.get("path")
    message = rule.get("message", f"Rule failed: {rule.get('id', 'UNKNOWN')}")

    if check_type == "required":
        if not path_exists(story, path):
            add_issue(report, severity, message)
        return

    value = get_path(story, path)

    if check_type == "type":
        expected = rule["expected_type"]
        if expected not in TYPE_MAP:
            add_issue(report, "warning", f"Unknown expected_type {expected!r} in rule {rule.get('id')}")
            return
        if not isinstance(value, TYPE_MAP[expected]):
            add_issue(report, severity, message)
        return

    if check_type == "list_of_strings":
        if not is_list_of_strings(value):
            add_issue(report, severity, message)
        return

    if check_type == "not_empty":
        if value == [] or value == "" or value is None:
            add_issue(report, severity, message)
        return

    if check_type == "regex_match":
        if not isinstance(value, str) or re.search(rule["pattern"], value) is None:
            add_issue(report, severity, message)
        return

    if check_type == "regex_not_match":
        if isinstance(value, str) and re.search(rule["pattern"], value):
            add_issue(report, severity, message)
        return

    if check_type == "allowed_values":
        if value not in set(rule["allowed_values"]):
            add_issue(report, severity, message)
        return

    if check_type == "relation_shape":
        check_relation_shape(value, path, report, severity)
        return

    if check_type == "relation_endpoint_check":
        check_relation_endpoints(story, rule, node_pools, report)
        return

    add_issue(report, "warning", f"Unknown rule type {check_type!r} in rule {rule.get('id')}")

def validate_story(story: Any, index: int, rules_config: dict[str, Any]) -> StoryReport:
    report = StoryReport(index=index)
    if not isinstance(story, dict):
        report.errors.append("Story entry must be a JSON object")
        return report

    pid = story.get("PID")
    report.pid = pid if isinstance(pid, str) else None

    for rule in rules_config.get("rules", []):
        apply_rule(story, rule, rules_config.get("node_pools", {}), report)
    return report

def validate_file(json_path: Path, rules_path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "file": str(json_path),
            "rules_file": str(rules_path),
            "valid": False,
            "errors": [f"Invalid JSON: {exc}"],
            "warnings": [],
            "stories": [],
            "summary": {"story_count": 0, "invalid_story_count": 0, "error_count": 1, "warning_count": 0},
        }

    rules_config = json.loads(rules_path.read_text(encoding="utf-8"))

    if not isinstance(raw, list):
        return {
            "file": str(json_path),
            "rules_file": str(rules_path),
            "valid": False,
            "errors": ["Top-level JSON value must be a list"],
            "warnings": [],
            "stories": [],
            "summary": {"story_count": 0, "invalid_story_count": 0, "error_count": 1, "warning_count": 0},
        }

    reports = [validate_story(story, idx, rules_config) for idx, story in enumerate(raw)]
    error_count = sum(len(r.errors) for r in reports)
    warning_count = sum(len(r.warnings) for r in reports)
    invalid_story_count = sum(1 for r in reports if not r.valid)

    return {
        "file": str(json_path),
        "rules_file": str(rules_path),
        "valid": error_count == 0,
        "errors": [],
        "warnings": [],
        "stories": [
            {"index": r.index, "pid": r.pid, "valid": r.valid, "errors": r.errors, "warnings": r.warnings}
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
    parser = argparse.ArgumentParser(description="Configurable JSON validator using editable rule files.")
    parser.add_argument("json_file", type=Path)
    parser.add_argument("--rules", type=Path, default=Path("rules") / "default_validation_rules.json")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    report = validate_file(args.json_file, args.rules)
    print(json.dumps(report, indent=2 if args.pretty else None, ensure_ascii=False))

if __name__ == "__main__":
    main()
'''

notes = '''# Configurable JSON Validator

Files:
- `configurable_json_validator.py`
- `rules/default_validation_rules.json`

The validator now reads rules from JSON instead of hardcoding them.

The UI can later edit:
- enabled/disabled
- severity: error/warning
- path
- check type
- regex pattern
- messages
- relation endpoint pools
- threshold setting

Supported check types:
- required
- type
- list_of_strings
- not_empty
- regex_match
- regex_not_match
- allowed_values
- relation_shape
- relation_endpoint_check

Example:
```bash
python configurable_json_validator.py llm_outputs\\extracted_stories.json --rules rules\\default_validation_rules.json --pretty'''