# crawler/tests/conftest.py
# Shared fixtures. Tests that need "the real graph" as a baseline get the
# curated graph: graphify-out/graph_v2.json without what the crawler itself added
# (nodes with file_type "crawled", links with origin "auto_crawled", and the
# crawler_evidence on curated links). The live file changes with every crawl, so
# a baseline taken from it would make these tests fail after each merge.

import json
from pathlib import Path

import pytest

LIVE_GRAPH = Path(__file__).resolve().parents[2] / "graphify-out" / "graph_v2.json"


def curated_graph(graph: dict) -> dict:
    """The graph as it was before any crawled content was merged in."""
    links = []
    for link in graph["links"]:
        if link.get("origin") == "auto_crawled":
            continue
        links.append({k: v for k, v in link.items() if k != "crawler_evidence"})
    nodes = [n for n in graph["nodes"] if n.get("file_type") != "crawled"]
    return {**graph, "nodes": nodes, "links": links}


@pytest.fixture(scope="session")
def curated_graph_file(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("curated") / "graph_v2.json"
    path.write_text(json.dumps(curated_graph(json.loads(LIVE_GRAPH.read_text()))))
    return path
