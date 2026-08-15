package de.uni.marburg.annotation;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public record InternalGraph(
        Nodes nodes,
        Edges edges
) {
    public record Nodes(
            List<String> personas,
            List<String> activities,
            List<String> entities
    ) {
    }

    public record Edges(
            List<Edge> triggers,
            List<Edge> targets,
            List<Edge> contains
    ) {
    }

    public record Edge(
            String source,
            String target
    ) {
    }
}