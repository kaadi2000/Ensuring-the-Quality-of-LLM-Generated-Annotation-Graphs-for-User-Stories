#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from openai import OpenAI

DEFAULT_BASE_URL = "http://192.168.0.212:1234/v1"
DEFAULT_API_KEY = "lm-studio"
DEFAULT_MODEL = "openai/gpt-oss-20b"

PROMPT_TEMPLATE = """You are an information extraction system for agile user stories.

Extract the following user story into JSON with EXACTLY these fields:
- PID
- Text
- Persona
- Action
- Entity
- Benefit
- Triggers
- Targets
- Contains

Rules:
1. Return valid JSON only. No markdown. No explanation.
2. PID must be a string.
3. Text must be the full original story.
4. Persona must be a list of strings.
5. Action must be an object with:
   - "Primary Action": list of strings
   - "Secondary Action": list of strings
6. Entity must be an object with:
   - "Primary Entity": list of strings
   - "Secondary Entity": list of strings
7. Benefit must be a string.
8. Triggers must be a list of [persona, action].
9. Targets must be a list of [action, entity].
10. Contains must be a list of [entity, entity].
11. Extract all relevant primary and secondary actions and entities, including concepts in the benefit clause when applicable.
12. Preserve meaningful capitalization from the story.
13. If a category has no items, return an empty list for that category.
14. Use PID "{pid}". If the story already has an ID prefix like #G02#, preserve it exactly.
15. ALWAYS include the "Benefit" key. If no benefit is explicitly present in the story, return an empty string for Benefit.
16. Triggers must link Persona to Primary Action only. Do not create trigger relations to helper verbs such as want, need, can, have, be, or be able.
17. Contains must only contain pairs where BOTH source and target already appear in Primary Entity or Secondary Entity.
18. If no clear containment relation exists, return an empty list for Contains.
19. Do not invent relation endpoints that do not already exist in the extracted Persona, Action, or Entity lists.

User story:
{story}
"""

PID_PATTERN = re.compile(r"^(#\w+#)\s*(.*)$")
BLOCKED_TRIGGER_VERBS = {
    "want", "need", "can", "have", "be", "be able", "should", "could", "would"
}

def build_prompt(story: str, pid: str) -> str:
    return PROMPT_TEMPLATE.format(story=story.strip(), pid=pid)

def split_pid_and_story(line: str, fallback_pid: str) -> tuple[str, str]:
    match = PID_PATTERN.match(line.strip())
    if match:
        pid, _rest = match.groups()
        return pid, line.strip()
    return fallback_pid, line.strip()

def extract_json_with_llm(
    story: str,
    pid: str,
    base_url: str,
    api_key: str,
    model: str,
    temperature: float = 0.0,
) -> dict[str, Any]:
    client = OpenAI(base_url=base_url, api_key=api_key)
    prompt = build_prompt(story, pid)

    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.choices[0].message.content
    if content is None:
        raise ValueError("Model returned empty content")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Model output was not valid JSON for PID {pid}: {exc}\nRaw output:\n{content}"
        ) from exc

    return data

def sanitize_extracted_json(data: dict[str, Any], pid: str, story: str) -> dict[str, Any]:
    data.setdefault("PID", pid)
    data.setdefault("Text", story)
    data.setdefault("Persona", [])
    data.setdefault("Action", {})
    data.setdefault("Entity", {})
    data.setdefault("Benefit", "")
    data.setdefault("Triggers", [])
    data.setdefault("Targets", [])
    data.setdefault("Contains", [])

    if not isinstance(data["Action"], dict):
        data["Action"] = {}
    if not isinstance(data["Entity"], dict):
        data["Entity"] = {}

    data["Action"].setdefault("Primary Action", [])
    data["Action"].setdefault("Secondary Action", [])
    data["Entity"].setdefault("Primary Entity", [])
    data["Entity"].setdefault("Secondary Entity", [])

    if data["Benefit"] is None:
        data["Benefit"] = ""

    personas = {x for x in data["Persona"] if isinstance(x, str)}
    primary_actions = {x for x in data["Action"]["Primary Action"] if isinstance(x, str)}
    secondary_actions = {x for x in data["Action"]["Secondary Action"] if isinstance(x, str)}
    all_actions = primary_actions | secondary_actions
    all_entities = (
        {x for x in data["Entity"]["Primary Entity"] if isinstance(x, str)} |
        {x for x in data["Entity"]["Secondary Entity"] if isinstance(x, str)}
    )

    clean_triggers = []
    for item in data["Triggers"]:
        if not (isinstance(item, list) and len(item) == 2 and all(isinstance(x, str) for x in item)):
            continue
        src, dst = item
        if src in personas and dst in primary_actions and dst.strip().lower() not in BLOCKED_TRIGGER_VERBS:
            clean_triggers.append([src, dst])
    data["Triggers"] = clean_triggers

    clean_targets = []
    for item in data["Targets"]:
        if not (isinstance(item, list) and len(item) == 2 and all(isinstance(x, str) for x in item)):
            continue
        src, dst = item
        if src in all_actions and dst in all_entities:
            clean_targets.append([src, dst])
    data["Targets"] = clean_targets

    clean_contains = []
    for item in data["Contains"]:
        if not (isinstance(item, list) and len(item) == 2 and all(isinstance(x, str) for x in item)):
            continue
        src, dst = item
        if src in all_entities and dst in all_entities:
            clean_contains.append([src, dst])
    data["Contains"] = clean_contains

    if not isinstance(data["Benefit"], str):
        data["Benefit"] = str(data["Benefit"]) if data["Benefit"] is not None else ""

    return data

def load_stories_from_file(path: Path) -> list[str]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [line for line in lines if line]

def main() -> None:
    parser = argparse.ArgumentParser(description="Extract one or more user stories with LM Studio and save all outputs in a single JSON file.")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--story", type=str, help="Single user story text")
    source_group.add_argument("--input-file", type=Path, help="Text file containing one story per line")

    #do this part later -> Need to connect it properly
    #current ussage only with base url
    
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="LM Studio base URL ending in /v1")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API key for LM Studio OpenAI-compatible server")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model name as exposed by LM Studio")
    parser.add_argument("--output-file", type=Path, default=Path("llm_outputs") / "extracted_stories.json", help="Single output JSON file")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature")
    
    args = parser.parse_args()

    stories = [args.story] if args.story else load_stories_from_file(args.input_file)

    extracted_items: list[dict[str, Any]] = []
    run_summary: list[dict[str, Any]] = []

    for index, raw_story in enumerate(stories, start=1):
        fallback_pid = f"#TEMP-{index:03d}#"
        pid, story = split_pid_and_story(raw_story, fallback_pid)

        extracted = extract_json_with_llm(
            story=story,
            pid=pid,
            base_url=args.base_url,
            api_key=args.api_key,
            model=args.model,
            temperature=args.temperature,
        )
        extracted = sanitize_extracted_json(extracted, pid=pid, story=story)

        extracted_items.append(extracted)
        run_summary.append(
            {
                "story_index": index,
                "pid": pid,
                "story": story,
            }
        )

    output_file = args.output_file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(extracted_items, indent=2, ensure_ascii=False), encoding="utf-8")

    summary_file = output_file.with_name(output_file.stem + "_summary.json")
    summary_file.write_text(json.dumps(run_summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Processed {len(stories)} story(s).")
    print(f"Combined output file: {output_file}")
    print(f"Run summary file: {summary_file}")

if __name__ == "__main__":
    main()