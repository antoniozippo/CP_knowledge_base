# crawler/discovery.py - Adjacent MeSH term discovery

import json
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class DiscoveredTerm(BaseModel):
    mesh_term: str
    frequency: int
    adjacent_themes: list[str] = Field(default_factory=list)
    example_pmids: list[str] = Field(default_factory=list)
    suggested_keywords: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# MeshDiscovery
# ---------------------------------------------------------------------------
class MeshDiscovery:
    def __init__(self, themes_path: str = "crawler/themes.yaml"):
        self.themes_path = Path(themes_path)
        if not self.themes_path.exists():
            log.warning("Themes file not found: %s", self.themes_path)
            self.themes: dict = {}
        else:
            self.themes = yaml.safe_load(self.themes_path.read_text()) or {}
        self.existing_mesh = self._collect_existing_mesh()

    # ------------------------------------------------------------------
    # Theme helpers
    # ------------------------------------------------------------------
    def _collect_existing_mesh(self) -> set[str]:
        """Collect all MeSH terms already in theme registry (lowercased)."""
        mesh: set[str] = set()
        for theme_id, theme in self.themes.items():
            if not isinstance(theme, dict):
                continue
            for term in theme.get("mesh_terms", []):
                mesh.add(term.lower().strip())
        return mesh

    def _theme_ids_for_mesh(self, mesh_term: str) -> list[str]:
        """Return theme IDs whose entity lists contain a token from *mesh_term*."""
        term_lower = mesh_term.lower()
        # Tokenize the MeSH term (e.g. "Matrix Metalloproteinase 9" -> tokens)
        tokens = set(re.findall(r"[a-z0-9]+", term_lower))
        # Remove trivially short tokens
        tokens = {t for t in tokens if len(t) > 2}
        if not tokens:
            return []

        matched: list[str] = []
        for theme_id, theme in self.themes.items():
            if not isinstance(theme, dict):
                continue
            entities_lower = " ".join(
                str(e).lower() for e in theme.get("entities", [])
            )
            mesh_lower = " ".join(
                str(m).lower() for m in theme.get("mesh_terms", [])
            )
            combined = f"{entities_lower} {mesh_lower}"
            # Check if any token from the discovered term overlaps
            if any(tok in combined for tok in tokens):
                matched.append(theme_id)
        return matched

    # ------------------------------------------------------------------
    # Core discovery
    # ------------------------------------------------------------------
    def discover(
        self,
        papers: list,
        min_frequency: int = 3,
    ) -> list[DiscoveredTerm]:
        """Discover new MeSH terms from crawled papers.

        Parameters
        ----------
        papers : list of dicts or PaperMeta
            Papers from a crawl run. Each must have at least ``mesh_terms``
            (list[str]) and ``pmid`` (str).  Accepts both dicts and
            ``PaperMeta`` dataclass instances.
        min_frequency : int
            Minimum number of distinct papers in which a MeSH term must
            appear to be proposed.

        Returns
        -------
        list of DiscoveredTerm
            Sorted by frequency descending.
        """
        # --- Step 1: count MeSH term frequency ----------------------
        mesh_counter: Counter[str] = Counter()
        # Track which papers contain each MeSH term (for PMID examples
        # and adjacency checks).
        mesh_to_pmids: dict[str, set[str]] = defaultdict(set)

        for paper in papers:
            # Support both dict and dataclass
            if isinstance(paper, dict):
                pmid = str(paper.get("pmid", ""))
                mesh_terms = paper.get("mesh_terms", [])
            else:
                pmid = getattr(paper, "pmid", "")
                mesh_terms = getattr(paper, "mesh_terms", [])

            if not mesh_terms:
                continue

            for term in mesh_terms:
                term_clean = term.strip()
                if not term_clean:
                    continue
                mesh_counter[term_clean] += 1
                mesh_to_pmids[term_clean].add(pmid)

        log.info("Observed %d distinct MeSH terms across %d papers", len(mesh_counter), len(papers))

        # --- Step 2: filter -----------------------------------------
        discoveries: list[DiscoveredTerm] = []
        for mesh_term, freq in mesh_counter.most_common():
            if freq < min_frequency:
                break  # Counter is sorted descending; once below threshold, done
            if mesh_term.lower().strip() in self.existing_mesh:
                continue  # already in theme registry

            # --- Step 3: adjacency -----------------------------------
            adjacent_themes = self._theme_ids_for_mesh(mesh_term)

            # --- Step 4: suggested keywords --------------------------
            suggested = self._suggest_keywords(mesh_term)

            # --- Step 5: example PMIDs (up to 5) --------------------
            pmids = sorted(mesh_to_pmids.get(mesh_term, set()))[:5]

            disc = DiscoveredTerm(
                mesh_term=mesh_term,
                frequency=freq,
                adjacent_themes=adjacent_themes,
                example_pmids=pmids,
                suggested_keywords=suggested,
            )
            discoveries.append(disc)

        log.info(
            "Discovered %d new MeSH terms (>= %d papers, not in registry)",
            len(discoveries), min_frequency,
        )
        return discoveries

    # ------------------------------------------------------------------
    # Keyword suggestion heuristic
    # ------------------------------------------------------------------
    @staticmethod
    def _suggest_keywords(mesh_term: str) -> list[str]:
        """Generate plausible search keywords from a MeSH term.

        This is a simple heuristic: combine the MeSH term with
        'neuropathic pain' and 'spinal cord' to produce candidate
        PubMed query phrases.
        """
        base = mesh_term.strip()
        return [
            f"{base} neuropathic pain",
            f"{base} spinal cord pain",
            f"{base} dorsal horn",
            f"{base} microglia",
        ]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save_discoveries(
        self,
        discoveries: list[DiscoveredTerm],
        output_path: str = "crawler/discovered_mesh.yaml",
    ) -> None:
        """Save discoveries to YAML for user review.

        The output file is a YAML list of discovered terms with their
        metadata.  Users can review, edit, and promote terms into
        ``themes.yaml`` manually or via a future CLI command.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        records: list[dict] = []
        for disc in discoveries:
            records.append({
                "mesh_term": disc.mesh_term,
                "frequency": disc.frequency,
                "adjacent_themes": disc.adjacent_themes,
                "example_pmids": disc.example_pmids,
                "suggested_keywords": disc.suggested_keywords,
                "status": "PENDING_REVIEW",
            })

        payload = {
            "generated_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "total_discovered": len(records),
            "terms": records,
        }

        out.write_text(yaml.dump(payload, default_flow_style=False, sort_keys=False, allow_unicode=True))
        log.info("Saved %d discovered terms to %s", len(records), out)
