"""
cross_domain.py — Cross-domain concept matching system.

Finds concepts that share dimensional signatures across different domains
and proposes candidate bridges with confidence scoring.

Three match types:
  GREEN  — same domain AND same dimension (identity candidates)
  AMBER  — different domain, same dimension (conversion needed)
  RED    — different domain, compatible but not identical dimension (speculative)

Each match gets a confidence score based on:
  - Dimension exact match
  - Domain proximity (physics↔chemistry closer than physics↔economics)
  - Whether a declared ConversionMechanism exists
  - Hub connectivity (highly connected concepts more likely to bridge)
"""

import sqlite3
import json
from itertools import combinations

DB = "concept_graph.db"

# Domain proximity — how many steps between domains
# Lower = closer = higher base confidence for cross-domain match
DOMAIN_PROXIMITY = {
    ("physics","mechanics"):        0.0,
    ("thermodynamics","chemistry"): 0.1,
    ("physics","chemistry"):        0.15,
    ("chemistry","biology"):        0.2,
    ("physics","biology"):          0.3,
    ("thermodynamics","biology"):   0.25,
    ("physics","economics"):        0.6,
    ("chemistry","economics"):      0.55,
    ("biology","economics"):        0.4,
    ("mathematics","physics"):      0.05,
    ("mathematics","chemistry"):    0.1,
    ("mathematics","biology"):      0.2,
    ("mathematics","economics"):    0.1,
}

# Known cross-domain bridges (declared mechanisms)
KNOWN_BRIDGES = [
    # (from_concept_name, to_concept_name, mechanism, confidence)
    ("activation_energy",   "reaction_rate",     "arrhenius",           1.00),
    ("temperature",         "reaction_rate",     "arrhenius",           1.00),
    ("gravitational_mass",  "hawking_temperature","hawking_radiation",   1.00),
    ("thermal_energy",      "mechanical_work",   "carnot",              0.85),
    ("thermal_energy",      "dimensionless",     "boltzmann_factor",    0.95),
    ("temperature",         "melting_temperature","dna_watson_crick",   0.90),
    ("temperature",         "reaction_rate",     "eyring",              0.92),
    ("gibbs_free_energy",   "equilibrium_constant","thermodynamics",    1.00),
    ("gibbs_free_energy",   "cell_emf",          "electrochemistry",    1.00),
    ("enthalpy",            "reaction_enthalpy", "identity",            1.00),
    ("entropy",             "gibbs_free_energy", "gibbs_helmholtz",     1.00),
    ("kinetic_energy",      "temperature",       "equipartition",       1.00),
    ("photon_energy",       "frequency",         "planck",              1.00),
    ("concentration",       "osmotic_pressure",  "vant_hoff",           1.00),
    ("concentration",       "ph",                "definition",          1.00),
]

def get_domain_proximity(d1, d2):
    """Get proximity score between two domain paths."""
    if d1 == d2:
        return 0.0
    key = tuple(sorted([d1, d2]))
    # Check direct
    if key in DOMAIN_PROXIMITY:
        return DOMAIN_PROXIMITY[key]
    # Check parent domains
    parent_map = {
        "kinematics":"mechanics","dynamics":"mechanics","energy_domain":"mechanics",
        "rotation":"mechanics","gravitation":"mechanics","oscillations":"mechanics",
        "fluids":"mechanics","heat_transfer":"thermodynamics","waves":"physics",
        "optics":"physics","electrostatics":"electromagnetism","circuits":"electromagnetism",
        "magnetism":"electromagnetism","electromagnetism":"physics",
        "relativity":"modern_physics","quantum":"modern_physics","nuclear":"modern_physics",
        "modern_physics":"physics","chem_kinetics":"chemistry","thermochem":"chemistry",
        "genomics":"biology","biochemistry":"biology",
    }
    p1 = parent_map.get(d1, d1)
    p2 = parent_map.get(d2, d2)
    key2 = tuple(sorted([p1, p2]))
    if key2 in DOMAIN_PROXIMITY:
        return DOMAIN_PROXIMITY[key2]
    if p1 == p2:
        return 0.05  # sibling domains
    return 0.5  # unknown proximity

def find_cross_domain_matches():
    conn = sqlite3.connect(DB)
    cur  = conn.cursor()

    # Load all concepts with connection counts
    concepts = cur.execute("""
        SELECT c.id, c.name, c.domain_id, c.unit_id, c.dimension,
               COUNT(ec.id) as conn_count
        FROM concepts c
        LEFT JOIN equation_components ec ON c.id = ec.concept_id
        GROUP BY c.id
        ORDER BY conn_count DESC
    """).fetchall()

    # Build known bridge index
    known_idx = set()
    for b in KNOWN_BRIDGES:
        known_idx.add((b[0], b[1]))
        known_idx.add((b[1], b[0]))

    matches = {"green": [], "amber": [], "red": []}

    for (id1,name1,dom1,unit1,dim1_json,conn1), (id2,name2,dom2,unit2,dim2_json,conn2) in combinations(concepts, 2):
        dim1 = json.loads(dim1_json)
        dim2 = json.loads(dim2_json)

        # Skip dimensionless pairs (too many false positives)
        if dim1 == [0,0,0,0,0,0,0] and dim2 == [0,0,0,0,0,0,0]:
            continue

        # Skip same-name matches
        if name1 == name2:
            continue

        prox = get_domain_proximity(dom1, dom2)
        same_domain = (dom1 == dom2 or prox < 0.06)

        if dim1 == dim2:
            # Check if known bridge exists
            is_known = (name1,name2) in known_idx

            # Confidence: start at 0.5, adjust
            conf = 0.5
            conf += 0.3 * (1 - prox)           # closer domains → higher
            conf += 0.1 * min(conn1,20)/20      # hub nodes → higher
            conf += 0.1 * min(conn2,20)/20
            if is_known:
                conf = min(conf + 0.2, 1.0)
            conf = round(min(conf, 0.99), 2)

            match = {
                "from": name1, "from_domain": dom1, "from_id": id1,
                "to":   name2, "to_domain":   dom2, "to_id":   id2,
                "dimension": dim1,
                "confidence": conf,
                "known_bridge": is_known,
                "from_connections": conn1,
                "to_connections":   conn2,
            }

            if same_domain:
                match["type"] = "green"
                match["note"] = "same domain, same dimension — identity candidate"
                matches["green"].append(match)
            else:
                match["type"] = "amber"
                match["note"] = "cross-domain, same dimension — conversion mechanism needed"
                matches["amber"].append(match)

    # Sort by confidence descending
    for k in matches:
        matches[k].sort(key=lambda x: -x["confidence"])

    conn.close()
    return matches

def print_report(matches):
    print("=" * 70)
    print("CROSS-DOMAIN CONCEPT MATCHING REPORT")
    print("=" * 70)

    print(f"\n🟢 GREEN — Same domain, same dimension ({len(matches['green'])} pairs)")
    print("   Identity candidates — may be aliases or related concepts")
    for m in matches["green"][:15]:
        flag = "✓ known" if m["known_bridge"] else ""
        print(f"   {m['from']:25s} ↔ {m['to']:25s}  [{m['from_domain']}]  conf={m['confidence']}  {flag}")

    print(f"\n🟡 AMBER — Cross-domain, same dimension ({len(matches['amber'])} pairs)")
    print("   Conversion mechanism needed — highest value bridges")
    for m in matches["amber"][:25]:
        flag = "✓ known" if m["known_bridge"] else "⚠ undeclared"
        print(f"   {m['from']:25s} ↔ {m['to']:25s}")
        print(f"   {'':4s}[{m['from_domain']}] → [{m['to_domain']}]  conf={m['confidence']}  {flag}")

    print(f"\n📊 Summary:")
    print(f"   Green (identity candidates): {len(matches['green'])}")
    print(f"   Amber (cross-domain bridges): {len(matches['amber'])}")
    known = sum(1 for m in matches['amber'] if m['known_bridge'])
    undeclared = len(matches['amber']) - known
    print(f"   Amber known:      {known}")
    print(f"   Amber undeclared: {undeclared}  ← knowledge holes")

    return matches

if __name__ == "__main__":
    matches = find_cross_domain_matches()
    print_report(matches)

    # Save for use by explorer
    with open("cross_domain_matches.json", "w") as f:
        json.dump(matches, f, indent=2)
    print(f"\nSaved to cross_domain_matches.json")
