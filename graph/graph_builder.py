from __future__ import annotations

from typing import Any


def normalize_label(label: str) -> str:
    return " ".join(label.strip().lower().split())


class GraphBuilder:
    def build(self, annotations: list[dict[str, Any]]) -> dict[str, Any]:
        personas: set[str] = set()
        activities: set[str] = set()
        entities: set[str] = set()
        triggers: set[tuple[str, str]] = set()
        targets: set[tuple[str, str]] = set()
        contains: set[tuple[str, str]] = set()

        for story in annotations:
            personas.update(normalize_label(value) for value in story["Persona"])
            activities.update(
                normalize_label(value)
                for value in story["Action"]["Primary Action"]
            )
            activities.update(
                normalize_label(value)
                for value in story["Action"]["Secondary Action"]
            )
            entities.update(
                normalize_label(value)
                for value in story["Entity"]["Primary Entity"]
            )
            entities.update(
                normalize_label(value)
                for value in story["Entity"]["Secondary Entity"]
            )

            triggers.update(
                (normalize_label(source), normalize_label(target))
                for source, target in story["Triggers"]
            )
            targets.update(
                (normalize_label(source), normalize_label(target))
                for source, target in story["Targets"]
            )
            contains.update(
                (normalize_label(source), normalize_label(target))
                for source, target in story["Contains"]
            )

        return {
            "nodes": {
                "personas": sorted(personas),
                "activities": sorted(activities),
                "entities": sorted(entities),
            },
            "edges": {
                "triggers": [
                    {"source": source, "target": target}
                    for source, target in sorted(triggers)
                ],
                "targets": [
                    {"source": source, "target": target}
                    for source, target in sorted(targets)
                ],
                "contains": [
                    {"source": source, "target": target}
                    for source, target in sorted(contains)
                ],
            },
            "counts": {
                "stories": len(annotations),
                "personas": len(personas),
                "activities": len(activities),
                "entities": len(entities),
                "triggers": len(triggers),
                "targets": len(targets),
                "contains": len(contains),
            },
        }