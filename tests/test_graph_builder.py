from graph.graph_builder import GraphBuilder

def test_builds_one_graph_per_story(valid_story, contains_story):
    graphs = GraphBuilder().build([valid_story, contains_story])
    assert len(graphs) == 2
    assert graphs[0]["pid"] == valid_story["PID"]
    assert graphs[1]["pid"] == contains_story["PID"]

def test_simple_story_graph_contents(valid_story):
    graph = GraphBuilder().build([valid_story])[0]
    assert graph["nodes"]["personas"] == ["user"]
    assert graph["nodes"]["activities"] == ["search"]
    assert graph["nodes"]["entities"] == ["information"]

def test_contains_relation_is_preserved(contains_story):
    graph = GraphBuilder().build([contains_story])[0]
    assert {"source": "order", "target": "item"} in graph["edges"]["contains"]
