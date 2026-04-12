
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from json_validator import validate_file

MAX_INVALID_STORY_PERCENT = 2.0

def normalize_label(label: str) -> str:
    return " ".join(label.strip().split())


@dataclass(frozen=True, order=True)
class PersonaNode:
    name: str


@dataclass(frozen=True, order=True)
class ActivityNode:
    name: str
    level: str  # primary or secondary


@dataclass(frozen=True, order=True)
class EntityNode:
    name: str
    level: str  # primary or secondary


@dataclass(frozen=True, order=True)
class TriggerEdge:
    source: str
    target: str


@dataclass(frozen=True, order=True)
class TargetEdge:
    source: str
    target: str


@dataclass(frozen=True, order=True)
class ContainsEdge:
    source: str
    target: str


@dataclass
class StoryGraph:
    index: int
    pid: str
    text: str
    benefit: str
    personas: dict[str, PersonaNode] = field(default_factory=dict)
    activities: dict[str, ActivityNode] = field(default_factory=dict)
    entities: dict[str, EntityNode] = field(default_factory=dict)
    triggers: set[TriggerEdge] = field(default_factory=set)
    targets: set[TargetEdge] = field(default_factory=set)
    contains: set[ContainsEdge] = field(default_factory=set)


@dataclass
class CombinedGraph:
    personas: dict[str, PersonaNode] = field(default_factory=dict)
    activities: dict[str, ActivityNode] = field(default_factory=dict)
    entities: dict[str, EntityNode] = field(default_factory=dict)
    triggers: set[TriggerEdge] = field(default_factory=set)
    targets: set[TargetEdge] = field(default_factory=set)
    contains: set[ContainsEdge] = field(default_factory=set)
    story_graphs: list[StoryGraph] = field(default_factory=list)


def parse_story_to_graph(story: dict[str, Any], index: int) -> StoryGraph:
    pid = normalize_label(story["PID"])
    text = story["Text"].strip()
    benefit = story["Benefit"].strip()

    graph = StoryGraph(index=index, pid=pid, text=text, benefit=benefit)

    for persona in story["Persona"]:
        name = normalize_label(persona)
        if name:
            graph.personas.setdefault(name, PersonaNode(name=name))

    for level_key, level_name in [
        ("Primary Action", "primary"),
        ("Secondary Action", "secondary"),
    ]:
        for action in story["Action"][level_key]:
            name = normalize_label(action)
            if name and name not in graph.activities:
                graph.activities[name] = ActivityNode(name=name, level=level_name)

    for level_key, level_name in [
        ("Primary Entity", "primary"),
        ("Secondary Entity", "secondary"),
    ]:
        for entity in story["Entity"][level_key]:
            name = normalize_label(entity)
            if name and name not in graph.entities:
                graph.entities[name] = EntityNode(name=name, level=level_name)

    for source, target in story["Triggers"]:
        graph.triggers.add(
            TriggerEdge(source=normalize_label(source), target=normalize_label(target))
        )

    for source, target in story["Targets"]:
        graph.targets.add(
            TargetEdge(source=normalize_label(source), target=normalize_label(target))
        )

    for source, target in story["Contains"]:
        graph.contains.add(
            ContainsEdge(source=normalize_label(source), target=normalize_label(target))
        )

    return graph


def build_combined_graph(validated_json: list[dict[str, Any]]) -> CombinedGraph:
    combined = CombinedGraph()

    for idx, story in enumerate(validated_json):
        story_graph = parse_story_to_graph(story, idx)
        combined.story_graphs.append(story_graph)

        for name, node in story_graph.personas.items():
            combined.personas.setdefault(name, node)
        for name, node in story_graph.activities.items():
            # Keep the first seen level if duplicate names appear across stories
            combined.activities.setdefault(name, node)
        for name, node in story_graph.entities.items():
            combined.entities.setdefault(name, node)

        combined.triggers.update(story_graph.triggers)
        combined.targets.update(story_graph.targets)
        combined.contains.update(story_graph.contains)

    return combined


def graph_to_summary(graph: CombinedGraph) -> dict[str, Any]:
    return {
        "counts": {
            "story_graphs": len(graph.story_graphs),
            "personas": len(graph.personas),
            "activities": len(graph.activities),
            "entities": len(graph.entities),
            "triggers": len(graph.triggers),
            "targets": len(graph.targets),
            "contains": len(graph.contains),
        },
        "personas": sorted(graph.personas.keys()),
        "activities": [
            {"name": node.name, "level": node.level}
            for node in sorted(graph.activities.values(), key=lambda x: (x.name.lower(), x.level))
        ],
        "entities": [
            {"name": node.name, "level": node.level}
            for node in sorted(graph.entities.values(), key=lambda x: (x.name.lower(), x.level))
        ],
        "triggers": [
            {"source": edge.source, "target": edge.target}
            for edge in sorted(graph.triggers)
        ],
        "targets": [
            {"source": edge.source, "target": edge.target}
            for edge in sorted(graph.targets)
        ],
        "contains": [
            {"source": edge.source, "target": edge.target}
            for edge in sorted(graph.contains)
        ],
    }


def build_graph_report(path: Path) -> dict[str, Any]:
    validation = validate_file(path)
    result: dict[str, Any] = {
        "file": str(path),
        "validation": validation,
        "graph_built": False,
        "graph_summary": None,
        "message": "",
        "excluded_story_count": 0,
        "excluded_story_percentage": 0.0,
        "threshold_percentage": MAX_INVALID_STORY_PERCENT,
    }

    # Global fatal: invalid JSON / wrong top-level
    if validation["summary"]["story_count"] == 0:
        result["message"] = (
            "Graph was not built because the file has a global fatal error "
            "(invalid JSON or wrong top-level structure)."
        )
        return result

    total_stories = validation["summary"]["story_count"]
    invalid_stories = [s for s in validation["stories"] if not s["valid"]]
    valid_story_indexes = {s["index"] for s in validation["stories"] if s["valid"]}

    excluded_count = len(invalid_stories)
    excluded_percentage = (excluded_count / total_stories) * 100 if total_stories else 0.0

    result["excluded_story_count"] = excluded_count
    result["excluded_story_percentage"] = round(excluded_percentage, 2)

    if excluded_percentage > MAX_INVALID_STORY_PERCENT:
        result["message"] = (
            f"Graph was not built because {excluded_count}/{total_stories} stories "
            f"failed hard validation ({excluded_percentage:.2f}%), which exceeds "
            f"the {MAX_INVALID_STORY_PERCENT:.2f}% threshold."
        )
        return result

    raw = json.loads(path.read_text(encoding="utf-8"))
    filtered_raw = [story for idx, story in enumerate(raw) if idx in valid_story_indexes]

    graph = build_combined_graph(filtered_raw)
    result["graph_built"] = True
    result["graph_summary"] = graph_to_summary(graph)

    if excluded_count:
        result["message"] = (
            f"Partial graph built successfully after excluding "
            f"{excluded_count}/{total_stories} invalid stories "
            f"({excluded_percentage:.2f}%)."
        )
    else:
        result["message"] = "Graph built successfully with all stories."

    return result


def print_human_summary(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"File: {report['file']}")
    lines.append(f"Validation passed: {report['validation']['valid']}")
    lines.append(
        "Validation summary: "
        f"{report['validation']['summary']['story_count']} stories, "
        f"{report['validation']['summary']['error_count']} errors, "
        f"{report['validation']['summary']['warning_count']} warnings"
    )
    lines.append(report["message"])

    if report["graph_built"] and report["graph_summary"]:
        counts = report["graph_summary"]["counts"]
        lines.append("")
        lines.append("Combined graph counts:")
        for key, value in counts.items():
            lines.append(f"- {key}: {value}")

        lines.append("")
        lines.append("Sample personas:")
        for item in report["graph_summary"]["personas"][:10]:
            lines.append(f"- {item}")

        lines.append("")
        lines.append("Sample triggers:")
        for item in report["graph_summary"]["triggers"][:10]:
            lines.append(f"- {item['source']} -> {item['target']}")

    else:
        invalid_stories = [
            s for s in report["validation"]["stories"] if not s["valid"]
        ][:5]
        if invalid_stories:
            lines.append("")
            lines.append("First invalid stories:")
            for story in invalid_stories:
                lines.append(
                    f"- Story index {story['index']} PID={story['pid']}: "
                    + "; ".join(story["errors"])
                )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build internal graph from annotated JSON.")
    parser.add_argument("json_file", type=Path, help="Path to the JSON file")
    parser.add_argument(
        "--human",
        action="store_true",
        help="Print a readable text summary instead of JSON",
    )
    args = parser.parse_args()

    report = build_graph_report(args.json_file)

    if args.human:
        print(print_human_summary(report))
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
