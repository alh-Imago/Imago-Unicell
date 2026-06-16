"""
concept_inference.py — Bridge Inference Engine

Finds the highest-confidence path between any two concepts in the
concept graph using a modified Dijkstra algorithm that maximises
the product of mechanism confidence scores along the path.

Map routing analogy: edge weight = -log(confidence) so that
maximising confidence product = minimising sum of weights.
Same algorithm, different objective.

Three outputs per query:
  GREEN  — direct declared mechanism (confidence ≥ 0.80)
  AMBER  — path via intermediate concepts (confidence product shown)
  RED    — no path found; returns dimensional constraints for
           what a bridging mechanism would need to look like

Usage:
  engine = InferenceEngine("concept_graph.db")
  result = engine.find("temperature", "melting_temperature")
  result = engine.find("mass", "activation_energy")
  result = engine.find("displacement", "wave_function")  # quantum gap

  # Precompute all pairs
  engine.precompute_all()
  engine.save_cache("path_cache.json")
"""

import sqlite3
import json
import math
import heapq
from dataclasses import dataclass, field
from typing import Optional

DB_PATH = "concept_graph.db"


# ── Data classes ──────────────────────────────────────────────────────────

@dataclass
class Concept:
    id:          str
    name:        str
    domain:      str
    unit:        str
    dimension:   list
    description: str
    uses:        int   # how many equations use this concept

@dataclass
class Mechanism:
    """A declared conversion between two concepts."""
    from_id:        str
    to_id:          str
    from_name:      str
    to_name:        str
    equation_name:  str
    formula:        str
    domain:         str
    confidence:     float   # from equation.confidence_max
    bidirectional:  bool = True  # most physical laws work both ways

@dataclass
class PathResult:
    found:       bool
    path:        list        # [concept_name, ...]
    path_ids:    list        # [concept_id, ...]
    mechanisms:  list        # [mechanism descriptions]
    confidence:  float       # product of all step confidences
    hops:        int
    colour:      str         # GREEN / AMBER / RED
    note:        str
    gap_shape:   Optional[dict] = None  # for RED: what a bridge needs to look like


# ── Engine ────────────────────────────────────────────────────────────────

class InferenceEngine:

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.concepts:   dict[str, Concept]   = {}   # id → Concept
        self.by_name:    dict[str, str]        = {}   # name → id
        self.mechanisms: dict[str, list]       = {}   # concept_id → [Mechanism]
        self._cache:     dict[str, PathResult] = {}   # "A→B" → PathResult
        self._load()

    def _load(self):
        conn = sqlite3.connect(self.db_path)
        cur  = conn.cursor()

        # Load concepts
        rows = cur.execute("""
            SELECT c.id, c.name, c.domain_id, c.unit_id,
                   c.dimension, c.description,
                   COUNT(ec.id) as uses
            FROM concepts c
            LEFT JOIN equation_components ec ON ec.concept_id = c.id
            GROUP BY c.id
        """).fetchall()

        for r in rows:
            cid, name, domain, unit, dim_json, desc, uses = r
            dim = json.loads(dim_json) if dim_json else []
            c = Concept(cid, name, domain or "", unit or "",
                       dim, desc or "", uses)
            self.concepts[cid]   = c
            self.by_name[name]   = cid
            # Also index by partial name for fuzzy lookup
            for part in name.split("_"):
                if len(part) > 3 and part not in self.by_name:
                    self.by_name[part] = cid

        # Build mechanism graph from equation components
        # Two concepts are connected if they appear in the same equation
        eq_concepts = cur.execute("""
            SELECT ec.equation_id, ec.concept_id, ec.role,
                   e.display_name, e.formula, e.domain_id,
                   e.confidence_max
            FROM equation_components ec
            JOIN equations e ON ec.equation_id = e.id
            WHERE ec.role IN ('input', 'output')
        """).fetchall()

        # Group by equation
        eq_map: dict[str, dict] = {}
        for eq_id, cid, role, name, formula, domain, conf in eq_concepts:
            if eq_id not in eq_map:
                eq_map[eq_id] = {
                    "name": name, "formula": formula,
                    "domain": domain, "confidence": conf or 1.0,
                    "inputs": [], "outputs": []
                }
            if role == "input":
                eq_map[eq_id]["inputs"].append(cid)
            else:
                eq_map[eq_id]["outputs"].append(cid)

        # Create mechanisms: input concepts → output concepts
        for eq_id, eq in eq_map.items():
            all_cids = eq["inputs"] + eq["outputs"]
            conf     = eq["confidence"]
            # Connect every pair of concepts in this equation
            for i, c1 in enumerate(all_cids):
                for c2 in all_cids[i+1:]:
                    if c1 == c2:
                        continue
                    n1 = self.concepts.get(c1)
                    n2 = self.concepts.get(c2)
                    if not n1 or not n2:
                        continue
                    m = Mechanism(
                        from_id=c1, to_id=c2,
                        from_name=n1.name, to_name=n2.name,
                        equation_name=eq["name"],
                        formula=eq["formula"],
                        domain=eq["domain"],
                        confidence=conf,
                        bidirectional=True
                    )
                    self.mechanisms.setdefault(c1, []).append(m)
                    # Reverse direction
                    m_rev = Mechanism(
                        from_id=c2, to_id=c1,
                        from_name=n2.name, to_name=n1.name,
                        equation_name=eq["name"],
                        formula=eq["formula"],
                        domain=eq["domain"],
                        confidence=conf,
                        bidirectional=True
                    )
                    self.mechanisms.setdefault(c2, []).append(m_rev)

        conn.close()
        print(f"Loaded: {len(self.concepts)} concepts, "
              f"{sum(len(v) for v in self.mechanisms.values())} mechanism edges")

    def resolve(self, name_or_id: str) -> Optional[str]:
        """Resolve a concept name or partial name to a concept ID."""
        name = name_or_id.lower().strip()
        # Exact ID
        if name_or_id in self.concepts:
            return name_or_id
        # Exact name
        for cid, c in self.concepts.items():
            if c.name.lower() == name:
                return cid
        # Starts with
        for cid, c in self.concepts.items():
            if c.name.lower().startswith(name):
                return cid
        # Contains
        for cid, c in self.concepts.items():
            if name in c.name.lower():
                return cid
        return None

    def find(self, a: str, b: str,
             min_confidence: float = 0.0,
             max_hops: int = 8) -> PathResult:
        """
        Find the highest-confidence path between concept a and concept b.

        Uses modified Dijkstra where edge weight = -log(confidence),
        so maximising confidence product = minimising total weight.

        Args:
            a: concept name or ID
            b: concept name or ID
            min_confidence: discard paths below this threshold
            max_hops: maximum path length to consider

        Returns:
            PathResult with colour GREEN/AMBER/RED
        """
        aid = self.resolve(a)
        bid = self.resolve(b)

        if not aid:
            return PathResult(False, [], [], [], 0.0, 0, "RED",
                            f"Concept not found: '{a}'")
        if not bid:
            return PathResult(False, [], [], [], 0.0, 0, "RED",
                            f"Concept not found: '{b}'")
        if aid == bid:
            ca = self.concepts[aid]
            return PathResult(True, [ca.name], [aid], [], 1.0, 0,
                            "GREEN", "Same concept")

        cache_key = f"{aid}→{bid}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # ── Dijkstra on -log(confidence) ─────────────────────────────────
        # Priority queue: (neg_log_conf, concept_id, path_ids, mechanisms)
        INF = float('inf')
        best = {cid: INF for cid in self.concepts}
        best[aid] = 0.0

        # heap: (cost, id, path_ids, mechanism_list)
        heap = [(0.0, 0, aid, [aid], [])]
        counter = 0

        while heap:
            cost, _, cur_id, path, mechs = heapq.heappop(heap)

            if cur_id == bid:
                # Reconstruct result
                conf_product = math.exp(-cost)
                path_names   = [self.concepts[cid].name for cid in path]
                hops         = len(path) - 1

                if hops == 1 and conf_product >= 0.80:
                    colour = "GREEN"
                    note   = f"Direct declared mechanism — {mechs[0]['equation']}"
                elif hops == 1:
                    colour = "AMBER"
                    note   = f"Direct mechanism but confidence {conf_product:.2f} below threshold"
                elif conf_product >= 0.60:
                    colour = "AMBER"
                    note   = f"{hops}-hop path, aggregate confidence {conf_product:.2f}"
                else:
                    colour = "RED"
                    note   = f"{hops}-hop path but confidence too low ({conf_product:.2f})"

                result = PathResult(
                    found=True,
                    path=path_names,
                    path_ids=path,
                    mechanisms=mechs,
                    confidence=round(conf_product, 4),
                    hops=hops,
                    colour=colour,
                    note=note
                )
                self._cache[cache_key] = result
                self._cache[f"{bid}→{aid}"] = result  # symmetric
                return result

            if cost > best[cur_id] + 1e-9:
                continue

            if len(path) > max_hops:
                continue

            for mech in self.mechanisms.get(cur_id, []):
                nid   = mech.to_id
                ncost = cost - math.log(max(mech.confidence, 0.001))
                if ncost < best.get(nid, INF):
                    best[nid] = ncost
                    counter += 1
                    heapq.heappush(heap, (
                        ncost, counter, nid, path + [nid],
                        mechs + [{
                            "equation":   mech.equation_name,
                            "formula":    mech.formula,
                            "domain":     mech.domain,
                            "confidence": mech.confidence,
                            "from":       mech.from_name,
                            "to":         mech.to_name,
                        }]
                    ))

        # No path found — return RED with gap shape
        ca = self.concepts[aid]
        cb = self.concepts[bid]
        gap_shape = {
            "from_concept":    ca.name,
            "from_domain":     ca.domain,
            "from_dimension":  ca.dimension,
            "to_concept":      cb.name,
            "to_domain":       cb.domain,
            "to_dimension":    cb.dimension,
            "dim_match":       ca.dimension == cb.dimension,
            "note": (
                "Dimensions match — a direct bridge is dimensionally possible. "
                "Declare a ConversionMechanism with formula and confidence."
                if ca.dimension == cb.dimension else
                "Dimensions differ — a bridge would require unit conversion "
                f"from {ca.unit or '?'} to {cb.unit or '?'}. "
                "Check whether a scaling factor or derived quantity connects them."
            )
        }

        result = PathResult(
            found=False,
            path=[ca.name, cb.name],
            path_ids=[aid, bid],
            mechanisms=[],
            confidence=0.0,
            hops=-1,
            colour="RED",
            note=f"No path found between '{ca.name}' and '{cb.name}'",
            gap_shape=gap_shape
        )
        self._cache[cache_key] = result
        self._cache[f"{bid}→{aid}"] = result
        return result

    def find_all_paths(self, a: str, b: str,
                       max_hops: int = 6,
                       top_n: int = 5) -> list[PathResult]:
        """
        Find the best path between a and b.
        Returns a list for API compatibility.
        Multi-path search on dense graphs is future work.
        """
        r = self.find(a, b, max_hops=max_hops)
        return [r] if r.found else []


    def precompute_all(self, max_hops: int = 6) -> dict:
        """
        Precompute best paths for all concept pairs.
        Returns the cache dict. Use save_cache() to persist.
        """
        ids = list(self.concepts.keys())
        total = len(ids) * (len(ids) - 1) // 2
        done  = 0
        print(f"Precomputing {total} pairs...")

        for i, aid in enumerate(ids):
            for bid in ids[i+1:]:
                cache_key = f"{aid}→{bid}"
                if cache_key not in self._cache:
                    self.find(
                        self.concepts[aid].name,
                        self.concepts[bid].name,
                        max_hops=max_hops
                    )
                done += 1
                if done % 1000 == 0:
                    pct = done / total * 100
                    print(f"  {done}/{total} ({pct:.0f}%)")

        print(f"Done. {len(self._cache)} cache entries.")
        return self._cache

    def save_cache(self, path: str = "path_cache.json"):
        """Serialise the path cache to JSON."""
        serialisable = {}
        for key, r in self._cache.items():
            serialisable[key] = {
                "found":      r.found,
                "path":       r.path,
                "mechanisms": r.mechanisms,
                "confidence": r.confidence,
                "hops":       r.hops,
                "colour":     r.colour,
                "note":       r.note,
                "gap_shape":  r.gap_shape,
            }
        with open(path, "w") as f:
            json.dump(serialisable, f, indent=2)
        print(f"Saved {len(serialisable)} paths to {path}")

    def summary(self, result: PathResult) -> str:
        """Human-readable summary of a PathResult."""
        col_sym = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴"}.get(result.colour, "⚪")
        if not result.found:
            s = f"{col_sym} NO PATH\n"
            s += f"   {result.note}\n"
            if result.gap_shape:
                g = result.gap_shape
                s += f"   Gap: [{g['from_domain']}]{g['from_concept']} → "
                s += f"[{g['to_domain']}]{g['to_concept']}\n"
                s += f"   Dims: {g['from_dimension']} → {g['to_dimension']}\n"
                s += f"   {g['note']}\n"
            return s

        s  = f"{col_sym} {result.colour}  confidence={result.confidence:.3f}  "
        s += f"hops={result.hops}\n"
        s += f"   Path: {' → '.join(result.path)}\n"
        for i, m in enumerate(result.mechanisms):
            s += f"   Step {i+1}: {m['from']} → {m['to']}\n"
            s += f"           via {m['equation']}  ({m['formula']})  "
            s += f"conf={m['confidence']}\n"
        return s


# ── Demo ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = InferenceEngine()
    print()

    queries = [
        # Expected GREEN — direct declared mechanism
        ("temperature",        "thermal_energy",      "Direct thermo"),
        ("mass",               "kinetic_energy",       "KE = ½mv²"),
        ("frequency",          "photon_energy",        "E = hf"),

        # Expected AMBER — path via intermediates
        ("temperature",        "reaction_rate",        "Arrhenius chain"),
        ("mass",               "hawking_temperature",  "Hawking via grav mass"),
        ("displacement",       "wavelength",           "Wave-particle"),
        ("temperature",        "gibbs_energy",         "Thermo → chemistry"),

        # Expected RED — knowledge holes
        ("melting_temperature","kinetic_energy",       "Genomics → mechanics gap"),
        ("base_count",         "thermal_energy",       "DNA → heat gap"),
        ("gc_content",         "pressure",             "Genomics → fluids gap"),
    ]

    print("=" * 65)
    print("BRIDGE INFERENCE ENGINE — path finder demo")
    print("=" * 65)

    for a, b, label in queries:
        print(f"\n── {label}")
        print(f"   Query: {a} → {b}")
        result = engine.find(a, b)
        print(engine.summary(result))

    print("\n── Top 3 paths: mass → melting_temperature")
    paths = engine.find_all_paths("mass", "melting_temperature", top_n=3)
    for i, p in enumerate(paths):
        print(f"\n   Path {i+1}: conf={p.confidence:.3f}  hops={p.hops}")
        print(f"   {' → '.join(p.path)}")
