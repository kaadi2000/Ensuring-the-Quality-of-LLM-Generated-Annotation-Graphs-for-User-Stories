from __future__ import annotations
import os
import httpx
import pytest

pytestmark = pytest.mark.integration


def test_live_henshin_can_fully_parse_simple_graph():
    base_url = os.getenv("HENSHIN_BASE_URL", "http://127.0.0.1:8081")
    payload = {
        "nodes": {
            "personas": ["user"],
            "activities": ["search"],
            "entities": ["information"],
        },
        "edges": {
            "triggers": [{"source": "user", "target": "search"}],
            "targets": [{"source": "search", "target": "information"}],
            "contains": [],
        },
    }
    response = httpx.post(f"{base_url}/validate", json=payload, timeout=10.0)
    response.raise_for_status()
    result = response.json()
    assert result["valid"] is True
    assert result["parsed"] is True
    assert result["fully_parsed"] is True
    assert result["remaining"] == {
        "personas": 0,
        "actions": 0,
        "entities": 0,
    }
