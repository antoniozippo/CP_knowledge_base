# crawler/tests/test_discovery.py - MeSH discovery threshold

import yaml

from crawler.discovery import MeshDiscovery


def test_default_threshold_is_twenty_papers(tmp_path):
    themes = tmp_path / "themes.yaml"
    themes.write_text(yaml.safe_dump({"T01": {"name": "t", "mesh_terms": ["Neuralgia"]}}))
    papers = (
        [{"pmid": f"a{i}", "mesh_terms": ["Microglia", "Neuralgia"]} for i in range(20)]
        + [{"pmid": f"b{i}", "mesh_terms": ["Astrocytes"]} for i in range(19)]
    )
    found = {t.mesh_term: t.frequency for t in MeshDiscovery(themes_path=str(themes)).discover(papers)}
    assert found == {"Microglia": 20}  # Astrocytes at 19 papers, Neuralgia already registered
