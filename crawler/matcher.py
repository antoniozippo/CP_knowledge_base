# crawler/matcher.py - Fuzzy match extracted entities vs existing graph

import json
import logging
from pathlib import Path
from typing import Optional

import yaml
from rapidfuzz import fuzz, process

from crawler.default_aliases import DEFAULT_ALIASES
from crawler.records import EdgeMatch, EntityMatch
from crawler.tokens import (
    DIGITS_RE,
    FUZZY_THRESHOLD,
    GENERIC_TOKENS,
    MIN_COVERAGE,
    PAREN_GROUP_RE,
    content_tokens,
    distinctive_tokens,
    is_informative,
)

logger = logging.getLogger(__name__)

ALIASES_PATH = Path("crawler/aliases.yaml")


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

        # Build lookup: norm_label (lowercase) → node id
        self.norm_labels: dict[str, dict] = {}
        for node in self.nodes:
            nl = node.get("norm_label", "").lower()
            if nl:
                self.norm_labels[nl] = node

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
        self._degree = degree
        for node in self.nodes:
            label = node.get("label", "")
            head_text = label.split("(")[0].strip() or label
            parens = [content_tokens(g) for g in PAREN_GROUP_RE.findall(label)]
            self._forms[node["id"]] = (distinctive_tokens(head_text), parens)

        self.aliases = self._load_aliases()
        self._alias_groups = self._build_alias_groups()

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
        """Try exact norm_label match."""
        return self.norm_labels.get(name_lower)

    def _token_candidates(self, name: str) -> list[tuple[tuple, dict]]:
        """Nodes this name may merge into, each with a ranking key.

        A node qualifies when the name's distinctive tokens sit inside its head
        (the label before the first "(") and cover at least MIN_COVERAGE of it,
        or when the name's tokens, generic words included, equal the content of a
        "(...)" group (a symbol alias such as "(SCN9A)"; "(RhoA Inhibitor)" is
        not an alias of RhoA). Words inside a description never match. Rank: coverage,
        then graph degree, then the shorter label.
        """
        wanted_full = content_tokens(name)
        wanted = wanted_full - GENERIC_TOKENS
        if not is_informative(wanted):
            return []
        found = []
        for node in self.nodes:
            head, parens = self._forms[node["id"]]
            coverage = 0.0
            if head and wanted <= head:
                coverage = len(wanted) / len(head)
            if wanted_full in parens:
                coverage = 1.0
            if coverage >= MIN_COVERAGE:
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
        if not self.norm_labels:
            return None
        digits = DIGITS_RE.findall(name_lower)
        for label, score, _ in process.extract(
            name_lower, list(self.norm_labels), scorer=fuzz.ratio,
            score_cutoff=threshold, limit=5,
        ):
            if DIGITS_RE.findall(label) == digits:
                return (self.norm_labels[label], score)
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
                if not subj_match.matched_node_id or not obj_match.matched_node_id:
                    continue

                edge = self.match_edge(
                    subj_match.matched_node_id,
                    predicate,
                    obj_match.matched_node_id,
                    sign=_field(rel, "sign", 0),
                    evidence_quote=_field(rel, "evidence_quote", ""),
                    source_pmid=_field(extraction, "pmid", ""),
                    source_doi=_field(extraction, "doi", ""),
                    extraction_confidence=_field(rel, "confidence", ""),
                )
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
