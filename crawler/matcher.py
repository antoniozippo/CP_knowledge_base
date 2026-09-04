# crawler/matcher.py - Fuzzy match extracted entities vs existing graph

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

ALIASES_PATH = Path("crawler/aliases.yaml")

_DEFAULT_ALIASES = {
    "SLC12A5": ["KCC2"],
    "SCN9A": ["Nav1.7"],
    "SCN10A": ["Nav1.8"],
    "A2BP1": ["Rbfox1"],
    "KALRN": ["Kalirin-7", "Kalirin7"],
    "HMOX1": ["HO-1", "Heme oxygenase-1"],
    "AGER": ["RAGE"],
    "NOS2": ["iNOS", "NOS2"],
    "GJA1": ["Connexin-43", "Cx43"],
    "CACNA1H": ["Cav3.2", "Cav3.2 T-type"],
    "TAC1": ["Substance P", "Substance-P"],
    "TACR1": ["NK1 Receptor", "NK1R", "NK-1"],
    "NLRP3": ["NLRP3 inflammasome"],
    "TNF": ["TNF-alpha", "TNFa", "TNF\u03b1"],
    "TLR4": ["TLR4", "Toll-like receptor 4"],
    "PTGS2": ["COX-2", "COX2"],
    "CALCA": ["CGRP", "\u03b1-CGRP"],
    "TRPV1": ["TRPV1", "VR1"],
    "SCN11A": ["Nav1.9"],
    "KCC2": ["SLC12A5", "KCC2"],
    "RHOA": ["RhoA", "Rho-a"],
    "ROCK1": ["ROCK", "ROCK-I"],
    "ROCK2": ["ROCK-II"],
    "BDNF": ["Brain-derived neurotrophic factor"],
    "NTRK2": ["TrkB", "TrkB receptor"],
    "GAP43": ["GAP-43", "B-50"],
    "MBP": ["Myelin basic protein"],
    "PLP1": ["PLP", "Proteolipid protein"],
    "MAG": ["MAG", "Myelin-associated glycoprotein"],
    "OMG": ["OMgp", "Oligodendrocyte myelin glycoprotein"],
    "LINGO1": ["LINGO-1", "LRR and Ig domain-containing Nogo receptor-interacting protein 1"],
    "RBFOX1": ["Rbfox1", "A2BP1", "Fox-1"],
    "DRGX": ["DRGX", "DRGx", "Prdm12"],
    "ZFHX2": ["ZFHX2"],
    "P2RX4": ["P2X4", "P2X4R"],
    "P2RX7": ["P2X7", "P2X7R"],
    "PANX1": ["Pannexin-1", "Panx1"],
    "GSDMD": ["Gasdermin D", "GSDMD"],
    "CASP1": ["Caspase-1", "Casp1"],
    "IL1B": ["IL-1\u03b2", "IL1beta"],
    "CX3CR1": ["CX3CR1", "CX3C chemokine receptor 1"],
    "CCL2": ["MCP-1", "CCL2", "Monocyte chemoattractant protein-1"],
    "HIF1A": ["HIF-1\u03b1", "HIF1-alpha", "Hypoxia-inducible factor 1-alpha"],
    "VEGFA": ["VEGF", "VEGF-A", "Vascular endothelial growth factor A"],
    "EDN1": ["Endothelin-1", "ET-1"],
    "NFE2L2": ["Nrf2", "NRF2"],
    "PPARG": ["PPAR-\u03b3", "PPARgamma", "Peroxisome proliferator-activated receptor gamma"],
    "CNR2": ["CB2", "CB2 receptor", "Cannabinoid receptor 2"],
    "HDAC1": ["HDAC1"],
    "HDAC3": ["HDAC3"],
    "HDAC4": ["HDAC4"],
    "STAT3": ["STAT3", "Signal transducer and activator of transcription 3"],
    "JAK2": ["JAK2", "Janus kinase 2"],
    "EZH2": ["EZH2", "Enhancer of zeste homolog 2"],
    "METTL3": ["METTL3", "Methyltransferase-like 3"],
    "BRD4": ["BRD4", "Bromodomain-containing protein 4"],
    "RAC1": ["Rac1", "Rac1 GTPase"],
    "CAMK2A": ["CaMKII", "CaMKII\u03b1"],
    "DLG4": ["PSD-95", "PSD95"],
    "ACTA1": ["Cofilin"],
    "LIMK1": ["LIMK", "LIM kinase"],
}


@dataclass
class EntityMatch:
    extracted_name: str
    status: str  # EXACT, FUZZY, ALIAS, NO_MATCH
    matched_node_id: Optional[str] = None
    matched_label: Optional[str] = None
    confidence: float = 0.0


@dataclass
class EdgeMatch:
    subject_id: str
    predicate: str
    object_id: str
    status: str  # EXISTS, INVERSE, NEW
    existing_edge_index: Optional[int] = None
    confidence: float = 0.0


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

        # Build lookup: (source_id, target_id, relation) → link index
        self.edge_index: dict[tuple[str, str, str], list[int]] = {}
        for i, link in enumerate(self.links):
            key = (link.get("source", ""), link.get("target", ""), link.get("relation", ""))
            self.edge_index.setdefault(key, []).append(i)

        self.aliases = self._load_aliases()

    def _load_aliases(self) -> dict[str, list[str]]:
        """Load alias registry. Falls back to built-in defaults if no file exists."""
        if ALIASES_PATH.exists():
            try:
                loaded = yaml.safe_load(ALIASES_PATH.read_text()) or {}
                logger.info("Loaded %d alias entries from %s", len(loaded), ALIASES_PATH)
                return loaded
            except Exception as exc:
                logger.warning("Failed to load aliases from %s: %s", ALIASES_PATH, exc)

        logger.info("Using built-in default aliases (%d entries)", len(_DEFAULT_ALIASES))
        return dict(_DEFAULT_ALIASES)

    def _build_reverse_aliases(self) -> dict[str, str]:
        """Map alias (lowercase) → canonical symbol."""
        reverse: dict[str, str] = {}
        for canonical, alias_list in self.aliases.items():
            reverse[canonical.lower()] = canonical
            if isinstance(alias_list, list):
                for alias in alias_list:
                    reverse[alias.lower()] = canonical
            elif isinstance(alias_list, str):
                reverse[alias_list.lower()] = canonical
        return reverse

    def _match_exact(self, name_lower: str) -> Optional[dict]:
        """Try exact norm_label match."""
        return self.norm_labels.get(name_lower)

    def _match_alias(self, name_lower: str) -> Optional[dict]:
        """Try alias match. Returns matching node or None.

        Checks if the extracted name resolves to a canonical symbol via aliases,
        then finds the best-matching node in the graph.
        """
        rev = self._build_reverse_aliases()
        canonical = rev.get(name_lower)
        if not canonical:
            return None

        canon_lower = canonical.lower()

        # Try exact norm_label match first
        node = self._match_exact(canon_lower)
        if node:
            return node

        # Check if canonical is contained in any norm_label
        for nl, nd in self.norm_labels.items():
            if canon_lower in nl:
                return nd

        return None

    def _match_token_prefix(self, name_lower: str) -> Optional[dict]:
        """Try token-prefix and substring match strategies.

        1. Exact token match: any space-delimited token of name matches a norm_label token
        2. Substring containment: name is contained within a norm_label
        3. Reverse containment: a norm_label token is contained within the name
        """
        name_tokens = name_lower.split()
        if not name_tokens:
            return None

        best_match = None
        best_score = 0

        for nl, node in self.norm_labels.items():
            nl_tokens = nl.split()

            # Strategy 1: exact token overlap (prefix matching)
            for nt in name_tokens:
                for nlt in nl_tokens:
                    if nlt.startswith(nt) and len(nt) >= 3:
                        score = len(nt) / max(len(nl), 1) + 0.1
                        if score > best_score:
                            best_score = score
                            best_match = node
                    elif nt.startswith(nlt) and len(nlt) >= 3:
                        score = len(nlt) / max(len(name_lower), 1) + 0.1
                        if score > best_score:
                            best_score = score
                            best_match = node

            # Strategy 2: name is a substring of norm_label
            if name_lower in nl and len(name_lower) >= 3:
                # Score higher for shorter norm_labels (more specific match)
                score = len(name_lower) / max(len(nl), 1) + 0.3
                if score > best_score:
                    best_score = score
                    best_match = node

            # Strategy 3: a norm_label token matches the name (for parenthetical abbreviations)
            # e.g., norm_label="kcc2 (potassium-chloride cotransporter)" has token "kcc2"
            for nlt in nl_tokens:
                # Strip parentheses content for comparison
                nlt_clean = nlt.strip("()")
                if nlt_clean == name_lower and len(name_lower) >= 2:
                    score = 0.95
                    if score > best_score:
                        best_score = score
                        best_match = node

        return best_match if best_score > 0.3 else None

    def _match_fuzzy(self, name_lower: str, threshold: int = 85) -> Optional[tuple[dict, float]]:
        """Fuzzy match using rapidfuzz. Returns (node, score) or None."""
        if not self.norm_labels:
            return None

        labels_list = list(self.norm_labels.keys())
        best = process.extractOne(
            name_lower,
            labels_list,
            scorer=fuzz.ratio,
            score_cutoff=threshold,
        )

        if best is not None:
            matched_label, score, _ = best
            node = self.norm_labels.get(matched_label)
            if node and score >= threshold:
                return (node, score)

        return None

    def match_entity(self, name: str) -> EntityMatch:
        """Match an extracted entity name against the graph.

        Strategy (ordered):
        1. Exact norm_label match
        2. Alias match (canonical symbol exists in graph)
        3. Token-prefix match
        4. Fuzzy match (rapidfuzz ratio >= 85)
        """
        name_lower = name.strip().lower()
        if not name_lower:
            return EntityMatch(extracted_name=name, status="NO_MATCH", confidence=0.0)

        # 1. Exact match
        exact_node = self._match_exact(name_lower)
        if exact_node:
            return EntityMatch(
                extracted_name=name,
                status="EXACT",
                matched_node_id=exact_node["id"],
                matched_label=exact_node.get("label", ""),
                confidence=1.0,
            )

        # 2. Alias match
        alias_node = self._match_alias(name_lower)
        if alias_node:
            return EntityMatch(
                extracted_name=name,
                status="ALIAS",
                matched_node_id=alias_node["id"],
                matched_label=alias_node.get("label", ""),
                confidence=0.9,
            )

        # 3. Token-prefix match
        prefix_node = self._match_token_prefix(name_lower)
        if prefix_node:
            return EntityMatch(
                extracted_name=name,
                status="FUZZY",
                matched_node_id=prefix_node["id"],
                matched_label=prefix_node.get("label", ""),
                confidence=0.8,
            )

        # 4. Fuzzy match
        fuzzy_result = self._match_fuzzy(name_lower)
        if fuzzy_result:
            fuzzy_node, score = fuzzy_result
            return EntityMatch(
                extracted_name=name,
                status="FUZZY",
                matched_node_id=fuzzy_node["id"],
                matched_label=fuzzy_node.get("label", ""),
                confidence=score / 100.0,
            )

        return EntityMatch(
            extracted_name=name,
            status="NO_MATCH",
            confidence=0.0,
        )

    def match_edge(
        self, subject_id: str, predicate: str, object_id: str
    ) -> EdgeMatch:
        """Match an extracted relationship against existing edges.

        Checks:
        - Exact triple match (source, target, relation)
        - Inverse triple (target, source, same_relation) with opposite sign
        """
        # 1. Exact triple match
        key_forward = (subject_id, object_id, predicate)
        if key_forward in self.edge_index:
            indices = self.edge_index[key_forward]
            return EdgeMatch(
                subject_id=subject_id,
                predicate=predicate,
                object_id=object_id,
                status="EXISTS",
                existing_edge_index=indices[0],
                confidence=1.0,
            )

        # 2. Inverse check: does (target→source, relation) exist?
        key_inverse = (object_id, subject_id, predicate)
        if key_inverse in self.edge_index:
            indices = self.edge_index[key_inverse]
            # Check sign on the existing inverse edge
            existing_link = self.links[indices[0]]
            existing_sign = existing_link.get("sign", 0)
            return EdgeMatch(
                subject_id=subject_id,
                predicate=predicate,
                object_id=object_id,
                status="INVERSE",
                existing_edge_index=indices[0],
                confidence=0.8,
            )

        return EdgeMatch(
            subject_id=subject_id,
            predicate=predicate,
            object_id=object_id,
            status="NEW",
            confidence=0.0,
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
                if subj_match.status == "NO_MATCH" or obj_match.status == "NO_MATCH":
                    continue

                edge = self.match_edge(
                    subj_match.matched_node_id,
                    predicate,
                    obj_match.matched_node_id,
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
        target.write_text(yaml.dump(_DEFAULT_ALIASES, default_flow_style=False, sort_keys=True))
        logger.info("Created default aliases at %s", target)
