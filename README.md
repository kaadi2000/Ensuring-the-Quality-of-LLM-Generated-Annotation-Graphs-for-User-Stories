# Ensuring the Quality of LLM-Generated Annotation Graphs for User Stories

This project implements a quality-assurance pipeline for annotation graphs derived from agile user stories.

It supports two entry paths:

1. **Raw user stories**, which can first be converted to annotation JSON by a local LLM.
2. **Existing annotation JSON**, which can be sent directly into the assurance pipeline.

Each user story is processed independently. Stories are never merged into one shared graph.

---

## Pipeline Flow

```text
Raw User Story
      │
      ├── optional LLM extraction
      ↓
Annotation JSON
      ↓
JSON Schema Validation
      ↓
Graph Consistency Validation
      ↓
Internal Graph Construction
      ↓
Save Graph Artifacts
  ├── JSON
  ├── DOT
  ├── SVG
  └── XMI
      ↓
Henshin Parsing / Validation
      ↓
Per-story Result
```

For a batch:

```text
Story 1 → Graph 1 → Henshin result 1
Story 2 → Graph 2 → Henshin result 2
Story 3 → Graph 3 → Henshin result 3
```

The graphs are never merged.

### Per-story fault isolation

Each story stops only at the stage it fails.

```text
JSON validation fails
→ stop that story
→ continue with the next story

JSON passes
→ graph validation fails
→ stop that story
→ continue with the next story

Graph validation passes
→ build graph
→ save JSON / DOT / SVG / XMI
→ run Henshin validation

Henshin validation fails
→ keep the already generated graph artifacts
→ record the Henshin failure
→ continue with the next story
```

This means a Henshin failure does **not** remove or block graph artifacts that were already created after successful graph validation.

---

## Pipeline Summary

A completed pipeline run reports how many stories passed each assurance stage independently.

Example:

```json
{
  "story_count": 5,
  "json_validation_passed_count": 4,
  "graph_validation_passed_count": 3,
  "henshin_validation_passed_count": 2
}
```

This provides more information than a single batch-level pass/fail result.

---

## Main Features

- Optional LLM-based annotation extraction from user stories
- Direct processing of existing annotation JSON
- JSON Schema validation
- Graph consistency validation
- Ecore cardinality checks
- One independent graph per user story
- Internal graph construction
- DOT export
- SVG rendering with Graphviz
- XMI model construction
- Henshin-based parsing and validation
- Per-story fault isolation
- Independent pass counts for JSON, graph, and Henshin validation
- Persistent run artifacts
- Automated pytest test suite

---

## Annotation Format

Each annotation has the following structure:

```json
{
  "PID": "#G01#",
  "Text": "As a public user, I want to search for information.",
  "Persona": [
    "public user"
  ],
  "Action": {
    "Primary Action": [
      "search"
    ],
    "Secondary Action": []
  },
  "Entity": {
    "Primary Entity": [
      "information"
    ],
    "Secondary Entity": []
  },
  "Benefit": "",
  "Triggers": [
    [
      "public user",
      "search"
    ]
  ],
  "Targets": [
    [
      "search",
      "information"
    ]
  ],
  "Contains": []
}
```

---

## Validation

### 1. JSON Schema Validation

JSON validation checks the structure and types of annotation data.

Examples include:

- required fields
- field types
- top-level structure
- `Persona` list structure
- `Action` object structure
- `Entity` object structure
- relation list structure
- relation entries containing exactly two strings

A story that fails this stage is not passed to graph validation.

### 2. Graph Consistency Validation

Graph validation checks whether relation endpoints correspond to declared graph nodes.

Examples:

```text
Triggers:
Persona → Action

Targets:
Action → Entity

Contains:
Entity → Entity
```

The validator checks, among other things:

- Trigger sources exist in `Persona`
- Trigger targets exist in `Action`
- Target sources exist in `Action`
- Target targets exist in `Entity`
- Contains sources exist in `Entity`
- Contains targets exist in `Entity`
- duplicate labels and relations
- suspicious labels
- Ecore cardinality constraints

The Ecore model contains single-valued opposite references:

```text
Action.persona → one Persona
Entity.action  → one Action
```

Therefore structures such as:

```text
admin   → approve
manager → approve
```

or:

```text
create → report
review → report
```

violate the metamodel cardinality and are rejected by graph validation.

---

## Graph Construction

A graph is built only after both JSON validation and graph validation succeed.

The internal representation contains:

```text
nodes:
  personas
  activities
  entities

edges:
  triggers
  targets
  contains
```

Each story produces exactly one internal graph.

---

## Generated Artifacts

Once graph validation succeeds, the pipeline saves the graph before running Henshin validation.

For each graph-valid story the pipeline generates:

```text
graph JSON
DOT
SVG
XMI
```

This ordering is intentional:

```text
Graph Validation
      ↓
Graph Construction
      ↓
JSON / DOT / SVG / XMI
      ↓
Henshin Validation
```

Therefore graph artifacts remain available even if Henshin parsing later fails.

---

## EMF / XMI Model

The Java service converts the internal graph representation into an EMF model conforming to:

```text
parsingAnnotationGraphs.ecore
```

The metamodel contains:

```text
AnnotationGraph
├── persona*
├── action*
└── entity*

Persona
└── triggers* ↔ Action.persona

Action
└── targets* ↔ Entity.action

Entity
└── contains*
```

An example serialized model is:

```xml
<parsingAnnotationGraphs:AnnotationGraph ...>
    <persona triggers="//@action.0" name="user"/>
    <action persona="//@persona.0"
            targets="//@entity.0"
            name="view"/>
    <entity action="//@action.0" name="order">
        <contains name="item"/>
    </entity>
</parsingAnnotationGraphs:AnnotationGraph>
```

Contained entities are serialized below their parent entity rather than duplicated as root entities.

---

## Henshin Parsing

The Java service uses the supplied Henshin transformation:

```text
parsing.henshin
```

The main parsing unit is:

```text
Parse
```

It repeatedly applies rules including:

```text
deletePersona
deleteAction
deleteRootEntity
deleteContainedEntity
```

A graph is considered fully parsed when the transformation succeeds and no personas, actions, or entities remain.

Conceptually:

```text
before parsing:

AnnotationGraph
├── Persona
├── Action
└── Entity

after successful parsing:

AnnotationGraph
```

A Henshin failure is recorded as a separate assurance result. It does not mean the preceding JSON or graph stages were incorrect.

---

## Project Structure

The relevant source structure is:

```text
.
├── app.py
├── api_server.py
├── pytest.ini
├── README.md
├── Validation Rules.md
├── sample_stories.txt
│
├── data/
│
├── graph/
│   ├── graph_builder.py
│   └── graph_visualizer.py
│
├── schemas/
│   └── annotation_graph.schema.json
│
├── validators/
│   ├── json_validator.py
│   └── graph_validator.py
│
├── utils/
│   └── result_writer.py
│
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   ├── test_json_validator.py
│   ├── test_graph_validator.py
│   ├── test_graph_builder.py
│   ├── test_pipeline.py
│   └── test_henshin_live.py
│
└── henshin-service/
    ├── pom.xml
    └── src/
        └── main/
            ├── java/
            │   └── de/uni/marburg/annotation/
            │       ├── GraphModelBuilder.java
            │       ├── HenshinHttpServer.java
            │       ├── HenshinValidator.java
            │       ├── InternalGraph.java
            │       └── ...
            │
            └── resources/
                ├── parsing.henshin
                ├── parsing.henshin_diagram
                ├── parsingAnnotationGraphs.ecore
                ├── parsingAnnotationGraphs.genmodel
                └── ...
```

Generated folders such as `outputs/`, `target/`, caches, and local environment files should not be treated as source code.

---

## Running the Project

### 1. Start the Java / Henshin Service

From:

```text
henshin-service/
```

run:

```powershell
mvn clean package
mvn exec:java "-Dexec.mainClass=de.uni.marburg.annotation.HenshinHttpServer"
```

The Java service runs on:

```text
http://127.0.0.1:8081
```

### 2. Start the Python API

From the project root:

```powershell
python -m uvicorn app:app --reload
```

The API runs on:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

---

## Main API Endpoints

### General

```text
GET /health
GET /schema
```

### Extraction

```text
POST /extract
```

Uses the configured local LLM to convert raw user stories into annotation JSON.

### Validation

```text
POST /validate/json
POST /validate/graph
POST /validate/henshin
```

### Graph Construction

```text
POST /build-graph
```

Returns one independent graph per supplied story.

### Full Pipeline With LLM Extraction

```text
POST /pipeline
```

Flow:

```text
Raw User Story
→ LLM Extraction
→ JSON Validation
→ Graph Validation
→ Graph Construction
→ Save Artifacts
→ Henshin Validation
```

### Full Pipeline With Existing Annotation JSON

```text
POST /pipeline/json
```

Flow:

```text
Annotation JSON
→ JSON Validation
→ Graph Validation
→ Graph Construction
→ Save Artifacts
→ Henshin Validation
```

### Visualization and Export

```text
POST /graph/visualize
POST /graph/visualize/svg
POST /graph/export/dot
POST /graph/export/svg
POST /graph/export/xmi
```

The single-graph export endpoints operate on one story graph at a time.

---

## Result Storage

Pipeline results are stored under:

```text
outputs/<run_id>/
```

A typical run contains:

```text
outputs/
└── <run_id>/
    ├── pipeline/
    │   └── pipeline_result.json
    │
    ├── validation/
    │   ├── 001_<PID>_json_validation.json
    │   ├── 001_<PID>_graph_validation.json
    │   └── 001_<PID>_henshin_validation.json
    │
    ├── graphs/
    │   ├── 001_<PID>_graph.json
    │   ├── 001_<PID>_graph.dot
    │   └── 001_<PID>_graph.svg
    │
    └── xmi/
        └── 001_<PID>_graph.xmi
```

The numerical story prefix prevents files from being overwritten when multiple stories use the same PID.

---

## Environment Configuration

Local configuration can be supplied through `.env`.

Example:

```env
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
LM_STUDIO_API_KEY=lm-studio
LM_STUDIO_MODEL=openai/gpt-oss-20b

HENSHIN_BASE_URL=http://127.0.0.1:8081

GRAPHVIZ_DOT_PATH=C:\Program Files\Graphviz\bin\dot.exe
```

The `.env` file is local configuration and should not be committed to Git.

---

## Graphviz

Graphviz is required for SVG generation.

The project uses the `dot` executable. On Windows it can be configured through:

```env
GRAPHVIZ_DOT_PATH=C:\Program Files\Graphviz\bin\dot.exe
```

---

## Tests

The Python test suite uses `pytest`.

Run all tests from the project root:

```powershell
python -m pytest -v
```

The suite covers:

- valid JSON annotations
- missing required schema fields
- invalid graph relation endpoints
- Ecore cardinality violations
- one graph per story
- `Contains` relations
- graph-valid but Henshin-invalid cases
- successful Henshin parsing
- JSON / graph / Henshin pass counters
- mixed-batch fault isolation
- graph artifact persistence
- duplicate PID output naming

### Live Henshin Integration Test

The Henshin integration test requires the Java service to be running.

If the test is configured to use the `HENSHIN_LIVE` environment variable, enable it before running the suite.

Command Prompt:

```cmd
set HENSHIN_LIVE=1
python -m pytest -v
```

PowerShell:

```powershell
$env:HENSHIN_LIVE="1"
python -m pytest -v
```

The live integration test verifies that a valid internal graph can be fully parsed by the real Java/Henshin service.

---
## Henshin Diagram

The supplied graphical Henshin model can be opened in Eclipse using:

```text
parsing.henshin
parsing.henshin_diagram
```

The appropriate Henshin / Eclipse modeling tooling is required for editing the graphical transformation model.