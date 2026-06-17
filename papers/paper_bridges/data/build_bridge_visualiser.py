"""
build_bridge_visualiser.py
Regenerates bridge_visualiser.html by replacing the hardcoded data blobs:
  - DOMAINS    line 102  — list of domain display names
  - VAR_ALL    line 104  — concept list with connection counts
  - CHORD_ALL  line 106  — domain-pair chord data

All three are recomputed from concept_graph.db.
"""

import sqlite3, json, re
from pathlib import Path

DB   = "concept_graph.db"
SRC  = Path("../bridge_visualiser.html")
OUT  = Path("../bridge_visualiser.html")

COLOURS = {
    "kinematics":          "#00d4ff",
    "dynamics":            "#0099ff",
    "energy_domain":       "#ff6600",
    "rotation":            "#ffcc00",
    "gravitation":         "#aa77ff",
    "oscillations":        "#66ffcc",
    "fluids":              "#00ffaa",
    "thermodynamics":      "#ff4455",
    "heat_transfer":       "#ff8888",
    "waves":               "#44ffff",
    "optics":              "#88eeff",
    "electrostatics":      "#ffff44",
    "circuits":            "#ffee44",
    "magnetism":           "#ff88ff",
    "electromagnetism":    "#ffaa00",
    "relativity":          "#ff44aa",
    "quantum":             "#cc44ff",
    "nuclear":             "#ff2200",
    "mechanics":           "#5599ff",
    "modern_physics":      "#ff33cc",
    "chemistry":           "#88ffcc",
    "chem_kinetics":       "#55ff55",
    "thermochem":          "#99ff44",
    "biology":             "#00ff88",
    "genomics":            "#44ff99",
    "biochemistry":        "#00ff66",
    "population_dynamics": "#aaff44",
    "mathematics":         "#ffdd88",
    "electoral_systems":   "#ffbb55",
    "economics":           "#ff9944",
    "accounting":          "#ffb366",
    "financial_math":      "#ffd700",
    "structural_geology":  "#c8a87a",
    "physics":             "#6688ff",
}

conn = sqlite3.connect(DB)
cur  = conn.cursor()

# ── 1. Hub counts (how many equations each concept appears in) ───────────────

hub = {}
edge_rows = cur.execute("""
    SELECT DISTINCT ec1.concept_id, ec2.concept_id
    FROM equation_components ec1
    JOIN equation_components ec2
      ON ec1.equation_id = ec2.equation_id
      AND ec1.concept_id != ec2.concept_id
    WHERE ec1.role IN ('input','output')
      AND ec2.role IN ('input','output')
""").fetchall()
for a, b in edge_rows:
    hub[a] = hub.get(a, 0) + 1
    hub[b] = hub.get(b, 0) + 1

# ── 2. VAR_ALL ───────────────────────────────────────────────────────────────

concepts_raw = cur.execute("""
    SELECT c.id, c.name, c.domain_id, c.unit_id, c.dimension, c.nature
    FROM concepts c ORDER BY c.domain_id, c.name
""").fetchall()

var_all = []
for cid, name, domain, unit, dim_json, nature in concepts_raw:
    try:
        dim = json.loads(dim_json) if dim_json and dim_json.strip() else ""
    except Exception:
        dim = ""
    var_all.append({
        "id":     cid,
        "name":   name,
        "domain": domain or "",
        "unit":   unit or "",
        "dim":    dim,
        "uses":   hub.get(cid, 0),
        "colour": COLOURS.get(domain, "#888888"),
        "nature": nature or "absolute",
    })
var_all.sort(key=lambda v: -v["uses"])

# ── 3. DOMAINS list ──────────────────────────────────────────────────────────

# Only include domains that actually have concepts
domains_with_concepts = {r[0] for r in cur.execute(
    "SELECT DISTINCT domain_id FROM concepts").fetchall()}

domain_display = {r[0]: r[1] for r in cur.execute(
    "SELECT id, name FROM domains").fetchall()}

# Sort by display name for stable ordering
domain_ids_sorted = sorted(domains_with_concepts,
                           key=lambda d: domain_display.get(d, d))
domains_list = [domain_display.get(d, d) for d in domain_ids_sorted]
domain_id_to_idx = {d: i for i, d in enumerate(domain_ids_sorted)}

# ── 4. CHORD_ALL ─────────────────────────────────────────────────────────────
# For each pair of domains (A, B): find concepts from A that share an equation
# with concepts from B. Count distinct shared concepts and list their names.

concept_domain = {r[0]: r[1] for r in cur.execute(
    "SELECT id, domain_id FROM concepts").fetchall()}
concept_name = {r[0]: r[1] for r in cur.execute(
    "SELECT id, name FROM concepts").fetchall()}

# Build: equation_id -> set of concept_ids
eq_concepts = {}
for eq_id, con_id in cur.execute(
        "SELECT equation_id, concept_id FROM equation_components "
        "WHERE role IN ('input','output')").fetchall():
    eq_concepts.setdefault(eq_id, set()).add(con_id)

# For each equation, find all cross-domain concept pairs
pair_vars = {}   # (domA_idx, domB_idx) -> set of concept names
for eq_id, cons in eq_concepts.items():
    cons_list = list(cons)
    for i in range(len(cons_list)):
        for j in range(i + 1, len(cons_list)):
            ca, cb = cons_list[i], cons_list[j]
            da = concept_domain.get(ca)
            db = concept_domain.get(cb)
            if da is None or db is None or da == db:
                continue
            if da not in domain_id_to_idx or db not in domain_id_to_idx:
                continue
            ia, ib = domain_id_to_idx[da], domain_id_to_idx[db]
            if ia > ib:
                ia, ib = ib, ia
                ca, cb = cb, ca
            key = (ia, ib)
            pair_vars.setdefault(key, set()).add(concept_name.get(ca, ca))
            pair_vars.setdefault(key, set()).add(concept_name.get(cb, cb))

chord_all = []
for (ia, ib), var_set in sorted(pair_vars.items()):
    chord_all.append({
        "from":      ia,
        "to":        ib,
        "from_name": domains_list[ia],
        "to_name":   domains_list[ib],
        "count":     len(var_set),
        "vars":      sorted(var_set),
    })

conn.close()

# ── 5. Patch HTML ────────────────────────────────────────────────────────────

src = SRC.read_text(encoding="utf-8")

var_json    = json.dumps(var_all,   ensure_ascii=False, separators=(',', ':'))
domain_json = json.dumps(domains_list, ensure_ascii=False, separators=(',', ':'))
chord_json  = json.dumps(chord_all, ensure_ascii=False, separators=(',', ':'))

src = re.sub(r'^const DOMAINS\s*=\s*\[.*?\];',
             f'const DOMAINS    = {domain_json};',
             src, flags=re.MULTILINE)

src = re.sub(r'^const VAR_ALL\s*=\s*\[.*?\];',
             f'const VAR_ALL    = {var_json};',
             src, flags=re.MULTILINE)

src = re.sub(r'^const CHORD_ALL\s*=\s*\[.*?\];',
             f'const CHORD_ALL  = {chord_json};',
             src, flags=re.MULTILINE)

OUT.write_text(src, encoding="utf-8")

print(f"Done: {OUT}  ({len(src)//1024}kb)")
print(f"  {len(var_all)} concepts")
print(f"  {len(domains_list)} domains: {', '.join(domains_list)}")
print(f"  {len(chord_all)} chord pairs")
# Show nuclear connections specifically
nuclear_chords = [c for c in chord_all if 'Nuclear' in (c['from_name'], c['to_name'])]
print(f"\nNuclear Physics chord connections ({len(nuclear_chords)}):")
for c in sorted(nuclear_chords, key=lambda x: -x['count']):
    other = c['to_name'] if c['from_name'] == 'Nuclear Physics' else c['from_name']
    print(f"  ↔ {other}: {c['count']} vars — {c['vars']}")


# ── 6. Patch hardcoded variable count strings ────────────────────────────────

N = len(var_all)
mid = N // 2

# Dropdown options
src = re.sub(
    r'<option value="0-49">Top 1–50 \(most used, \d+ total\)</option>',
    f'<option value="0-49">Top 1–50 (most used, {N} total)</option>',
    src)
src = re.sub(
    r'<option value="\d+-\d+">51–\d+ \(remaining\)</option>',
    f'<option value="50-{N-1}">51–{N} (remaining)</option>',
    src)
src = re.sub(
    r'<option value="0-\d+">ALL \d+ variables</option>',
    f'<option value="0-{N-1}">ALL {N} variables</option>',
    src)
# Medium band — keep centred
src = re.sub(
    r'<option value="\d+-\d+">26–75 \(medium\)</option>',
    f'<option value="{mid-25}-{mid+24}">26–75 (medium)</option>',
    src)

# Default display — show top 50
src = re.sub(
    r'let aIdx = \[\.\.\.Array\(Math\.min\(\d+,VAR_ALL\.length\)\)\.keys\(\)\];',
    f'let aIdx = [...Array(Math.min(50,VAR_ALL.length)).keys()];',
    src)

OUT.write_text(src, encoding="utf-8")
print(f"  dropdown updated: {N} total variables")


# ── 7. Inject functional family data for BRIDGE TABLE tab ────────────────────

family_rows = conn2.execute("""
    SELECT functional_family,
           COUNT(*) as n_eq,
           COUNT(DISTINCT domain_id) as n_domains,
           GROUP_CONCAT(DISTINCT domain_id) as domains,
           GROUP_CONCAT(id || ':' || name || ':' || domain_id, '|') as equations
    FROM equations
    WHERE functional_family IS NOT NULL AND functional_family != 'other'
    GROUP BY functional_family
    ORDER BY n_domains DESC, n_eq DESC
""").fetchall() if False else []


# ── 8. Inject FAMILY_DATA (functional families) ──────────────────────────────

conn3 = sqlite3.connect(DB)
cur3  = conn3.cursor()

all_domain_ids = sorted({r[0] for r in cur3.execute(
    "SELECT DISTINCT domain_id FROM concepts").fetchall()})

fam_rows = cur3.execute("""
    SELECT functional_family, COUNT(*) as n_eq, COUNT(DISTINCT domain_id) as n_domains,
           GROUP_CONCAT(DISTINCT domain_id) as domains
    FROM equations WHERE functional_family IS NOT NULL AND functional_family != 'other'
    GROUP BY functional_family ORDER BY n_domains DESC, n_eq DESC
""").fetchall()

family_data = []
for fam, n_eq, n_dom, dom_str in fam_rows:
    present = set(dom_str.split(','))
    eqs = cur3.execute(
        "SELECT id,name,formula,domain_id FROM equations WHERE functional_family=? ORDER BY domain_id LIMIT 8",
        (fam,)).fetchall()
    family_data.append({
        "family":fam, "n_eq":n_eq, "n_domains":n_dom,
        "present":sorted(present),
        "missing":sorted(set(all_domain_ids) - present),
        "examples":[{"id":r[0],"name":r[1],"formula":r[2],"domain":r[3]} for r in eqs],
    })
conn3.close()

# Remove any existing FAMILY_DATA lines then inject once after CHORD_ALL
src_lines = src.split('\n')
src = '\n'.join(l for l in src_lines if 'const FAMILY_DATA' not in l)

fam_json = json.dumps(family_data, ensure_ascii=False, separators=(',', ':'))
pos = src.find("const CHORD_ALL")
end = src.find(";", pos) + 1
src = src[:end] + f"\nconst FAMILY_DATA = {fam_json};" + src[end:]

OUT.write_text(src, encoding="utf-8")
print(f"  FAMILY_DATA: {len(family_data)} families injected")
