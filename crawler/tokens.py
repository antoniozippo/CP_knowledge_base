# crawler/tokens.py - Token normalization for entity matching

import re

# Words that name a class of thing rather than a specific one. They never
# justify a merge on their own ("Zorblax-9 kinase" must not become PKC).
GENERIC_TOKENS = frozenset({
    "protein", "kinase", "receptor", "factor", "pathway", "signaling", "signalling",
    "cell", "neuron", "channel", "transporter", "cotransporter", "enzyme", "gene",
    "expression", "activation", "inhibitor", "antagonist", "agonist", "axis",
    "cascade", "complex", "family", "level", "gtpase",
})
STOPWORDS = frozenset({"of", "for", "and", "the", "in", "by", "to", "with", "via", "a", "an", "on", "or", "as"})
# Fraction of a node's head tokens the extracted name must cover to merge.
MIN_COVERAGE = 0.6
FUZZY_THRESHOLD = 85

_GREEK = str.maketrans({
    "\u03b1": "alpha", "\u03b2": "beta", "\u03b3": "gamma",
    "\u03b4": "delta", "\u03ba": "kappa", "\u03bc": "mu",
})
_TOKEN_RE = re.compile(r"[^\W_]+")
PAREN_GROUP_RE = re.compile(r"\(([^)]*)\)")
DIGITS_RE = re.compile(r"\d+")


def stem(token: str) -> str:
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def content_tokens(text: str) -> frozenset[str]:
    """Lowercased, Greek-spelled-out, plural-stripped tokens minus stopwords."""
    tokens = (stem(t) for t in _TOKEN_RE.findall(text.lower().translate(_GREEK)))
    return frozenset(t for t in tokens if t not in STOPWORDS)


def distinctive_tokens(text: str) -> frozenset[str]:
    """Content tokens minus generic words."""
    return content_tokens(text) - GENERIC_TOKENS


def is_informative(tokens: frozenset[str]) -> bool:
    """Enough signal to merge on; rejects empty sets and lone single letters."""
    return sum(len(t) for t in tokens) >= 3
