from __future__ import annotations
from copy import deepcopy
import api_server as api

class FakeResponse:
    def __init__(self, *, json_data=None, content=b"", status_code=200, text=""):
        self._json_data = json_data
        self.content = content
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            request = api.httpx.Request("POST", "http://test")
            response = api.httpx.Response(self.status_code, request=request, text=self.text)
            raise api.httpx.HTTPStatusError("fake error", request=request, response=response)

def install_output_spies(monkeypatch):
    calls = {"json": [], "text": [], "bytes": []}

    def fake_save_json(data, *, folder, name, run_id):
        calls["json"].append({"data": data, "folder": folder, "name": name, "run_id": run_id})

    def fake_save_text(data, *, folder, name, extension, run_id):
        calls["text"].append({
            "data": data, "folder": folder, "name": name,
            "extension": extension, "run_id": run_id
        })

    def fake_save_bytes(data, *, folder, name, extension, run_id):
        calls["bytes"].append({
            "data": data, "folder": folder, "name": name,
            "extension": extension, "run_id": run_id
        })

    monkeypatch.setattr(api, "save_json", fake_save_json)
    monkeypatch.setattr(api, "save_text", fake_save_text)
    monkeypatch.setattr(api, "save_bytes", fake_save_bytes)
    monkeypatch.setattr(api, "create_run_id", lambda: "TEST_RUN")
    monkeypatch.setattr(api, "render_graph_svg", lambda dot: "<svg/>")
    return calls

def fake_henshin_result(valid: bool):
    return {
        "valid": valid,
        "parsed": True,
        "fully_parsed": valid,
        "remaining": {
            "personas": 0,
            "actions": 0 if valid else 1,
            "entities": 0,
        },
    }

def test_graph_outputs_are_saved_even_when_henshin_fails(monkeypatch, henshin_invalid_story):
    calls = install_output_spies(monkeypatch)

    def fake_post(url, *, json, timeout):
        if url == api.HENSHIN_XMI_URL:
            return FakeResponse(content=b"<xmi/>")
        if url == api.HENSHIN_SERVICE_URL:
            return FakeResponse(json_data=fake_henshin_result(False))
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(api.httpx, "post", fake_post)
    result = api.run_assurance_pipeline([henshin_invalid_story])

    assert result["story_count"] == 1
    assert result["json_validation_passed_count"] == 1
    assert result["graph_validation_passed_count"] == 1
    assert result["henshin_validation_passed_count"] == 0
    assert result["stories"][0]["stage"] == "henshin-validation"
    assert result["stories"][0]["graph"] is not None

    graph_json = [c for c in calls["json"] if c["folder"] == "graphs"]
    assert len(graph_json) == 1

    graph_exts = {c["extension"] for c in calls["text"] if c["folder"] == "graphs"}
    assert graph_exts == {"dot", "svg"}

    xmi = [c for c in calls["bytes"] if c["folder"] == "xmi" and c["extension"] == "xmi"]
    assert len(xmi) == 1

def test_successful_story_increments_all_three_counters(monkeypatch, valid_story):
    install_output_spies(monkeypatch)

    def fake_post(url, *, json, timeout):
        if url == api.HENSHIN_XMI_URL:
            return FakeResponse(content=b"<xmi/>")
        if url == api.HENSHIN_SERVICE_URL:
            return FakeResponse(json_data=fake_henshin_result(True))
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(api.httpx, "post", fake_post)
    result = api.run_assurance_pipeline([valid_story])

    assert result["story_count"] == 1
    assert result["json_validation_passed_count"] == 1
    assert result["graph_validation_passed_count"] == 1
    assert result["henshin_validation_passed_count"] == 1
    assert result["stories"][0]["stage"] == "complete"

def test_mixed_batch_counts_each_stage_independently(
    monkeypatch,
    valid_story,
    invalid_schema_story,
    invalid_relation_story,
    henshin_invalid_story,
):
    install_output_spies(monkeypatch)

    valid_story_2 = deepcopy(valid_story)
    valid_story_2["PID"] = "#TEST-VALID-2#"
    henshin_calls = {"count": 0}

    def fake_post(url, *, json, timeout):
        if url == api.HENSHIN_XMI_URL:
            return FakeResponse(content=b"<xmi/>")
        if url == api.HENSHIN_SERVICE_URL:
            henshin_calls["count"] += 1
            valid = henshin_calls["count"] in {1, 3}
            return FakeResponse(json_data=fake_henshin_result(valid))
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(api.httpx, "post", fake_post)

    batch = [
        invalid_schema_story,
        invalid_relation_story,
        valid_story,
        henshin_invalid_story,
        valid_story_2,
    ]
    result = api.run_assurance_pipeline(batch)

    assert result["story_count"] == 5
    assert result["json_validation_passed_count"] == 4
    assert result["graph_validation_passed_count"] == 3
    assert result["henshin_validation_passed_count"] == 2

    assert [s["stage"] for s in result["stories"]] == [
        "json-validation",
        "graph-validation",
        "complete",
        "henshin-validation",
        "complete",
    ]

def test_duplicate_pid_uses_different_output_names(monkeypatch, valid_story):
    calls = install_output_spies(monkeypatch)

    def fake_post(url, *, json, timeout):
        if url == api.HENSHIN_XMI_URL:
            return FakeResponse(content=b"<xmi/>")
        if url == api.HENSHIN_SERVICE_URL:
            return FakeResponse(json_data=fake_henshin_result(True))
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(api.httpx, "post", fake_post)

    api.run_assurance_pipeline([deepcopy(valid_story), deepcopy(valid_story)])

    graph_names = [c["name"] for c in calls["json"] if c["folder"] == "graphs"]
    assert len(graph_names) == 2
    assert graph_names[0] != graph_names[1]
    assert graph_names[0].startswith("001_")
    assert graph_names[1].startswith("002_")
