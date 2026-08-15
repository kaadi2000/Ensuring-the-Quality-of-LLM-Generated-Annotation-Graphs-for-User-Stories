from __future__ import annotations

from typing import Any


SUSPICIOUS_LABELS = {
    "when",
    "it",
    "thing",
    "stuff",
}


class GraphValidator:
    def _add_issue(
        self,
        issues: list[dict[str, Any]],
        *,
        severity: str,
        story_index: int,
        location: str,
        message: str,
    ) -> None:
        issues.append(
            {
                "severity": severity,
                "source": "graph",
                "story_index": story_index,
                "location": location,
                "message": message,
            }
        )

    def _check_empty_primary_lists(
        self,
        story: dict[str, Any],
        story_index: int,
        issues: list[dict[str, Any]],
    ) -> None:
        if not story["Persona"]:
            self._add_issue(
                issues,
                severity="warning",
                story_index=story_index,
                location=f"$[{story_index}].Persona",
                message="Persona list is empty.",
            )

        if not story["Action"]["Primary Action"]:
            self._add_issue(
                issues,
                severity="warning",
                story_index=story_index,
                location=f"$[{story_index}].Action.Primary Action",
                message="Primary Action list is empty.",
            )

        if not story["Entity"]["Primary Entity"]:
            self._add_issue(
                issues,
                severity="warning",
                story_index=story_index,
                location=f"$[{story_index}].Entity.Primary Entity",
                message="Primary Entity list is empty.",
            )

    def _check_label_quality(
        self,
        labels: list[str],
        *,
        story_index: int,
        location: str,
        category: str,
        issues: list[dict[str, Any]],
    ) -> None:
        exact_seen: set[str] = set()
        exact_reported: set[str] = set()
        case_groups: dict[str, set[str]] = {}

        for label_index, label in enumerate(labels):
            clean = label.strip()
            lowered = clean.casefold()

            if label in exact_seen and label not in exact_reported:
                self._add_issue(
                    issues,
                    severity="warning",
                    story_index=story_index,
                    location=f"{location}[{label_index}]",
                    message=f"Exact duplicate label in {category}: {label!r}.",
                )
                exact_reported.add(label)

            exact_seen.add(label)
            case_groups.setdefault(lowered, set()).add(label)

            if lowered in SUSPICIOUS_LABELS:
                self._add_issue(
                    issues,
                    severity="warning",
                    story_index=story_index,
                    location=f"{location}[{label_index}]",
                    message=f"Suspicious label in {category}: {label!r}.",
                )

        for variants in case_groups.values():
            if len(variants) > 1:
                self._add_issue(
                    issues,
                    severity="warning",
                    story_index=story_index,
                    location=location,
                    message=(
                        f"Case-insensitive duplicate labels in {category}: "
                        f"{sorted(variants)!r}."
                    ),
                )

    def validate(self, annotations: list[dict[str, Any]]) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        for story_index, story in enumerate(annotations):
            self._check_empty_primary_lists(story, story_index, issues)

            label_groups = [
                ("Persona", story["Persona"], f"$[{story_index}].Persona"),
                (
                    "Primary Action",
                    story["Action"]["Primary Action"],
                    f"$[{story_index}].Action.Primary Action",
                ),
                (
                    "Secondary Action",
                    story["Action"]["Secondary Action"],
                    f"$[{story_index}].Action.Secondary Action",
                ),
                (
                    "Primary Entity",
                    story["Entity"]["Primary Entity"],
                    f"$[{story_index}].Entity.Primary Entity",
                ),
                (
                    "Secondary Entity",
                    story["Entity"]["Secondary Entity"],
                    f"$[{story_index}].Entity.Secondary Entity",
                ),
            ]

            for category, labels, location in label_groups:
                self._check_label_quality(
                    labels,
                    story_index=story_index,
                    location=location,
                    category=category,
                    issues=issues,
                )

            personas = set(story["Persona"])
            activities = set(story["Action"]["Primary Action"])
            activities.update(story["Action"]["Secondary Action"])
            entities = set(story["Entity"]["Primary Entity"])
            entities.update(story["Entity"]["Secondary Entity"])

            checks = [
                ("Triggers", personas, activities, "persona", "activity"),
                ("Targets", activities, entities, "activity", "entity"),
                ("Contains", entities, entities, "entity", "entity"),
            ]

            for relation_name, source_pool, target_pool, source_kind, target_kind in checks:
                seen_pairs: set[tuple[str, str]] = set()

                for relation_index, pair in enumerate(story[relation_name]):
                    source, target = pair
                    relation = (source, target)

                    if source not in source_pool:
                        self._add_issue(
                            issues,
                            severity="error",
                            story_index=story_index,
                            location=f"$[{story_index}].{relation_name}[{relation_index}][0]",
                            message=f"{source!r} is not a known {source_kind}.",
                        )

                    if target not in target_pool:
                        self._add_issue(
                            issues,
                            severity="error",
                            story_index=story_index,
                            location=f"$[{story_index}].{relation_name}[{relation_index}][1]",
                            message=f"{target!r} is not a known {target_kind}.",
                        )

                    if relation in seen_pairs:
                        self._add_issue(
                            issues,
                            severity="warning",
                            story_index=story_index,
                            location=f"$[{story_index}].{relation_name}[{relation_index}]",
                            message=f"Duplicate {relation_name} relation {relation!r}.",
                        )

                    seen_pairs.add(relation)

        error_count = sum(1 for issue in issues if issue["severity"] == "error")
        warning_count = sum(1 for issue in issues if issue["severity"] == "warning")
        invalid_story_indexes = sorted(
            {
                issue["story_index"]
                for issue in issues
                if issue["severity"] == "error"
            }
        )

        return {
            "valid": error_count == 0,
            "story_count": len(annotations),
            "invalid_story_count": len(invalid_story_indexes),
            "invalid_story_indexes": invalid_story_indexes,
            "error_count": error_count,
            "warning_count": warning_count,
            "issues": issues,
        }