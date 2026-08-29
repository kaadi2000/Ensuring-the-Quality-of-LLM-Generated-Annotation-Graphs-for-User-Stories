from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from pydantic import RootModel

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from graph import graph_builder
from validators.json_validator import JsonValidator
from validators.graph_validator import GraphValidator
from graph.graph_builder import GraphBuilder
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import httpx
from graph.graph_visualizer import GraphVisualizer
from fastapi import Body
import subprocess
from fastapi.responses import Response
from utils.result_writer import (
    create_run_id,
    save_json,
    save_text,
    save_bytes,
)

load_dotenv()

APP_ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = APP_ROOT / "schemas" / "annotation_graph.schema.json"

LM_STUDIO_BASE_URL = os.getenv(
    "LM_STUDIO_BASE_URL",
    "http://127.0.0.1:1234/v1",
)

LM_STUDIO_API_KEY = os.getenv(
    "LM_STUDIO_API_KEY",
    "lm-studio",
)

LM_STUDIO_MODEL = os.getenv(
    "LM_STUDIO_MODEL",
    "openai/gpt-oss-20b",
)

HENSHIN_BASE_URL = os.getenv(
    "HENSHIN_BASE_URL",
    "http://127.0.0.1:8081",
)

HENSHIN_SERVICE_URL = f"{HENSHIN_BASE_URL}/validate"
HENSHIN_XMI_URL = f"{HENSHIN_BASE_URL}/export/xmi"

GRAPHVIZ_DOT_PATH = os.getenv(
    "GRAPHVIZ_DOT_PATH",
    r"C:\Program Files\Graphviz\bin\dot.exe",
)

graph_visualizer = GraphVisualizer()

app = FastAPI(
    title="Annotation Graph Assurance API",
    version="0.1.0",
    description=(
        "API endpoints for extracting, validating, and building "
        "LLM-generated annotation graphs for user stories."
    ),
)

class AnnotationPayload(RootModel[list[dict[str, Any]]]):
    pass

class ExtractRequest(BaseModel):
    stories: list[str] = Field(min_length=1)
    temperature: float = 0.0



class PipelineRequest(BaseModel):
    stories: list[str] = Field(min_length=1)
    temperature: float = 0.0

def run_assurance_pipeline(
    annotations: list[dict[str, Any]]
) -> dict[str, Any]:

    print("===== PIPELINE FUNCTION CALLED =====")

    run_id = create_run_id()
    print("RUN ID:", run_id)

    # 1. JSON validation
    json_result = json_validator.validate(annotations)

    if not json_result["valid"]:
        pipeline_result = {
            "run_id": run_id,
            "stage": "json-validation",
            "valid": False,
            "json_validation": json_result,
            "graph_validation": None,
            "graphs": None,
            "henshin_validation": None,
        }

    else:
        # 2. Graph validation
        graph_result = graph_validator.validate(annotations)

        if not graph_result["valid"]:
            pipeline_result = {
                "run_id": run_id,
                "stage": "graph-validation",
                "valid": False,
                "json_validation": json_result,
                "graph_validation": graph_result,
                "graphs": None,
                "henshin_validation": None,
            }

        else:
            # 3. Build one graph per story
            internal_graphs = graph_builder.build(annotations)

            # 4. Henshin validation
            henshin_results = []

            for graph in internal_graphs:
                graph_payload = {
                    "nodes": graph["nodes"],
                    "edges": graph["edges"],
                }

                try:
                    response = httpx.post(
                        HENSHIN_SERVICE_URL,
                        json=graph_payload,
                        timeout=10.0,
                    )

                    response.raise_for_status()
                    result = response.json()

                except httpx.ConnectError as exc:
                    raise HTTPException(
                        status_code=503,
                        detail={
                            "message": "Henshin service is unavailable.",
                            "service": HENSHIN_SERVICE_URL,
                        },
                    ) from exc

                except httpx.HTTPStatusError as exc:
                    raise HTTPException(
                        status_code=502,
                        detail={
                            "message": "Henshin service returned an error.",
                            "pid": graph["pid"],
                            "status_code": exc.response.status_code,
                            "response": exc.response.text,
                        },
                    ) from exc

                henshin_results.append({
                    "pid": graph["pid"],
                    **result,
                })

            overall_valid = all(
                result["valid"]
                for result in henshin_results
            )

            pipeline_result = {
                "run_id": run_id,
                "stage": "complete",
                "valid": overall_valid,
                "json_validation": json_result,
                "graph_validation": graph_result,
                "graphs": internal_graphs,
                "henshin_validation": henshin_results,
            }

            for index, graph in enumerate(internal_graphs, start=1):
                pid = graph["pid"]
                file_prefix = f"{index:03d}_{pid}"

                save_json(
                    graph,
                    folder="graphs",
                    name=f"{file_prefix}_graph",
                    run_id=run_id,
                )

                dot = graph_visualizer.to_dot(graph)

                save_text(
                    dot,
                    folder="graphs",
                    name=f"{file_prefix}_graph",
                    extension="dot",
                    run_id=run_id,
                )

                svg = render_graph_svg(dot)

                save_text(
                    svg,
                    folder="graphs",
                    name=f"{file_prefix}_graph",
                    extension="svg",
                    run_id=run_id,
                )
                graph_payload = {
                    "nodes": graph["nodes"],
                    "edges": graph["edges"],
                }

                xmi_response = httpx.post(
                    HENSHIN_XMI_URL,
                    json=graph_payload,
                    timeout=10.0,
                )

                xmi_response.raise_for_status()

                save_bytes(
                    xmi_response.content,
                    folder="xmi",
                    name=f"{file_prefix}_graph",
                    extension="xmi",
                    run_id=run_id,
                )

            for index, result in enumerate(henshin_results, start=1):
                pid = result["pid"]

                file_prefix = f"{index:03d}_{pid}"

                save_json(
                    result,
                    folder="validation",
                    name=f"{file_prefix}_henshin_validation",
                    run_id=run_id,
                )

    # Save exactly once regardless of where validation stopped
    save_json(
        pipeline_result,
        folder="pipeline",
        name="pipeline_result",
        run_id=run_id,
    )

    return pipeline_result

@app.post("/graph/visualize")
def visualize_graph(
    payload: AnnotationPayload = Body(...)
) -> dict[str, Any]:
    annotations = payload.root

    schema_result = json_validator.validate(annotations)

    if not schema_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Visualization blocked by JSON-schema errors.",
                "validation": schema_result,
            },
        )

    graph_result = graph_validator.validate(annotations)

    if not graph_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Visualization blocked by graph errors.",
                "validation": graph_result,
            },
        )

    graph = get_single_graph(annotations)
    dot = graph_visualizer.to_dot(graph)

    return {
        "graph": graph,
        "dot": dot,
    }

@app.post("/graph/visualize/svg")
def visualize_graph_svg(
    payload: AnnotationPayload
) -> Response:
    annotations = payload.root

    schema_result = json_validator.validate(annotations)

    if not schema_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Visualization blocked by JSON-schema errors.",
                "validation": schema_result,
            },
        )

    graph_result = graph_validator.validate(annotations)

    if not graph_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Visualization blocked by graph errors.",
                "validation": graph_result,
            },
        )

    graph = get_single_graph(annotations)
    dot = graph_visualizer.to_dot(graph)
    svg = render_graph_svg(dot)

    return Response(
        content=svg,
        media_type="image/svg+xml",
    )

@app.post("/validate/henshin")
def validate_henshin(payload: AnnotationPayload) -> dict[str, Any]:
    annotations = payload.root

    schema_result = json_validator.validate(annotations)
    if not schema_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Henshin validation blocked by JSON-schema errors.",
                "validation": schema_result,
            },
        )

    graph_result = graph_validator.validate(annotations)
    if not graph_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Henshin validation blocked by graph errors.",
                "validation": graph_result,
            },
        )

    internal_graphs = graph_builder.build(annotations)

    results = []

    for graph in internal_graphs:
        graph_payload = {
            "nodes": graph["nodes"],
            "edges": graph["edges"],
        }

        try:
            response = httpx.post(
                HENSHIN_SERVICE_URL,
                json=graph_payload,
                timeout=10.0,
            )

            response.raise_for_status()
            result = response.json()

        except httpx.ConnectError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Henshin service is unavailable.",
                    "service": HENSHIN_SERVICE_URL,
                },
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "Henshin service returned an error.",
                    "pid": graph["pid"],
                    "status_code": exc.response.status_code,
                    "response": exc.response.text,
                },
            ) from exc

        results.append({
            "pid": graph["pid"],
            **result,
        })

    return {
        "valid": all(result["valid"] for result in results),
        "results": results,
    }
    
    """ internal_graph = graph_builder.build(annotations)

    try:
        response = httpx.post(
            HENSHIN_SERVICE_URL,
            json=internal_graph,
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()

    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Henshin service is unavailable.",
                "service": HENSHIN_SERVICE_URL,
            },
        ) from exc

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Henshin service returned an error.",
                "status_code": exc.response.status_code,
                "response": exc.response.text,
            },
        ) from exc """

@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = exc.errors()

    malformed_json = any(
        error.get("type") == "json_invalid"
        for error in errors
    )

    status_code = 400 if malformed_json else 422

    return JSONResponse(
        status_code=status_code,
        content={
            "valid": False,
            "error_count": len(errors),
            "warning_count": 0,
            "issues": [
                {
                    "severity": "error",
                    "source": "request",
                    "location": list(error.get("loc", [])),
                    "message": error.get("msg", "Invalid request."),
                }
                for error in errors
            ],
        },
    )

json_validator = JsonValidator()
graph_validator = GraphValidator()
graph_builder = GraphBuilder()





def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def split_pid(line: str, index: int) -> tuple[str, str]:
    match = re.match(r"^(#\w+#)\s*(.*)$", line.strip())
    if match:
        return match.group(1), line.strip()
    return f"#TEMP-{index:03d}#", line.strip()


PROMPT = """You are an information extraction system for agile user stories.

Extract the following user story into JSON with exactly these fields:
PID, Text, Persona, Action, Entity, Benefit, Triggers, Targets, Contains.

Rules:
- Return JSON only.
- Always include every field.
- Persona must be a list of strings.
- Action must contain "Primary Action" and "Secondary Action", both lists of strings.
- Entity must contain "Primary Entity" and "Secondary Entity", both lists of strings.
- Benefit must be a string. Use an empty string when no explicit benefit exists.
- Triggers must contain [persona, primary action] pairs.
- Targets must contain [action, entity] pairs.
- Contains must contain [entity, entity] pairs.
- Relation endpoints must exactly match labels present in the corresponding lists.
- Do not invent concepts.
- Use PID "{pid}".

User story:
{story}
"""


def extract_one(client: OpenAI, story: str, pid: str, temperature: float) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=LM_STUDIO_MODEL,
        temperature=temperature,
        messages=[
            {
                "role": "user",
                "content": PROMPT.format(pid=pid, story=story),
            }
        ],
    )

    content = response.choices[0].message.content

    print("===== RAW LLM RESPONSE =====")
    print(repr(content))
    print("============================")

    if not content or not content.strip():
        raise ValueError("The model returned an empty response.")

    return json.loads(content.strip())



def render_graph_svg(dot: str) -> str:
    try:
        result = subprocess.run(
            [GRAPHVIZ_DOT_PATH, "-Tsvg"],
            input=dot,
            text=True,
            capture_output=True,
            check=True,
        )

        return result.stdout

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Graphviz 'dot' executable was not found.",
                "path": GRAPHVIZ_DOT_PATH,
            },
        ) from exc

    except subprocess.CalledProcessError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Graphviz rendering failed.",
                "error": exc.stderr,
            },
        ) from exc

def get_single_graph(
        annotations: list[dict[str, Any]]
    ) -> dict[str, Any]:

        graphs = graph_builder.build(annotations)

        if len(graphs) != 1:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        "This endpoint exports one story graph at a time."
                    ),
                    "graph_count": len(graphs),
                },
            )

        return graphs[0]

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/schema")
def get_schema() -> dict[str, Any]:
    return load_schema()


@app.post("/extract")
def extract(request: ExtractRequest) -> dict[str, Any]:
    client = OpenAI(base_url=LM_STUDIO_BASE_URL, api_key=LM_STUDIO_API_KEY)
    annotations = []

    for index, raw_story in enumerate(request.stories, start=1):
        pid, story = split_pid(raw_story, index)
        try:
            annotations.append(extract_one(client, story, pid, request.temperature))
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "The LLM returned invalid JSON.",
                    "story_index": index - 1,
                    "error": str(exc),
                },
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "LLM extraction failed.",
                    "story_index": index - 1,
                    "error": str(exc),
                },
            ) from exc

    return {
        "count": len(annotations),
        "annotations": annotations,
    }


@app.post("/validate/json")
def validate_json(payload: AnnotationPayload) -> dict[str, Any]:
    return json_validator.validate(payload.root)


@app.post("/validate/graph")
def validate_graph(payload: AnnotationPayload) -> dict[str, Any]:
    schema_result = json_validator.validate(payload.root)
    if not schema_result["valid"]:
        return {
            "valid": False,
            "blocked_by": "json-schema",
            "json_validation": schema_result,
            "graph_validation": None,
        }

    return graph_validator.validate(payload.root)


@app.post("/build-graph")
def build_graph(payload: AnnotationPayload) -> dict[str, Any]:
    schema_result = json_validator.validate(payload.root)
    if not schema_result["valid"]:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Graph construction blocked by JSON-schema errors.",
                "validation": schema_result,
            },
        )

    graph_result = graph_validator.validate(payload.root)
    if not graph_result["valid"]:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Graph construction blocked by graph-consistency errors.",
                "validation": graph_result,
            },
        )

    return {
        "valid": True,
        "graphs": graph_builder.build(payload.root),
    }


# @app.post("/validate/henshin")
# def validate_henshin(payload: AnnotationPayload) -> JSONResponse:
#     return JSONResponse(
#         status_code=501,
#         content={
#             "implemented": False,
#             "message": (
#                 "The endpoint contract exists, but Henshin validation requires "
#                 "the Java/Henshin adapter service, which has not been implemented yet."
#             ),
#             "expected_input_count": len(payload.root),
#         },
#     )

@app.post("/pipeline/json")
def pipeline_json(
    payload: AnnotationPayload
) -> dict[str, Any]:

    result = run_assurance_pipeline(
        payload.root
    )

    return {
        "input_type": "annotation-json",
        **result,
    }

@app.post("/pipeline")
def pipeline(request: PipelineRequest) -> dict[str, Any]:

    extraction = extract(
        ExtractRequest(
            stories=request.stories,
            temperature=request.temperature,
        )
    )

    result = run_assurance_pipeline(
        extraction["annotations"]
    )

    return {
        "input_type": "user-stories",
        "extraction": extraction,
        **result,
    }

@app.post("/graph/export/dot")
def export_graph_dot(
    payload: AnnotationPayload
) -> Response:
    annotations = payload.root

    schema_result = json_validator.validate(annotations)

    if not schema_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Export blocked by JSON-schema errors.",
                "validation": schema_result,
            },
        )

    graph_result = graph_validator.validate(annotations)

    if not graph_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Export blocked by graph errors.",
                "validation": graph_result,
            },
        )

    graph = get_single_graph(annotations)
    dot = graph_visualizer.to_dot(graph)

    return Response(
        content=dot,
        media_type="text/vnd.graphviz",
        headers={
            "Content-Disposition": 'attachment; filename="annotation-graph.dot"'
        },
    )

@app.post("/graph/export/svg")
def export_graph_svg(
    payload: AnnotationPayload
) -> Response:
    annotations = payload.root

    schema_result = json_validator.validate(annotations)

    if not schema_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Export blocked by JSON-schema errors.",
                "validation": schema_result,
            },
        )

    graph_result = graph_validator.validate(annotations)

    if not graph_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Export blocked by graph errors.",
                "validation": graph_result,
            },
        )

    graph = get_single_graph(annotations)

    dot = graph_visualizer.to_dot(graph)
    svg = render_graph_svg(dot)

    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": 'attachment; filename="annotation-graph.svg"'
        },
    )



@app.post("/graph/export/xmi")
def export_graph_xmi(
    payload: AnnotationPayload
) -> Response:
    annotations = payload.root

    schema_result = json_validator.validate(annotations)

    if not schema_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "XMI export blocked by JSON-schema errors.",
                "validation": schema_result,
            },
        )

    graph_result = graph_validator.validate(annotations)

    if not graph_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "XMI export blocked by graph errors.",
                "validation": graph_result,
            },
        )

    graph = get_single_graph(annotations)

    internal_graph = {
        "nodes": graph["nodes"],
        "edges": graph["edges"],
    }

    try:
        print("Calling Henshin XMI service...")
        response = httpx.post(
            HENSHIN_XMI_URL,
            json=internal_graph,
            timeout=10.0,
        )
        print("Henshin XMI response received:", response.status_code)

        response.raise_for_status()

    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Henshin XMI service is unavailable.",
                "service": HENSHIN_XMI_URL,
            },
        ) from exc

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Henshin XMI service returned an error.",
                "status_code": exc.response.status_code,
                "response": exc.response.text,
            },
        ) from exc

    return Response(
        content=response.content,
        media_type="application/xml",
        headers={
            "Content-Disposition": 'attachment; filename="annotation-graph.xmi"'
        },
    )