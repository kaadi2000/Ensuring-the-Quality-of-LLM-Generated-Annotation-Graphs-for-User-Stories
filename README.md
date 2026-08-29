# Ensuring the Quality of LLM Generated Annotation Graphs for User Stories# Ensuring the Quality of LLM-Generated Annotation Graphs for User Stories

This project provides a quality assurance pipeline for annotation graphs generated from agile user stories.

The pipeline supports both raw user stories processed through an LLM and directly provided annotation JSON. Each user story is handled independently and produces its own annotation graph.

## Overview

```text
User Story
   ↓
Optional LLM Extraction
   ↓
Annotation JSON
   ↓
JSON Schema Validation
   ↓
Graph Consistency Validation
   ↓
Internal Graph Construction
   ↓
EMF Model Construction
   ↓
Henshin Parsing
   ↓
Graph / XMI / SVG / DOT Output
```

Multiple user stories are never merged into one graph:

```text
Story 1 → Graph 1
Story 2 → Graph 2
Story 3 → Graph 3
```

## Main Features

- LLM-based extraction of annotation graphs from user stories
- Direct processing of annotation JSON without using the LLM
- JSON Schema validation
- Graph consistency validation
- Validation against Ecore cardinalities
- One independent graph per user story
- EMF model construction
- Henshin-based graph parsing
- DOT graph generation
- SVG graph visualization
- XMI export
- Automatic result storage for pipeline runs

## Project Structure

```text
.
├── api_server.py
├── app.py
├── .env
├── schemas/
│   └── annotation_graph.schema.json
├── validators/
│   ├── json_validator.py
│   └── graph_validator.py
├── graph/
│   ├── graph_builder.py
│   └── graph_visualizer.py
├── utils/
│   └── result_writer.py
├── henshin-service/
│   ├── pom.xml
│   └── src/
│       └── main/
│           ├── java/
│           │   └── de/uni/marburg/annotation/
│           └── resources/
│               ├── parsing.henshin
│               ├── parsing.henshin_diagram
│               ├── parsingAnnotationGraphs.ecore
│               └── ...
└── outputs/
```

## Annotation Format

```json
{
  "PID": "#G01#",
  "Text": "As a public user, I want to search for information.",
  "Persona": ["public user"],
  "Action": {
    "Primary Action": ["search"],
    "Secondary Action": []
  },
  "Entity": {
    "Primary Entity": ["information"],
    "Secondary Entity": []
  },
  "Benefit": "",
  "Triggers": [
    ["public user", "search"]
  ],
  "Targets": [
    ["search", "information"]
  ],
  "Contains": []
}
```

## Validation

### JSON Validation

JSON Schema validation checks the structure and types of the annotation data, including:

- required fields
- correct field types
- valid relation structure
- correct `Action` and `Entity` object structure

### Graph Validation

Graph validation checks semantic consistency between nodes and relations.

Examples:

- Trigger source must exist in `Persona`
- Trigger target must exist in `Action`
- Target source must exist in `Action`
- Target target must exist in `Entity`
- Contains source and target must exist in `Entity`
- Duplicate relations generate warnings
- Suspicious labels generate warnings

The validator also checks cardinalities imposed by the Ecore metamodel.

For example:

```text
Action.persona → one Persona
Entity.action  → one Action
```

Therefore relations such as:

```text
admin   → approve
manager → approve
```

or:

```text
create → report
review → report
```

are invalid because they violate single-valued opposite references in the metamodel.

## Henshin Parsing

The Java service uses the provided Henshin transformation:

```text
parsing.henshin
```

The main transformation unit is:

```text
Parse
```

The transformation repeatedly applies parsing rules such as:

```text
deletePersona
deleteAction
deleteRootEntity
deleteContainedEntity
```

A successfully parsed annotation graph is reduced to an empty `AnnotationGraph` root.

Example transformed XMI:

```xml
<?xml version="1.0" encoding="ASCII"?>
<parsingAnnotationGraphs:AnnotationGraph
    xmi:version="2.0"
    xmlns:xmi="http://www.omg.org/XMI"
    xmlns:parsingAnnotationGraphs="http://www.example.org/parsingAnnotationGraphs"/>
```

## Running the Project

### 1. Start the Henshin Java Service

From `henshin-service/`:

```powershell
mvn clean package
mvn exec:java "-Dexec.mainClass=de.uni.marburg.annotation.HenshinHttpServer"
```

The Henshin service runs on:

```text
http://localhost:8081
```

### 2. Start the Python API

From the project root:

```powershell
python -m uvicorn app:app --reload
```

The API runs on:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```

## Main API Endpoints

### Health

```text
GET /health
```

### JSON Schema

```text
GET /schema
```

### LLM Extraction

```text
POST /extract
```

### JSON Validation

```text
POST /validate/json
```

### Graph Validation

```text
POST /validate/graph
```

### Graph Construction

```text
POST /build-graph
```

Returns one graph per user story.

### Henshin Validation

```text
POST /validate/henshin
```

Each user story graph is sent separately to the Henshin service.

### Full Pipeline With LLM

```text
POST /pipeline
```

Flow:

```text
Raw User Stories
→ LLM
→ JSON Validation
→ Graph Validation
→ Graph Construction
→ Henshin
```

### Full Pipeline Without LLM

```text
POST /pipeline/json
```

Flow:

```text
Annotation JSON
→ JSON Validation
→ Graph Validation
→ Graph Construction
→ Henshin
```

## Graph Export

Export endpoints operate on one user story at a time.

### DOT

```text
POST /graph/export/dot
```

### SVG

```text
POST /graph/export/svg
```

### XMI

```text
POST /graph/export/xmi
```

The XMI output conforms to:

```text
parsingAnnotationGraphs.ecore
```

Example:

```xml
<parsingAnnotationGraphs:AnnotationGraph ...>
    <persona triggers="//@action.0" name="user"/>
    <action persona="//@persona.0" targets="//@entity.0" name="view"/>
    <entity action="//@action.0" name="order">
        <contains name="item"/>
    </entity>
</parsingAnnotationGraphs:AnnotationGraph>
```

## Result Storage

Pipeline runs can automatically store generated results under:

```text
outputs/
```

Each run receives a unique timestamp-based run ID.

Example:

```text
outputs/
└── 20260829_154523_482731/
    ├── pipeline/
    │   └── pipeline_result.json
    ├── validation/
    │   ├── json_validation.json
    │   ├── graph_validation.json
    │   ├── 001_G01_henshin_validation.json
    │   └── 002_G02_henshin_validation.json
    ├── graphs/
    │   ├── 001_G01_graph.json
    │   ├── 001_G01_graph.dot
    │   ├── 001_G01_graph.svg
    │   ├── 002_G02_graph.json
    │   ├── 002_G02_graph.dot
    │   └── 002_G02_graph.svg
    └── xmi/
        ├── 001_G01_graph.xmi
        └── 002_G02_graph.xmi
```

The story index is included in filenames so that multiple stories using the same PID do not overwrite each other.

## Environment Configuration

Configuration is stored in `.env`.

Example:

```env
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_API_KEY=lm-studio
LM_STUDIO_MODEL=openai/gpt-oss-20b

HENSHIN_BASE_URL=http://localhost:8081

GRAPHVIZ_DOT_PATH=C:\Program Files\Graphviz\bin\dot.exe
```

Install the environment dependency with:

```powershell
pip install python-dotenv
```

## Graphviz

Graphviz is required for SVG rendering.

The `dot` executable must either be available in `PATH` or configured through:

```env
GRAPHVIZ_DOT_PATH=C:\Program Files\Graphviz\bin\dot.exe
```

## Henshin Diagram

The graphical Henshin model can be opened in Eclipse using:

```text
parsing.henshin
parsing.henshin_diagram
```

The Henshin Eclipse plugin and required Papyrus/GMF tooling must be installed for the graphical diagram editor.


## Notes

The `outputs/` directory contains generated run artifacts and should normally not be committed to Git.
