from __future__ import annotations

from typing import Any


def normalize_label(label: str) -> str:
    return " ".join(label.strip().lower().split())


class GraphBuilder:

    def build(self, annotations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        graphs: list[dict[str, Any]] = []

        for story in annotations:
            graphs.append(self._build_story_graph(story))

        return graphs

    def _build_story_graph(self,story: dict[str, Any],) -> dict[str, Any]:

        personas = { normalize_label(value) for value in story["Persona"] }

        activities = { normalize_label(value) for value in story["Action"]["Primary Action"] }

        activities.update( normalize_label(value) for value in story["Action"]["Secondary Action"])

        entities = { normalize_label(value) for value in story["Entity"]["Primary Entity"] }

        entities.update( normalize_label(value) for value in story["Entity"]["Secondary Entity"] )

        triggers = { (normalize_label(source),normalize_label(target),) for source, target in story["Triggers"] }

        targets = { ( normalize_label(source), normalize_label(target),) for source, target in story["Targets"] }

        contains = { ( normalize_label(source), normalize_label(target),) for source, target in story["Contains"] }

        return {
            "pid": story["PID"],
            "nodes": { "personas": sorted(personas), "activities": sorted(activities), "entities": sorted(entities),},
            "edges": {
                "triggers": [
                    {
                        "source": source,
                        "target": target,
                    }
                    for source, target in sorted(triggers)
                ],
                "targets": [
                    {
                        "source": source,
                        "target": target,
                    }
                    for source, target in sorted(targets)
                ],
                "contains": [
                    {
                        "source": source,
                        "target": target,
                    }
                    for source, target in sorted(contains)
                ],
            },
            "counts": { "personas": len(personas),"activities": len(activities),"entities": len(entities),"triggers": len(triggers),"targets": len(targets), "contains": len(contains), },
        }