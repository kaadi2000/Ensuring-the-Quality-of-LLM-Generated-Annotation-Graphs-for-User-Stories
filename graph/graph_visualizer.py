from __future__ import annotations

from typing import Any


class GraphVisualizer:

    def to_dot(self, graph: dict[str, Any]) -> str:
        lines = [
            "digraph AnnotationGraph {",
            '  rankdir="LR";',
            '  graph [pad="0.4", nodesep="0.6", ranksep="0.8"];',
        ]

        nodes = graph["nodes"]
        edges = graph["edges"]

        for persona in nodes["personas"]:
            lines.append(
                f'  {self._id("persona", persona)} '
                f'[label="{self._escape(persona)}", shape=box];'
            )

        for activity in nodes["activities"]:
            lines.append(
                f'  {self._id("activity", activity)} '
                f'[label="{self._escape(activity)}", shape=ellipse];'
            )

        for entity in nodes["entities"]:
            lines.append(
                f'  {self._id("entity", entity)} '
                f'[label="{self._escape(entity)}", shape=diamond];'
            )

        for edge in edges["triggers"]:
            lines.append(
                f'  {self._id("persona", edge["source"])} -> '
                f'{self._id("activity", edge["target"])} '
                f'[label="Triggers"];'
            )

        for edge in edges["targets"]:
            lines.append(
                f'  {self._id("activity", edge["source"])} -> '
                f'{self._id("entity", edge["target"])} '
                f'[label="Targets"];'
            )

        for edge in edges["contains"]:
            lines.append(
                f'  {self._id("entity", edge["source"])} -> '
                f'{self._id("entity", edge["target"])} '
                f'[label="Contains"];'
            )

        lines.append("}")

        return "\n".join(lines)

    def _id(self, node_type: str, label: str) -> str:
        return '"' + self._escape(f"{node_type}:{label}") + '"'

    def _escape(self, value: str) -> str:
        return (
            value
            .replace("\\", "\\\\")
            .replace('"', '\\"')
        )