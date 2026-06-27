# -*- coding: utf-8 -*-
"""
forge-data core — BM25 search engine over curated 3D production datasets.

Pure stdlib. No network calls. Windows: use `python`, not `python3`.

Changes vs atelier-data upstream:
- tokenize() keeps len >= 2 so "uv", "3d", "ao", "gi", "lm", "ue", "vr", "ar" all match.
- Domains scoped to 3D production: tools, polycount, texel, format, material, gotchas.
- Stdlib only; utf-8-sig CSV reads; UTF-8 stdout wrapper at call site.
"""

import csv
import re
from pathlib import Path
from math import log
from collections import defaultdict

# ============ CONFIGURATION ============
DATA_DIR = Path(__file__).parent.parent / "data"
MAX_RESULTS = 3

CSV_CONFIG = {
    "tools": {
        "file": "tool-cheatsheet.csv",
        "search_cols": ["tool", "when_to_use", "headless_invocation", "gotcha"],
        "output_cols": ["tool", "headless_invocation", "when_to_use", "gotcha"],
    },
    "polycount": {
        "file": "polycount-budgets.csv",
        "search_cols": ["asset_class", "platform", "notes"],
        "output_cols": ["asset_class", "platform", "lod0_tris", "lod1_tris", "lod2_tris", "lod3_tris", "notes"],
    },
    "texel": {
        "file": "texel-density.csv",
        "search_cols": ["platform_tier", "asset_tier", "notes"],
        "output_cols": ["platform_tier", "asset_tier", "px_per_m", "texture_for_1m2", "notes"],
    },
    "format": {
        "file": "format-matrix.csv",
        "search_cols": ["format", "best_use", "notes"],
        "output_cols": [
            "format", "carries_geo", "carries_uv", "carries_pbr", "carries_rig",
            "carries_anim", "carries_morph", "up_axis", "unit", "lossy",
            "assimp_import", "assimp_export", "best_use", "notes",
        ],
    },
    "material": {
        "file": "material-presets.csv",
        "search_cols": ["name", "category", "keywords", "notes"],
        "output_cols": ["name", "category", "metallic", "roughness", "base_color_hint", "keywords", "notes"],
    },
    "gotchas": {
        "file": "gotchas.csv",
        "search_cols": ["topic", "symptom", "fix", "applies_to"],
        "output_cols": ["topic", "applies_to", "symptom", "fix"],
    },
}

AVAILABLE_DOMAINS = list(CSV_CONFIG.keys())


# ============ BM25 IMPLEMENTATION ============
class BM25:
    """BM25 ranking — keeps 2-char tokens so 'uv', '3d', 'ao' match."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.corpus: list[list[str]] = []
        self.doc_lengths: list[int] = []
        self.avgdl: float = 0.0
        self.idf: dict[str, float] = {}
        self.doc_freqs: dict[str, int] = defaultdict(int)
        self.N: int = 0

    def tokenize(self, text: str) -> list[str]:
        """Lowercase, split on non-word chars AND underscores, keep tokens of length >= 2.
        Splitting on underscores means 'web_webgl_ar' yields ['web', 'webgl', 'ar'],
        so 2-char domain terms like 'uv', '3d', 'ao', 'gi', 'ar', 'vr' all match."""
        text = re.sub(r'[^\w\s]', ' ', str(text).lower())
        text = text.replace('_', ' ')  # split underscore-joined terms
        return [w for w in text.split() if len(w) >= 2]

    def fit(self, documents: list[str]) -> None:
        self.corpus = [self.tokenize(d) for d in documents]
        self.N = len(self.corpus)
        if not self.N:
            return
        self.doc_lengths = [len(d) for d in self.corpus]
        self.avgdl = sum(self.doc_lengths) / self.N
        for doc in self.corpus:
            seen: set[str] = set()
            for word in doc:
                if word not in seen:
                    self.doc_freqs[word] += 1
                    seen.add(word)
        for word, freq in self.doc_freqs.items():
            self.idf[word] = log((self.N - freq + 0.5) / (freq + 0.5) + 1)

    def score(self, query: str) -> list[tuple[int, float]]:
        q_tokens = self.tokenize(query)
        scores: list[tuple[int, float]] = []
        for idx, doc in enumerate(self.corpus):
            s = 0.0
            dl = self.doc_lengths[idx]
            tfs: dict[str, int] = defaultdict(int)
            for w in doc:
                tfs[w] += 1
            for token in q_tokens:
                if token in self.idf:
                    tf = tfs[token]
                    num = tf * (self.k1 + 1)
                    den = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                    s += self.idf[token] * num / den
            scores.append((idx, s))
        return sorted(scores, key=lambda x: x[1], reverse=True)


# ============ CSV HELPERS ============
def _load_csv(filepath: Path) -> list[dict]:
    """Load CSV with utf-8-sig to handle BOM on Windows."""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def _search_csv(
    filepath: Path,
    search_cols: list[str],
    output_cols: list[str],
    query: str,
    max_results: int,
) -> list[dict]:
    if not filepath.exists():
        return []
    data = _load_csv(filepath)
    documents = [
        " ".join(str(row.get(col, "")) for col in search_cols)
        for row in data
    ]
    bm25 = BM25()
    bm25.fit(documents)
    ranked = bm25.score(query)
    results = []
    for idx, score in ranked[:max_results]:
        if score > 0:
            row = data[idx]
            results.append({col: row.get(col, "") for col in output_cols if col in row})
    return results


# ============ DOMAIN DETECTION ============
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "tools": [
        "blender", "openscad", "assimp", "gltf-transform", "gltfpack", "freecad", "cadquery",
        "headless", "cli", "invocation", "command", "export", "convert", "batch", "script",
        "toktx", "ktx2", "render", "bpy", "python",
    ],
    "polycount": [
        "polycount", "polygon", "triangle", "tris", "lod", "budget", "hero", "npc", "character",
        "vehicle", "prop", "environment", "foliage", "mobile", "console", "pc", "aaa", "web",
        "nanite", "imposter", "billboard", "asset class",
    ],
    "texel": [
        "texel", "density", "px/m", "pixel", "texture resolution", "td", "uv utilization",
        "px per meter", "lightmap", "uv channel", "uvmap",
    ],
    "format": [
        "format", "gltf", "glb", "fbx", "obj", "stl", "usd", "usda", "usdc", "abc", "alembic",
        "step", "ply", "collada", "3mf", "interchange", "convert", "axis", "up-axis", "unit",
        "skeleton", "animation", "morph", "pbr", "embed",
    ],
    "material": [
        "material", "pbr", "metallic", "roughness", "base color", "orm", "normal", "emissive",
        "glass", "metal", "steel", "wood", "plastic", "rubber", "concrete", "gold", "copper",
        "principled", "bsdf", "preset", "shading",
    ],
    "gotchas": [
        "gotcha", "fail", "error", "bug", "symptom", "fix", "pitfall", "broken", "mismatch",
        "scale", "eevee", "headless", "windows", "encoding", "utf", "bom", "path", "draco",
        "seam", "artifact", "crash", "silent",
    ],
}


def detect_domain(query: str) -> str:
    query_lower = query.lower()
    scores: dict[str, int] = {}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        scores[domain] = sum(
            1 for kw in keywords
            if re.search(r'\b' + re.escape(kw) + r'\b', query_lower)
        )
    best = max(scores, key=lambda d: scores[d])
    return best if scores[best] > 0 else "gotchas"


# ============ PUBLIC SEARCH API ============
def search(
    query: str,
    domain: str | None = None,
    max_results: int = MAX_RESULTS,
) -> dict:
    """Main search function with auto-domain detection."""
    if domain is None:
        domain = detect_domain(query)

    config = CSV_CONFIG.get(domain)
    if config is None:
        return {"error": f"Unknown domain: '{domain}'. Available: {', '.join(AVAILABLE_DOMAINS)}"}

    filepath = DATA_DIR / config["file"]
    if not filepath.exists():
        return {
            "error": f"Data file not found: {filepath}",
            "domain": domain,
            "hint": "Run from the forge-data scripts/ directory or verify data/ CSVs exist.",
        }

    results = _search_csv(
        filepath, config["search_cols"], config["output_cols"], query, max_results
    )
    return {
        "domain": domain,
        "query": query,
        "file": config["file"],
        "count": len(results),
        "results": results,
    }
