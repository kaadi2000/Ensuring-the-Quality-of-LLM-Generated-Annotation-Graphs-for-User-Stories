package de.uni.marburg.annotation;

import java.io.IOException;
import java.nio.file.Path;

import com.fasterxml.jackson.databind.ObjectMapper;

public final class JsonGraphLoader {

    private final ObjectMapper objectMapper = new ObjectMapper();

    public InternalGraph load(Path path) throws IOException {
        return objectMapper.readValue(
                path.toFile(),
                InternalGraph.class
        );
    }
}