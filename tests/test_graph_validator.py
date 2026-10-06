from validators.graph_validator import GraphValidator

def test_valid_story_passes_graph_validation(valid_story):
    result = GraphValidator().validate([valid_story])
    assert result["valid"] is True
    assert result["error_count"] == 0

def test_unknown_relation_endpoint_fails_graph_validation(invalid_relation_story):
    result = GraphValidator().validate([invalid_relation_story])
    assert result["valid"] is False
    assert result["error_count"] >= 1

def test_entity_targeted_by_multiple_actions_fails_cardinality(cardinality_story):
    result = GraphValidator().validate([cardinality_story])
    assert result["valid"] is False
    assert result["error_count"] >= 1
