from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = PROJECT_ROOT / "outputs"


def create_run_id() -> str:
    """
    Example:
    20260829_154523_482731
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _safe_name(value: str) -> str:
    value = value.strip().replace("#", "")
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value or "unknown"


def _ensure_folder(folder: str, run_id: str) -> Path:
    path = OUTPUT_ROOT / run_id / folder
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_json(
    data: Any,
    *,
    folder: str,
    name: str,
    run_id: str,
) -> Path:

    output_dir = _ensure_folder(folder, run_id)

    path = output_dir / f"{_safe_name(name)}.json"

    path.write_text(
        json.dumps(data, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"[OUTPUT] Saved: {path}")

    return path


def save_text(
    content: str,
    *,
    folder: str,
    name: str,
    extension: str,
    run_id: str,
) -> Path:

    output_dir = _ensure_folder(folder, run_id)

    extension = extension.lstrip(".")

    path = output_dir / (
        f"{_safe_name(name)}.{extension}"
    )

    path.write_text(
        content,
        encoding="utf-8",
    )

    print(f"[OUTPUT] Saved: {path}")

    return path


def save_bytes(
    content: bytes,
    *,
    folder: str,
    name: str,
    extension: str,
    run_id: str,
) -> Path:

    output_dir = _ensure_folder(folder, run_id)

    extension = extension.lstrip(".")

    path = output_dir / (
        f"{_safe_name(name)}.{extension}"
    )

    path.write_bytes(content)

    print(f"[OUTPUT] Saved: {path}")

    return path