from __future__ import annotations
import json
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"

def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

@pytest.fixture
def valid_story():
    return load_fixture("valid_story.json")

@pytest.fixture
def invalid_schema_story():
    return load_fixture("invalid_schema.json")

@pytest.fixture
def invalid_relation_story():
    return load_fixture("invalid_relation.json")

@pytest.fixture
def cardinality_story():
    return load_fixture("cardinality_violation.json")

@pytest.fixture
def contains_story():
    return load_fixture("contains_story.json")

@pytest.fixture
def henshin_invalid_story():
    return load_fixture("graph_valid_henshin_invalid.json")
