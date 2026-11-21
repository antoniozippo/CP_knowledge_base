# crawler/tests/test_correct_links.py - corrections to wrong crawled relationships

import json

import pytest

from crawler import correct_links as cl


def crawled(s, t, sign, relation="modulates", papers=(("1", "q1"),)):
    ev = [{"pmid": p, "doi": "", "quote": q, "predicate": relation, "sign": sign} for p, q in papers]
    return {"source": s, "target": t, "sign": sign, "relation": relation, "origin": "auto_crawled",
            "source_pmid": papers[0][0], "quote": papers[0][1], "crawler_evidence": ev}


def curated(s, t, sign, relation="activates"):
    return {"source": s, "target": t, "sign": sign, "relation": relation, "source_ref": "note.md"}


def drop(pmid, quote, s, t, sign):
    return {"pmid": pmid, "quote": quote, "action": "drop", "graph_was": {"source": s, "target": t},
            "was": {"subject": s, "predicate": "modulates", "object": t, "sign": sign}}


def replace(pmid, quote, s, t, sign, ns, nt, nsign, relation="modulates"):
    return {"pmid": pmid, "quote": quote, "action": "replace", "graph_was": {"source": s, "target": t},
            "was": {"subject": s, "predicate": relation, "object": t, "sign": sign},
            "now": {"subject": ns, "predicate": relation, "object": nt, "sign": nsign},
            "graph": {"source": ns, "target": nt}}


def run(links, listed=(), fixes=(), protect=-1):
    graph, log = cl.correct_graph({"nodes": [], "links": links}, list(listed), list(fixes), protect)
    return graph["links"], log


def ends(links):
    return [(l["source"], l["target"], l["sign"]) for l in links]


def test_dropping_a_links_only_paper_removes_the_link():
    links, _ = run([crawled("sp", "np", 0), crawled("a", "b", 1)], [drop("1", "q1", "sp", "np", 0)])
    assert ends(links) == [("a", "b", 1)]


def test_dropping_the_primary_paper_promotes_the_next_one():
    link = crawled("nkcc1", "kcc2", -1, papers=(("1", "q1"), ("2", "q2")))
    (l,), _ = run([link], [drop("1", "q1", "nkcc1", "kcc2", -1)])
    assert l["source_pmid"] == "2" and l["quote"] == "q2" and [e["pmid"] for e in l["crawler_evidence"]] == ["2"]


def test_a_reversed_paper_joins_the_existing_reverse_link_and_its_old_link_keeps_the_rest():
    links = [crawled("trpv1", "tnf", 1, papers=(("1", "q1"), ("2", "q2"))), crawled("tnf", "trpv1", 1, "upregulates", (("3", "q3"),))]
    out, log = run(links, [replace("1", "q1", "trpv1", "tnf", 1, "tnf", "trpv1", 1)])
    assert ends(out) == [("trpv1", "tnf", 1), ("tnf", "trpv1", 1)]
    assert [e["pmid"] for e in out[0]["crawler_evidence"]] == ["2"] and out[0]["source_pmid"] == "2"
    assert [e["pmid"] for e in out[1]["crawler_evidence"]] == ["3", "1"] and log[0][0] == "join"


def test_a_links_only_paper_is_rewritten_in_place_when_no_corrected_link_exists():
    out, log = run([crawled("tlr4", "microglia", 0, "expresses")],
                   [replace("1", "q1", "tlr4", "microglia", 0, "microglia", "tlr4", 0, "expresses")])
    assert ends(out) == [("microglia", "tlr4", 0)] and log[0][0] == "rewrite"
    assert out[0]["crawler_evidence"][0]["corrected"]


def test_a_paper_split_off_a_shared_link_gets_a_new_crawled_link():
    link = crawled("a", "b", 1, papers=(("1", "q1"), ("2", "q2")))
    out, log = run([link], [replace("2", "q2", "a", "b", 1, "b", "a", 1)])
    assert ends(out) == [("a", "b", 1), ("b", "a", 1)]
    new = out[1]
    assert new["origin"] == "auto_crawled" and new["validation_status"] == "UNREVIEWED"
    assert new["source_pmid"] == "2" and new["quote"] == "q2" and log[0][0] == "new"


def test_the_sign_rule_moves_every_paper_and_removes_the_emptied_link():
    # five papers all say "loss of Nav1.7 causes CIP"; the verb made the link +1
    papers = tuple((str(i), f"q{i}") for i in range(5))
    out, _ = run([crawled("nav17", "cip", 1, "causes", papers)],
                 fixes=[(p, q, 1, "modulates", -1) for p, q in papers])
    (l,) = out
    assert ends(out) == [("nav17", "cip", -1)] and l["relation"] == "modulates"
    assert sorted(e["pmid"] for e in l["crawler_evidence"]) == ["0", "1", "2", "3", "4"]
    assert all(e["sign"] == -1 for e in l["crawler_evidence"])


def test_a_corrected_paper_joins_a_curated_link_as_evidence():
    out, _ = run([crawled("p2x7", "pain", -1, "prevents"), curated("p2x7", "pain", 1)], fixes=[("1", "q1", -1, "modulates", 1)])
    assert ends(out) == [("p2x7", "pain", 1)] and out[0]["source_ref"] == "note.md"
    assert [e["pmid"] for e in out[0]["crawler_evidence"]] == ["1"]


def test_corrections_are_idempotent():
    links = [crawled("trpv1", "tnf", 1, papers=(("1", "q1"), ("2", "q2"))), crawled("sp", "np", 0, papers=(("5", "q5"),)),
             crawled("x", "y", 1, "causes", (("7", "q7"),))]
    listed = [replace("1", "q1", "trpv1", "tnf", 1, "tnf", "trpv1", 1), drop("5", "q5", "sp", "np", 0)]
    fixes = [("7", "q7", 1, "modulates", -1)]
    once, _ = run(links, listed, fixes)
    twice, log = run(once, listed, fixes)
    assert twice == once and log == []


def test_a_listed_correction_only_touches_the_named_link():
    # the same paper and quote back an unrelated link, which stays
    links = [crawled("sp", "np", 0), crawled("cgrp", "np", 0)]
    out, _ = run(links, [drop("1", "q1", "sp", "np", 0)])
    assert ends(out) == [("cgrp", "np", 0)]


def test_links_the_conflict_log_points_at_are_never_removed():
    with pytest.raises(ValueError, match="conflicts.yaml"):
        run([crawled("sp", "np", 0)], [drop("1", "q1", "sp", "np", 0)], protect=0)


def test_the_extraction_file_is_corrected_once(tmp_path):
    rel = {"subject": "TRPV1", "predicate": "modulates", "object": "TNF-alpha", "sign": 1, "evidence_quote": "q1"}
    other = {"subject": "A", "predicate": "binds", "object": "B", "sign": 0, "evidence_quote": "q9"}
    (tmp_path / "1.json").write_text(json.dumps({"pmid": "1", "relationships": [rel, other]}))
    (tmp_path / "2.json").write_text(json.dumps({"pmid": "2", "relationships": [dict(rel, evidence_quote="q2")]}))
    corr = [{"pmid": "1", "quote": "q1", "action": "replace", "was": {k: rel[k] for k in cl.FIELDS},
             "now": {"subject": "TNF-alpha", "predicate": "modulates", "object": "TRPV1", "sign": 1}},
            {"pmid": "2", "quote": "q2", "action": "drop", "was": {k: rel[k] for k in cl.FIELDS}}]
    assert cl.correct_extraction_files(corr, tmp_path) == {"applied": ["1", "2"]}
    assert cl.correct_extraction_files(corr, tmp_path) == {"done": ["1", "2"]}
    one = json.loads((tmp_path / "1.json").read_text())["relationships"]
    assert one[0]["subject"] == "TNF-alpha" and one[1] == other
    assert json.loads((tmp_path / "2.json").read_text())["relationships"] == []


def test_sign_rule_fixes_skip_quotes_that_back_several_relationships(tmp_path):
    rels = [{"subject": "A", "predicate": "causes", "object": "B", "sign": -1, "evidence_quote": "shared"},
            {"subject": "A", "predicate": "causes", "object": "C", "sign": 1, "evidence_quote": "shared"},
            {"subject": "D", "predicate": "prevents", "object": "E", "sign": 1, "evidence_quote": "alone"}]
    (tmp_path / "9.json").write_text(json.dumps({"pmid": "9", "relationships": rels}))
    assert cl.sign_rule_fixes(tmp_path) == [("9", "alone", -1, "modulates", 1)]
