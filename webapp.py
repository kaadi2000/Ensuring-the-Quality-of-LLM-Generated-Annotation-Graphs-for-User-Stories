from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import json
import re

from validators.json_validator import validate_json_data
from graph.graph_builder import build_graph_from_json

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def group_issues_by_story(issues: list[dict]) -> dict[int, list[dict]]:
    grouped = {}
    for issue in issues:
        location = issue.get("location", "")
        match = re.search(r"stories\[(\d+)\]", location)
        if match:
            idx = int(match.group(1))
            grouped.setdefault(idx, []).append(issue)
    return grouped


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )


@app.post("/validate", response_class=HTMLResponse)
async def validate(
    request: Request,
    json_text: str = Form(default=""),
    json_file: UploadFile | None = File(default=None),
):
    parsed_data = None
    issues = []
    summary = {"errors": 0, "warnings": 0, "status": "invalid"}

    try:
        if json_file and json_file.filename:
            content = await json_file.read()
            parsed_data = json.loads(content.decode("utf-8"))
        elif json_text.strip():
            parsed_data = json.loads(json_text)
        else:
            issues.append({
                "severity": "error",
                "source": "input",
                "message": "No JSON input provided.",
                "location": "$",
            })
            summary["errors"] = 1

            return templates.TemplateResponse(
                request=request,
                name="results.html",
                context={
                    "request": request,
                    "summary": summary,
                    "issues": issues,
                    "raw_json": None,
                    "story_issue_map": {},
                    "parsed_data": None,
                    "mode": "direct",
                },
            )

        validation_result = validate_json_data(parsed_data)
        graph_result = build_graph_from_json(parsed_data)

        issues.extend(validation_result.get("issues", []))
        issues.extend(graph_result.get("issues", []))

        errors = sum(1 for i in issues if i.get("severity") == "error")
        warnings = sum(1 for i in issues if i.get("severity") == "warning")

        summary = {
            "errors": errors,
            "warnings": warnings,
            "status": "valid" if errors == 0 else "invalid",
        }

        story_issue_map = group_issues_by_story(issues)

        return templates.TemplateResponse(
            request=request,
            name="results.html",
            context={
                "request": request,
                "summary": summary,
                "issues": issues,
                "raw_json": json.dumps(parsed_data, indent=2, ensure_ascii=False),
                "story_issue_map": story_issue_map,
                "parsed_data": parsed_data,
                "mode": "direct",
            },
        )

    except json.JSONDecodeError as e:
        issues.append({
            "severity": "error",
            "source": "parser",
            "message": f"Invalid JSON: {str(e)}",
            "location": "$",
        })
        summary["errors"] = 1

        return templates.TemplateResponse(
            request=request,
            name="results.html",
            context={
                "request": request,
                "summary": summary,
                "issues": issues,
                "raw_json": None,
                "story_issue_map": {},
                "parsed_data": None,
                "mode": "direct",
            },
        )


@app.post("/llm-validate", response_class=HTMLResponse)
async def llm_validate(
    request: Request,
    story_text: str = Form(default=""),
):
    # Placeholder for now until we wire extract_with_LLM.py properly
    issues = []
    summary = {"errors": 0, "warnings": 1, "status": "invalid"}

    if not story_text.strip():
        issues.append({
            "severity": "error",
            "source": "input",
            "message": "No story text provided for LLM extraction.",
            "location": "$",
        })
        summary["errors"] = 1
        summary["warnings"] = 0
    else:
        issues.append({
            "severity": "warning",
            "source": "llm",
            "message": "LLM extraction route is not wired yet. UI is ready, backend hook comes next.",
            "location": "$",
        })

    return templates.TemplateResponse(
        request=request,
        name="results.html",
        context={
            "request": request,
            "summary": summary,
            "issues": issues,
            "raw_json": None,
            "story_issue_map": {},
            "parsed_data": None,
            "mode": "llm",
        },
    )