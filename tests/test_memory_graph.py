import pytest

from shyftr.graph import GraphEdge, append_graph_edge, graph_context_for, list_graph_edges
from shyftr.layout import init_cell


def test_append_graph_edges_with_provenance_and_rebuild(tmp_path):
    cell = init_cell(tmp_path, "core")
    edge = GraphEdge(
        edge_id="e1",
        source_id="m1",
        target_id="m2",
        edge_type="depends_on",
        provenance={"feedback_id": "f1"},
        reviewer="operator",
    )
    append_graph_edge(cell, edge)
    rows = list_graph_edges(cell)
    assert rows == [edge.to_dict()]
    assert rows[0]["provenance"]["feedback_id"] == "f1"
    assert graph_context_for(cell, ["m1"])["m1"][0]["edge_type"] == "depends_on"


def test_graph_edge_type_filtering(tmp_path):
    cell = init_cell(tmp_path, "core")
    append_graph_edge(cell, GraphEdge("e1", "m1", "m2", "depends_on", {"feedback_id": "f1"}, "operator"))
    append_graph_edge(cell, GraphEdge("e2", "m1", "m3", "contradicted_by", {"feedback_id": "f2"}, "operator"))
    rows = list_graph_edges(cell, edge_type="contradicted_by")
    assert [row["edge_id"] for row in rows] == ["e2"]


def test_invalid_edge_type_rejected(tmp_path):
    init_cell(tmp_path, "core")
    with pytest.raises(ValueError):
        GraphEdge(edge_id="e1", source_id="m1", target_id="m2", edge_type="auto_magic", provenance={}, reviewer="operator")
