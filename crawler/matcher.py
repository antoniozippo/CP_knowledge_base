# crawler/matcher.py - Fuzzy match extracted entities vs existing graph

import json
import logging
import re
from pathlib import Path
from typing import Optional

import yaml
from rapidfuzz import fuzz, process

from crawler.classify import normalize_label
from crawler.default_aliases import DEFAULT_ALIASES
from crawler.records import EdgeMatch, EntityMatch
from crawler.tokens import (
    CLASS_QUALIFIERS,
    DIGITS_RE,
    FUZZY_THRESHOLD,
    GENERIC_TOKENS,
    MIN_COVERAGE,
    PAREN_GROUP_RE,
    content_tokens,
    distinctive_tokens,
    is_informative,
    is_spelling_variant,
    skeleton,
)

logger = logging.getLogger(__name__)

ALIASES_PATH = Path("crawler/aliases.yaml")
CONTEXT_NODES_PATH = Path("crawler/context_nodes.yaml")
NO_MERGE_PATH = Path("crawler/no_merge.yaml")


# a head with one of these words names a group, not a gene: "BCL-2 Family Proteins" is not "Bcl2"
_NOT_A_SYMBOL = frozenset({"family", "complex", "axis", "pathway", "signaling", "signalling", "cascade", "protein"})


def _symbol_forms(name_key: str, owners: dict[str, set[str]]) -> frozenset[str]:
    """Skeletons a one-word name may be a symbol for. A trailing receptor "R" after a digit is
    dropped ("p2x7r" -> "p2x7") only when no node owns the name as written, so "CSF1R" stays
    the receptor and does not become the CSF1 ligand. Empty for a multi-word name."""
    if " " in name_key:
        return frozenset()
    sk = skeleton(name_key)
    if len(sk) >= 3 and sk in owners:
        return frozenset({sk})
    stripped = re.sub(r"(\d[a-z]?)r$", r"\1", sk)
    return frozenset(f for f in {sk, stripped} if len(f) >= 3)


def is_crawled(node: dict) -> bool:
    """A node the crawler created itself (free-text label, never reviewed)."""
    return node.get("file_type") == "crawled"


def _field(obj, name: str, default):
    """Read a field from a pydantic/dataclass object or a plain dict."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class EntityMatcher:
    """Match extracted entities and relationships against the existing knowledge graph."""

    def __init__(self, graph_path: str = "graphify-out/graph_v2.json"):
        graph_file = Path(graph_path)
        if not graph_file.exists():
            raise FileNotFoundError(f"Graph file not found: {graph_path}")

        self.graph = json.loads(graph_file.read_text())
        self.nodes: list[dict] = self.graph.get("nodes", [])
        self.links: list[dict] = self.graph.get("links", [])

        # Curated nodes: lowercased label → node (what the graph stores as norm_label).
        # Auto-crawled nodes: the updater's normalized key → node. They are kept
        # apart so a curated node always wins a collision and the loose rules
        # (token, fuzzy) only ever see curated labels.
        self.context_node_ids = self._load_context_node_ids()
        self._no_merge = self._load_no_merge()
        self.norm_labels: dict[str, dict] = {}
        self._crawled_by_key: dict[str, dict] = {}
        for node in self.nodes:
            nl = node.get("norm_label", "").lower()
            if not nl:
                continue
            if is_crawled(node):
                self._crawled_by_key.setdefault(nl, node)
            else:
                self.norm_labels[nl] = node
        self._loose_labels = [nl for nl, node in self.norm_labels.items()
                              if node["id"] not in self.context_node_ids]

        # Build lookup: node id → node
        self.nodes_by_id: dict[str, dict] = {n["id"]: n for n in self.nodes}

        # Build lookup: (source_id, target_id) → link indices, any relation
        self.pair_index: dict[tuple[str, str], list[int]] = {}
        for i, link in enumerate(self.links):
            pair = (link.get("source", ""), link.get("target", ""))
            self.pair_index.setdefault(pair, []).append(i)

        degree: dict[str, int] = {}
        for link in self.links:
            for end in (link.get("source", ""), link.get("target", "")):
                degree[end] = degree.get(end, 0) + 1
        # id -> (distinctive head tokens, full content-token sets of (...) groups)
        self._forms: dict[str, tuple[frozenset[str], list[frozenset[str]]]] = {}
        # id -> content tokens of the head / of the whole label, generic words kept
        self._head_all: dict[str, frozenset[str]] = {}
        self._label_all: dict[str, frozenset[str]] = {}
        self._head_is_symbol: dict[str, bool] = {}   # head is one word: "KCC2", "IL-1beta"
        # id -> skeletons of the head and of one-word "(...)" groups: "MMP-9" and "MMP9" share "mmp9"
        self._symbols: dict[str, frozenset[str]] = {}
        self._symbol_owners: dict[str, set[str]] = {}
        self._degree = degree
        for node in self.nodes:
            label = node.get("label", "")
            head_text = label.split("(")[0].strip() or label
            parens = [content_tokens(g) for g in PAREN_GROUP_RE.findall(label)]
            self._forms[node["id"]] = (distinctive_tokens(head_text), parens)
            self._head_all[node["id"]] = content_tokens(head_text)
            self._head_is_symbol[node["id"]] = not head_text.strip().count(" ")
            head_symbol = set() if content_tokens(head_text) & _NOT_A_SYMBOL else {skeleton(head_text)}
            symbols = head_symbol | {skeleton(g) for g in PAREN_GROUP_RE.findall(label) if " " not in g.strip()}
            self._symbols[node["id"]] = frozenset(k for k in symbols if len(k) >= 3)
            for k in self._symbols[node["id"]]:
                self._symbol_owners.setdefault(k, set()).add(node["id"])
            self._label_all[node["id"]] = content_tokens(label)

        self.aliases = self._load_aliases()
        self._alias_groups = self._build_alias_groups()

    def _load_context_node_ids(self) -> frozenset[str]:
        """Ids of curated nodes the loose rules must not merge into (context_nodes.yaml)."""
        if not CONTEXT_NODES_PATH.exists():
            return frozenset()
        try:
            loaded = yaml.safe_load(CONTEXT_NODES_PATH.read_text()) or {}
        except Exception as exc:
            logger.warning("Failed to load context nodes from %s: %s", CONTEXT_NODES_PATH, exc)
            return frozenset()
        return frozenset(entry["id"] for entry in loaded.get("context_nodes", []) if entry.get("id"))

    def _load_no_merge(self) -> frozenset[tuple[str, str]]:
        """(name skeleton, node id) pairs the loose rules must not merge (no_merge.yaml): every spelling
        of a listed name is blocked ("IGF1" also blocks "IGF-1")."""
        if not NO_MERGE_PATH.exists():
            return frozenset()
        try:
            loaded = yaml.safe_load(NO_MERGE_PATH.read_text()) or {}
        except Exception as exc:
            logger.warning("Failed to load no-merge pairs from %s: %s", NO_MERGE_PATH, exc)
            return frozenset()
        return frozenset(
            (skeleton(str(name)), entry["node"])
            for entry in loaded.get("no_merge", []) if entry.get("node")
            for name in entry.get("names", [])
        )

    def _load_aliases(self) -> dict[str, list[str]]:
        """Load alias registry. Falls back to built-in defaults if no file exists."""
        if ALIASES_PATH.exists():
            try:
                loaded = yaml.safe_load(ALIASES_PATH.read_text()) or {}
                logger.info("Loaded %d alias entries from %s", len(loaded), ALIASES_PATH)
                return loaded
            except Exception as exc:
                logger.warning("Failed to load aliases from %s: %s", ALIASES_PATH, exc)

        logger.info("Using built-in default aliases (%d entries)", len(DEFAULT_ALIASES))
        return dict(DEFAULT_ALIASES)

    def _build_alias_groups(self) -> dict[str, frozenset[str]]:
        """Map each alias name (lowercase) to its whole alias group.

        Entries that list each other (KCC2 <-> SLC12A5) fall into one group, so
        the registry cannot shadow itself.
        """
        parent: dict[str, str] = {}

        def find(x: str) -> str:
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for canonical, alias_list in self.aliases.items():
            names = [canonical]
            if isinstance(alias_list, list):
                names += alias_list
            elif isinstance(alias_list, str):
                names.append(alias_list)
            roots = [find(n.strip().lower()) for n in names if n and n.strip()]
            for r in roots[1:]:
                parent[find(r)] = find(roots[0])

        groups: dict[str, set[str]] = {}
        for name in list(parent):
            groups.setdefault(find(name), set()).add(name)
        return {name: frozenset(members) for members in groups.values() for name in members}

    def _match_exact(self, name_lower: str) -> Optional[dict]:
        """Exact label match: a curated node by lowercased label, else a crawled
        node by the updater's normalized key (punctuation, synonyms), which is how
        the updater de-duplicates the nodes it creates."""
        return self.norm_labels.get(name_lower) or self._crawled_by_key.get(normalize_label(name_lower))

    def _qualifiers_ok(self, name_tokens: frozenset[str], node: dict) -> bool:
        """False when the name says "receptor", "inhibitor", "antagonist", "agonist",
        "blocker" or "neurons" and the node does not (see CLASS_QUALIFIERS)."""
        for q in name_tokens & CLASS_QUALIFIERS:
            have = self._label_all if q == "receptor" else self._head_all
            if q not in have.get(node["id"], frozenset()):
                return False
        return True

    def _token_candidates(self, name: str) -> list[tuple[tuple, dict]]:
        """Nodes this name may merge into, each with a ranking key.

        Auto-crawled nodes never qualify: their labels are free text, and a short
        name would merge into a longer one ("spinal cord" into "spinal cord
        injury"). They are reached by exact label only. So are the curated nodes
        listed in context_nodes.yaml, whose label carries a context the general name
        lacks ("Cannabidiol (CBD) as PPARγ Agonist"). A node qualifies when the
        name's distinctive tokens sit inside its head
        (the label before the first "(") and cover at least MIN_COVERAGE of it,
        or when the name's tokens, generic words included, equal the content of a
        "(...)" group (a symbol alias such as "(SCN9A)"; "(RhoA Inhibitor)" is
        not an alias of RhoA). Words inside a description never match. Rank: coverage,
        then graph degree, then the shorter label.
        """
        wanted_full = content_tokens(name)
        name_key = name.strip().lower()
        name_skel = skeleton(name_key)
        symbol_forms = _symbol_forms(name_key, self._symbol_owners)
        wanted = wanted_full - GENERIC_TOKENS
        if not is_informative(wanted):
            return []
        found = []
        for node in self.nodes:
            if is_crawled(node) or node["id"] in self.context_node_ids:
                continue
            if (name_skel, node["id"]) in self._no_merge:
                continue
            head, parens = self._forms[node["id"]]
            coverage = 0.0
            if head and wanted <= head:
                coverage = len(wanted) / len(head)
            # A "(...)" group is an alias only when the name is a one-word symbol ("SCN9A",
            # "TNF-alpha") or the label's head is one word and the group its expansion ("KCC2
            # (Potassium-Chloride Cotransporter)"); a phrase matching a descriptive group
            # ("(Neurite Outgrowth)", "(diabetic neuropathy)") is not an alias.
            if wanted_full in parens and (" " not in name_key or self._head_is_symbol[node["id"]]):
                coverage = 1.0
            # a one-word symbol written with other punctuation: "MMP9" for "MMP-9", "VEGF-A" for "VEGFA",
            # "P2X7R" for "P2X7 Receptor"
            if coverage < 1.0 and symbol_forms & self._symbols[node["id"]]:
                coverage = 1.0
            if coverage >= MIN_COVERAGE and self._qualifiers_ok(wanted_full, node):
                key = (coverage, self._degree.get(node["id"], 0), -len(node.get("label", "")))
                found.append((key, node))
        return found

    def _match_alias(self, name_lower: str) -> Optional[dict]:
        """Resolve a name through its alias group to the best graph node."""
        group = self._alias_groups.get(name_lower)
        if not group:
            return None
        found = []
        for member in group | {name_lower}:
            exact = self._match_exact(member)
            if exact:
                found.append(((1.0, self._degree.get(exact["id"], 0), 0), exact))
            found.extend(self._token_candidates(member))
        return max(found, key=lambda kn: kn[0])[1] if found else None

    def _match_token(self, name_lower: str) -> Optional[dict]:
        found = self._token_candidates(name_lower)
        return max(found, key=lambda kn: kn[0])[1] if found else None

    def _match_fuzzy(self, name_lower: str, threshold: int = FUZZY_THRESHOLD) -> Optional[tuple[dict, float]]:
        """Fuzzy match using rapidfuzz, never across differing digits.

        "Caspase-1" and "Caspase-3" score 89 but are different genes.
        """
        if not self._loose_labels:
            return None
        digits = DIGITS_RE.findall(name_lower)
        name_tokens = content_tokens(name_lower)
        name_skeleton = skeleton(name_lower)
        for label, score, _ in process.extract(
            name_lower, self._loose_labels, scorer=fuzz.ratio,
            score_cutoff=threshold, limit=5,
        ):
            node = self.norm_labels[label]
            if DIGITS_RE.findall(label) != digits or not self._qualifiers_ok(name_tokens, node):
                continue
            if (name_skeleton, node["id"]) in self._no_merge:
                continue
            # the ratio only finds candidates; the name must be the label spelled differently
            # ("caspase3" / "Caspase-3"), not a different short identifier ("EP2" / "Tie2")
            if not any(is_spelling_variant(name_skeleton, skeleton(form))
                       for form in (PAREN_GROUP_RE.sub(" ", label), label)):
                continue
            return (node, score)
        return None

    def match_entity(self, name: str) -> EntityMatch:
        """Match an extracted entity name against the graph.

        Strategy (ordered, precision first):
        1. Exact norm_label match
        2. Alias group match
        3. Distinctive-token match (see _token_candidates)
        4. Fuzzy match (rapidfuzz ratio >= 85, digits must agree)
        """
        name_lower = name.strip().lower()
        if not name_lower:
            return EntityMatch(extracted_name=name, status="NO_MATCH", confidence=0.0)

        def matched(status: str, node: dict, confidence: float) -> EntityMatch:
            return EntityMatch(
                extracted_name=name,
                status=status,
                matched_node_id=node["id"],
                matched_label=node.get("label", ""),
                confidence=confidence,
            )

        exact_node = self._match_exact(name_lower)
        if exact_node:
            return matched("EXACT", exact_node, 1.0)

        alias_node = self._match_alias(name_lower)
        if alias_node:
            return matched("ALIAS", alias_node, 0.9)

        token_node = self._match_token(name_lower)
        if token_node:
            return matched("FUZZY", token_node, 0.8)

        fuzzy_result = self._match_fuzzy(name_lower)
        if fuzzy_result:
            fuzzy_node, score = fuzzy_result
            return matched("FUZZY", fuzzy_node, score / 100.0)

        return EntityMatch(extracted_name=name, status="NO_MATCH", confidence=0.0)

    def _pick_edge(self, indices: list[int], predicate: str) -> int:
        """Choose the most informative existing edge between a node pair.

        Prefers an edge with the same predicate, then one that carries a sign,
        then the first edge.
        """
        for i in indices:
            if self.links[i].get("relation") == predicate:
                return i
        for i in indices:
            if self.links[i].get("sign", 0) != 0:
                return i
        return indices[0]

    @staticmethod
    def derive_relation_type(existing_sign: int, new_sign: int) -> str:
        """Classify new evidence against an existing edge by sign.

        CONTRADICTS: both signed, opposite. EXTENDS: existing edge unsigned and
        the evidence adds a direction. CONFIRMS: otherwise (same sign, or the
        evidence is unsigned and only supports that the relationship exists).
        """
        if existing_sign != 0 and new_sign != 0 and existing_sign != new_sign:
            return "CONTRADICTS"
        if existing_sign == 0 and new_sign != 0:
            return "EXTENDS"
        return "CONFIRMS"

    def match_edge(
        self, subject_id: str, predicate: str, object_id: str, **evidence
    ) -> EdgeMatch:
        """Match an extracted relationship against existing edges.

        - EXISTS: an edge subject→object exists (any relation). The predicate
          vocabularies differ (LLM verbs vs. graph relations), so the pair is
          matched and the sign comparison decides CONFIRMS / EXTENDS /
          CONTRADICTS.
        - INVERSE: only object→subject exists; reported but makes no claim
          about the existing edge.
        - NEW: no edge between the pair.
        """
        forward = self.pair_index.get((subject_id, object_id))
        if forward:
            idx = self._pick_edge(forward, predicate)
            link = self.links[idx]
            return EdgeMatch(
                subject_id=subject_id,
                predicate=predicate,
                object_id=object_id,
                status="EXISTS",
                existing_edge_index=idx,
                confidence=1.0 if link.get("relation") == predicate else 0.7,
                relation_type=self.derive_relation_type(
                    link.get("sign", 0), evidence.get("sign", 0)
                ),
                **evidence,
            )

        inverse = self.pair_index.get((object_id, subject_id))
        if inverse:
            return EdgeMatch(
                subject_id=subject_id,
                predicate=predicate,
                object_id=object_id,
                status="INVERSE",
                existing_edge_index=inverse[0],
                confidence=0.8,
                **evidence,
            )

        return EdgeMatch(
            subject_id=subject_id,
            predicate=predicate,
            object_id=object_id,
            status="NEW",
            confidence=0.0,
            **evidence,
        )

    def match_batch(
        self, extractions: list
    ) -> tuple[list[EntityMatch], list[EdgeMatch]]:
        """Match a batch of ExtractionResult objects.

        Args:
            extractions: list of ExtractionResult (or dicts with entities/relationships).

        Returns:
            (entity_matches, edge_matches) tuple.
        """
        entity_matches: list[EntityMatch] = []
        edge_matches: list[EdgeMatch] = []

        # First pass: match all entities, build name → node_id map
        name_to_node: dict[str, EntityMatch] = {}

        for extraction in extractions:
            entities = getattr(extraction, "entities", [])
            for ent in entities:
                ent_name = getattr(ent, "name", None) or ent.get("name", "")
                if not ent_name or ent_name in name_to_node:
                    continue
                match = self.match_entity(ent_name)
                match.entity_type = _field(ent, "entity_type", "")
                match.compartment = _field(ent, "compartment", "")
                match.source_pmid = _field(extraction, "pmid", "")
                match.source_doi = _field(extraction, "doi", "")
                name_to_node[ent_name] = match
                entity_matches.append(match)

        # Second pass: match edges using resolved node IDs
        for extraction in extractions:
            rels = getattr(extraction, "relationships", [])
            for rel in rels:
                subj_name = getattr(rel, "subject", None) or rel.get("subject", "")
                obj_name = getattr(rel, "object", None) or rel.get("object", "")
                predicate = getattr(rel, "predicate", None) or rel.get("predicate", "")

                subj_match = name_to_node.get(subj_name)
                obj_match = name_to_node.get(obj_name)

                if not subj_match or not obj_match:
                    continue
                subj_id, obj_id = subj_match.matched_node_id, obj_match.matched_node_id
                # A relationship with one new endpoint is what links a new
                # entity to the graph, so it is kept; the updater creates the
                # node. Two new endpoints would form an island: dropped.
                if not subj_id and not obj_id:
                    continue

                evidence = dict(
                    sign=_field(rel, "sign", 0),
                    evidence_quote=_field(rel, "evidence_quote", ""),
                    source_pmid=_field(extraction, "pmid", ""),
                    source_doi=_field(extraction, "doi", ""),
                    extraction_confidence=_field(rel, "confidence", ""),
                    subject_name=subj_name,
                    object_name=obj_name,
                )
                if subj_id and obj_id:
                    edge = self.match_edge(subj_id, predicate, obj_id, **evidence)
                else:
                    edge = EdgeMatch(subject_id=subj_id, predicate=predicate, object_id=obj_id,
                                     status="NEW", **evidence)
                edge_matches.append(edge)

        logger.info(
            "Batch match: %d entities (%d exact, %d alias, %d fuzzy, %d no_match), "
            "%d edges (%d exists, %d inverse, %d new)",
            len(entity_matches),
            sum(1 for m in entity_matches if m.status == "EXACT"),
            sum(1 for m in entity_matches if m.status == "ALIAS"),
            sum(1 for m in entity_matches if m.status == "FUZZY"),
            sum(1 for m in entity_matches if m.status == "NO_MATCH"),
            len(edge_matches),
            sum(1 for e in edge_matches if e.status == "EXISTS"),
            sum(1 for e in edge_matches if e.status == "INVERSE"),
            sum(1 for e in edge_matches if e.status == "NEW"),
        )
        return entity_matches, edge_matches


def ensure_aliases(path: Path | None = None):
    """Create a default aliases.yaml if it doesn't exist."""
    target = path or ALIASES_PATH
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.dump(DEFAULT_ALIASES, default_flow_style=False, sort_keys=True))
        logger.info("Created default aliases at %s", target)
