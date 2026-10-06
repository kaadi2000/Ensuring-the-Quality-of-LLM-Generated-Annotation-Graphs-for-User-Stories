from validators.json_validator import JsonValidator

def test_valid_story_passes_json_validation(valid_story):
    result = JsonValidator().validate([valid_story])
    assert result["valid"] is True
    assert result["error_count"] == 0

def test_missing_required_field_fails_json_validation(invalid_schema_story):
    result = JsonValidator().validate([invalid_schema_story])
    assert result["valid"] is False
    assert result["error_count"] >= 1
