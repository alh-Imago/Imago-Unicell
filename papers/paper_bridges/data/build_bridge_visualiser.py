"""
build_bridge_visualiser.py
Regenerates bridge_visualiser.html by replacing the hardcoded
VAR_ALL and DOMAINS data blobs with fresh data from concept_graph.db.

The HTML file is split at the two data lines (102-103 in the original)
and reconstructed with updated JSON.
"""

import sqlite3, json, re
from pathlib import Path

DB   = "concept_graph.db"
SRC  = Path("../bridge_visualiser.html")
OUT  = Path("../bridge_visualiser.html")

# ── Colour palette — extend as new domains are added ─────────────────────────

COLOURS = {
    # Physics subdomains
    "kinematics":       "#00d4ff",
    "dynamics":         "#0099ff",
    "energy_domain":    "#ff6600",
    "rotation":         "#ffcc00",
    "gravitation":      "#aa77ff",
    "oscillations":     "#66ffcc",
    "fluids":           "#00ffaa",
    "thermodynamics":   "#ff4455",
    "heat_transfer":    "#ff8888",
    "waves":            "#44ffff",
    "optics":           "#88eeff",
    "electrostatics":   "#ffff44",
    "circuits":         "#ffee44",
    "magnetism":        "#ff88ff",
    "electromagnetism": "#ffaa00",
    "relativity":       "#ff44aa",
    "quantum":          "#cc44ff",
    "nuclear":          "#ff2200",
    "mechanics":        "#5599ff",
    "modern_physics":   "#ff33cc",
    # Chemistry
    "chemistry":        "#88ffcc",
    "chem_kinetics":    "#55ff55",
    "thermochem":       "#99ff44",
    # Biology
    "biology":          "#00ff88",
    "genomics":         "#44ff99",
    "biochemistry":     "#00ff66",
    # Population
    "population_dynamics": "#aaff44",
    # Mathematics
    "mathematics":      "#ffdd88",
    "electoral_systems":"#ffbb55",
    # Economics / Finance
    "economics":        "#ff9944",
    "accounting":       "#ffb366",
    "financial_math":   "#ffd700",
    # Structural Geology
    "structural_geology": "#c8a87a",
    # Physics parent
    "physics":          "#6688ff",
}

conn = sqlite3.connect(DB)
cur  = conn.cursor()

# ── Build VAR_ALL: concepts sorted by connection count desc ──────────────────

hub = {}
edges = cur.execute("""
    SELECT DISTINCT ec1.concept_id, ec2.concept_id
    FROM equation_components ec1
    JOIN equation_components ec2 ON ec1.equation_id = ec2.equation_id
        AND ec1.concept_id != ec2.concept_id
    WHERE ec1.role IN ('input','output') AND ec2.role IN ('input','output')
""").fetchall()
for a, b in edges:
    hub[a] = hub.get(a, 0) + 1
    hub[b] = hub.get(b, 0) + 1

concepts = cur.execute("""
    SELECT c.id, c.name, c.domain_id, c.unit_id, c.dimension
    FROM concepts c ORDER BY c.domain_id, c.name
""").fetchall()

var_all = []
for cid, name, domain, unit, dim_json in concepts:
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
    })

# Sort by uses desc (match original behaviour)
var_all.sort(key=lambda v: -v["uses"])

# ── Build DOMAINS list: display names, sorted ────────────────────────────────

domains_rows = cur.execute(
    "SELECT name FROM domains ORDER BY name"
).fetchall()
domains_list = [r[0] for r in domains_rows]

conn.close()

# ── Read source HTML, replace the two data lines ─────────────────────────────

src = SRC.read_text(encoding="utf-8")

var_json    = json.dumps(var_all, ensure_ascii=False, separators=(',', ':'))
domain_json = json.dumps(domains_list, ensure_ascii=False, separators=(',', ':'))

# Replace DOMAINS line (line starting with "const DOMAINS")
src = re.sub(
    r'^const DOMAINS\s*=\s*\[.*?\];',
    f'const DOMAINS    = {domain_json};',
    src, flags=re.MULTILINE
)

# Replace VAR_ALL line
src = re.sub(
    r'^const VAR_ALL\s*=\s*\[.*?\];',
    f'const VAR_ALL    = {var_json};',
    src, flags=re.MULTILINE
)

OUT.write_text(src, encoding="utf-8")
print(f"Done: {OUT}  ({len(src)//1024}kb)  {len(var_all)} concepts  {len(domains_list)} domains")
