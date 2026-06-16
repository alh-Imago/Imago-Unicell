"""
build_static_explorer.py
Generates concept_graph_explorer.html — static pre-computed 3D graph.
No force simulation. Positions pre-computed in Python, rendered in JS.
"""
import sqlite3, json, math

DB  = "concept_graph.db"
OUT = "concept_graph_explorer.html"

conn = sqlite3.connect(DB)
cur  = conn.cursor()

concepts = cur.execute("""
    SELECT c.id, c.name, c.domain_id, c.unit_id, c.dimension, c.description
    FROM concepts c ORDER BY c.domain_id, c.name
""").fetchall()

edges_raw = cur.execute("""
    SELECT DISTINCT ec1.concept_id, ec2.concept_id, e.display_name, e.formula
    FROM equation_components ec1
    JOIN equation_components ec2
      ON ec1.equation_id = ec2.equation_id AND ec1.concept_id < ec2.concept_id
    JOIN equations e ON ec1.equation_id = e.id
    WHERE ec1.role IN ('input','output') AND ec2.role IN ('input','output')
""").fetchall()
conn.close()

# Hub counts
hub = {}
for e in edges_raw:
    hub[e[0]] = hub.get(e[0], 0) + 1
    hub[e[1]] = hub.get(e[1], 0) + 1

COLOURS = {
    "kinematics":"#00ccff",   "dynamics":"#3399ff",
    "energy_domain":"#ff7700","rotation":"#ffdd00",
    "gravitation":"#cc99ff",  "oscillations":"#00ffcc",
    "fluids":"#00ffaa",       "thermodynamics":"#ff3355",
    "heat_transfer":"#ff6677","waves":"#33ffff",
    "optics":"#aaeeff",       "electrostatics":"#ffff33",
    "circuits":"#ffee55",     "magnetism":"#ff66ff",
    "electromagnetism":"#ffaa33","relativity":"#ff55bb",
    "quantum":"#cc55ff",      "nuclear":"#ff3300",
    "chem_kinetics":"#55ff55","thermochem":"#99ff44",
    "mechanics":"#5599ff",    "genomics":"#44ff99",
    "biochemistry":"#00ff77", "momentum_domain":"#ffaa00",
    "chemistry":"#88ffcc",
}

# Domain-clustered sphere positions
domains = list(dict.fromkeys(c[2] for c in concepts))
N_dom   = len(domains)
dom_idx = {d: i for i, d in enumerate(domains)}

nodes_data = []
for c in concepts:
    cid, name, domain, unit, dim_json, desc = c
    dim      = json.loads(dim_json) if dim_json else []
    cc       = hub.get(cid, 0)
    d_idx    = dom_idx[domain]
    dom_nodes= [x for x in concepts if x[2] == domain]
    n_idx    = dom_nodes.index(c)
    n_frac   = n_idx / max(len(dom_nodes), 1)
    phi      = math.pi * (0.12 + (d_idx / N_dom) * 0.76)
    theta    = n_frac * math.pi * 2 * 2.618
    phi     += (n_frac - 0.5) * 0.20
    R        = 280
    nodes_data.append({
        "id": cid, "name": name, "domain": domain,
        "unit": unit or "", "dim": dim, "desc": desc or "",
        "connections": cc,
        "r": max(7, 5 + cc * 2),
        "colour": COLOURS.get(domain, "#aaaaaa"),
        "x": round(R * math.sin(phi) * math.cos(theta), 1),
        "y": round(R * math.cos(phi), 1),
        "z": round(R * math.sin(phi) * math.sin(theta), 1),
    })

edges_data, seen = [], set()
for e in edges_raw:
    k = f"{e[0]}-{e[1]}"
    if k not in seen:
        seen.add(k)
        edges_data.append({"from": e[0], "to": e[1], "name": e[2], "formula": e[3]})

# Adjacency for BFS
adj = {n["id"]: [] for n in nodes_data}
for e in edges_data:
    adj[e["from"]].append(e["to"])
    adj[e["to"]].append(e["from"])

node_edges = {n["id"]: [] for n in nodes_data}
for e in edges_data:
    node_edges[e["from"]].append(e)
    node_edges[e["to"]].append(e)

# Domain positions (rings)
dom_pos = {}
for n in nodes_data:
    d    = n["domain"]
    di   = dom_idx[d]
    ns   = [x for x in nodes_data if x["domain"] == d]
    ni   = ns.index(n)
    R2   = 60 + di * 26
    Y2   = (di - N_dom / 2) * 22
    a    = (ni / len(ns)) * math.pi * 2
    dom_pos[n["id"]] = [round(R2*math.cos(a),1), round(Y2,1), round(R2*math.sin(a),1)]

# Dimension filter groups
dim_groups = {}
for n in nodes_data:
    k = str(n["dim"])
    dim_groups.setdefault(k, []).append(n["id"])

dim_filters = sorted(
    [{"dim": k, "ids": v} for k, v in dim_groups.items() if len(v) >= 2],
    key=lambda x: -len(x["ids"])
)

DIM_NAMES = {
    str([2,1,-2,0,0,0,0]):   "energy / work / heat  (J)",
    str([1,0,-1,0,0,0,0]):   "velocity / speed  (m/s)",
    str([1,0,-2,0,0,0,0]):   "acceleration  (m/s²)",
    str([0,1,-2,0,0,0,0]):   "force / weight  (N)",
    str([0,0,0,0,1,0,0]):    "temperature  (K)",
    str([0,1,0,0,0,0,0]):    "mass  (kg)",
    str([1,0,0,0,0,0,0]):    "length / distance  (m)",
    str([0,0,1,0,0,0,0]):    "time / period  (s)",
    str([0,0,-1,0,0,0,0]):   "frequency / rate  (Hz)",
    str([2,1,-3,0,0,0,0]):   "power  (W)",
    str([-1,1,-2,0,0,0,0]):  "pressure  (Pa)",
    str([2,1,-2,0,-1,0,0]):  "entropy  (J/K)",
    str([2,1,-3,-1,0,0,0]):  "voltage / EMF  (V)",
    str([0,0,1,1,0,0,0]):    "electric charge  (C)",
    str([0,1,-2,-1,0,0,0]):  "magnetic field  (T)",
    str([2,1,-2,-2,0,0,0]):  "inductance / action  (H)",
    str([-2,-1,4,2,0,0,0]):  "capacitance  (F)",
    str([2,1,-3,-2,0,0,0]):  "resistance / impedance  (Ω)",
    str([0,0,0,0,0,0,0]):    "dimensionless",
    str([1,1,-2,0,0,0,0]):   "force / torque  (N)",
    str([2,1,-2,0,0,-1,0]):  "molar energy  (J/mol)",
    str([1,1,-1,0,0,0,0]):   "momentum  (kg·m/s)",
    str([2,0,-1,0,0,0,0]):   "kinematic viscosity / stream fn  (m²/s)",
    str([-1,1,-1,0,0,0,0]):  "dynamic viscosity  (Pa·s)",
    str([-3,1,0,0,0,0,0]):   "density  (kg/m³)",
    str([3,0,0,0,0,0,0]):    "volume  (m³)",
    str([2,0,-2,0,-1,0,0]):  "specific heat  (J/kg·K)",
    str([2,0,-2,0,0,0,0]):   "specific energy  (J/kg)",
    str([-3,0,0,0,0,1,0]):   "concentration  (mol/m³)",
    str([0,1,-1,0,0,0,0]):   "damping  (kg/s)",
    str([2,0,0,0,0,0,0]):    "area  (m²)",
    str([0,0,0,1,0,0,0]):    "electric current  (A)",
}

legend = "".join(
    f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0;'
    f'font-size:11px;color:#ccc">'
    f'<div style="width:10px;height:10px;border-radius:50%;flex-shrink:0;'
    f'background:{COLOURS.get(d,"#888")}"></div>{d}</div>'
    for d in sorted(set(n["domain"] for n in nodes_data))
)

# Load cross-domain matches if available
try:
    with open("cross_domain_matches.json") as f:
        cd = json.load(f)
    top_amber = cd.get("amber", [])[:80]
except:
    top_amber = []

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Concept Graph Explorer</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:#0d0d1f;overflow:hidden;font-family:monospace;color:#ddd;user-select:none;}}
canvas{{position:fixed;top:0;left:0;width:100%;height:100%;display:block;z-index:1;}}
#ui{{position:fixed;top:0;left:0;width:100%;height:100%;z-index:2;pointer-events:none;}}

#panel{{position:absolute;top:10px;right:10px;width:270px;
  background:rgba(8,8,24,0.95);border:1px solid #336;padding:14px;
  font-size:11px;line-height:1.7;pointer-events:all;max-height:86vh;overflow-y:auto;}}
#panel b{{color:#88aaff;font-size:13px;display:block;margin-bottom:4px;}}

#left{{position:absolute;top:10px;left:10px;width:195px;
  display:flex;flex-direction:column;gap:6px;pointer-events:all;}}

input.ctrl{{background:rgba(8,8,24,0.95);border:1px solid #336;color:#ddd;
  padding:7px 10px;font-family:monospace;font-size:12px;width:100%;outline:none;}}
#sres{{background:rgba(8,8,24,0.98);border:1px solid #224;}}
#sres div{{padding:5px 10px;cursor:pointer;font-size:11px;color:#aaa;border-bottom:1px solid #1a1a2e;}}
#sres div:hover{{background:#151530;color:#fff;}}

.box{{background:rgba(8,8,24,0.95);border:1px solid #336;padding:8px;}}
.box label{{font-size:10px;color:#556;display:block;margin-bottom:4px;letter-spacing:1px;text-transform:uppercase;}}
select.ctrl{{background:#080818;border:1px solid #334;color:#aaa;
  font-family:monospace;font-size:10px;width:100%;padding:4px;outline:none;}}
button.ctrl{{background:none;border:1px solid #334;color:#667;
  font-family:monospace;font-size:10px;padding:4px 8px;cursor:pointer;width:100%;margin-top:4px;}}
button.ctrl:hover{{color:#88aaff;border-color:#88aaff;}}

#bar{{position:absolute;bottom:10px;left:50%;transform:translateX(-50%);
  display:flex;gap:5px;pointer-events:all;flex-wrap:wrap;justify-content:center;}}
#bar button{{background:rgba(8,8,24,0.95);border:1px solid #336;color:#aaa;
  padding:7px 12px;font-family:monospace;font-size:11px;cursor:pointer;}}
#bar button:hover{{border-color:#88aaff;color:#88aaff;}}
#bar button.on{{border-color:#ff7700;color:#ff7700;}}

#leg{{position:absolute;bottom:50px;right:10px;background:rgba(8,8,24,0.95);
  border:1px solid #224;padding:10px;max-height:260px;overflow-y:auto;
  display:none;pointer-events:all;}}

#cdpanel{{display:none;position:absolute;top:10px;left:215px;width:290px;
  background:rgba(8,8,24,0.97);border:1px solid #553;padding:14px;
  max-height:86vh;overflow-y:auto;pointer-events:all;font-size:11px;}}

#hint{{position:absolute;bottom:10px;right:10px;color:#334;font-size:10px;pointer-events:none;text-align:right;}}
#stats{{position:absolute;bottom:10px;left:10px;color:#334;font-size:10px;pointer-events:none;}}
</style>
</head>
<body>
<canvas id="cv"></canvas>
<div id="ui">

<div id="panel">
  <b id="pn">click a node to explore</b>
  <div id="pd" style="color:#556;margin-bottom:2px"></div>
  <div id="pu" style="color:#44ffcc"></div>
  <div id="pdm" style="color:#445;font-size:10px;margin:2px 0"></div>
  <div id="pds" style="color:#bbc;margin:5px 0"></div>
  <div id="pc" style="color:#88aaff;margin-bottom:5px"></div>
  <div id="pe"></div>
</div>

<div id="left">
  <input id="si" class="ctrl" placeholder="search concepts..." autocomplete="off">
  <div id="sres"></div>

  <div class="box">
    <label>Filter by Dimension</label>
    <select id="dimsel" class="ctrl" onchange="filterDim(this.value)">
      <option value="">— show all —</option>
    </select>
    <button class="ctrl" onclick="clearDimFilter()">clear filter</button>
  </div>

  <div class="box">
    <label>Find Path</label>
    <input id="pa" class="ctrl" placeholder="from concept..." autocomplete="off" style="margin-bottom:3px">
    <input id="pb" class="ctrl" placeholder="to concept..." autocomplete="off" style="margin-bottom:4px">
    <button class="ctrl" style="border-color:#ff7700;color:#ff7700" onclick="findPath()">FIND SHORTEST PATH</button>
    <div id="pr" style="font-size:10px;color:#aacc88;margin-top:5px;line-height:1.5"></div>
  </div>
</div>

<div id="bar">
  <button class="on" onclick="setView('sphere',this)">SPHERE</button>
  <button onclick="setView('domain',this)">DOMAIN</button>
  <button id="bsp" onclick="toggleSpin(this)">SPIN</button>
  <button onclick="toggleLegend()">LEGEND</button>
  <button onclick="toggleBridges()">BRIDGES</button>
  <button onclick="resetCam()">RESET</button>
</div>

<div id="leg">{legend}</div>

<div id="cdpanel">
  <div style="color:#ffaa33;letter-spacing:2px;font-size:12px;margin-bottom:6px">
    ⚠ UNDECLARED BRIDGES</div>
  <div style="color:#667;font-size:10px;margin-bottom:10px">
    Concepts sharing SI dimensions across domains — candidate knowledge holes.</div>
  <div id="cdlist"></div>
</div>

<div id="hint">drag to rotate · scroll to zoom · click node</div>
<div id="stats">{len(nodes_data)} concepts · {len(edges_data)} connections</div>
</div>

<script>
// ── Data ──────────────────────────────────────────────────────────────────
const NODES       = {json.dumps(nodes_data)};
const EDGES       = {json.dumps(edges_data)};
const DOM_POS     = {json.dumps(dom_pos)};
const ADJ         = {json.dumps(adj)};
const NODE_EDGES  = {json.dumps(node_edges)};
const DIM_FILTERS = {json.dumps(dim_filters)};
const DIM_NAMES   = {json.dumps(DIM_NAMES)};
const CROSS_DOMAIN= {json.dumps(top_amber)};

const byId = {{}};
NODES.forEach(n => byId[n.id] = n);

// Populate dimension dropdown
(function(){{
  const sel = document.getElementById('dimsel');
  DIM_FILTERS.forEach((f,i) => {{
    const opt = document.createElement('option');
    opt.value = i;
    opt.textContent = (DIM_NAMES[f.dim] || f.dim) + ' (' + f.ids.length + ')';
    sel.appendChild(opt);
  }});
}})();

// Populate bridge panel
(function(){{
  const list = document.getElementById('cdlist');
  list.innerHTML = CROSS_DOMAIN.map(m =>
    `<div style="border-top:1px solid #221;padding:6px 0;cursor:pointer"
       onclick="highlightBridge('${{m.from_id}}','${{m.to_id}}')"
       onmouseenter="this.style.background='#111133'"
       onmouseleave="this.style.background=''">
      <div style="color:#ffcc66">${{m.from}} <span style="color:#445">↔</span> ${{m.to}}</div>
      <div style="color:#556;font-size:10px">[${{m.from_domain}}] → [${{m.to_domain}}]</div>
      <div style="color:#88aaff;font-size:10px">conf: ${{m.confidence}}</div>
    </div>`
  ).join('');
}})();

// ── Canvas ────────────────────────────────────────────────────────────────
const cv = document.getElementById('cv');
const cx = cv.getContext('2d');
let W, H;
function resize() {{ W = cv.width = window.innerWidth; H = cv.height = window.innerHeight; }}
resize();
window.addEventListener('resize', resize);

// ── State ─────────────────────────────────────────────────────────────────
let rx=0.30, ry=0.50, zoom=1.0, spinning=false;
let selId=null, hlSet=new Set(), pathSet=new Set(), dimFilter=null;
let currentPos = 'sphere';  // 'sphere' or 'domain'

function getPos(id) {{
  const n = byId[id];
  if (!n) return null;
  return currentPos === 'domain' ? DOM_POS[id] : [n.x, n.y, n.z];
}}

// ── Projection ────────────────────────────────────────────────────────────
function proj(p) {{
  const cy=Math.cos(ry), sy=Math.sin(ry);
  const x1=p[0]*cy - p[2]*sy, z1=p[0]*sy + p[2]*cy;
  const cx2=Math.cos(rx), sx2=Math.sin(rx);
  const y2=p[1]*cx2 - z1*sx2, z2=p[1]*sx2 + z1*cx2;
  const fov=520*zoom, sc=fov/(fov+z2+300);
  return [W/2 + x1*sc, H/2 + y2*sc, sc, z2];
}}

// ── Render ────────────────────────────────────────────────────────────────
function draw() {{
  if (spinning) ry += 0.005;

  cx.fillStyle = '#0d0d1f';
  cx.fillRect(0, 0, W, H);

  const pr = {{}};
  const activeIds = dimFilter ? new Set(dimFilter) : null;
  NODES.forEach(n => {{
    const p = getPos(n.id);
    if (p) pr[n.id] = proj(p);
  }});

  // Edges
  EDGES.forEach(e => {{
    const a=pr[e.from], b=pr[e.to];
    if (!a || !b) return;
    if (activeIds && (!activeIds.has(e.from) || !activeIds.has(e.to))) return;
    const onPath = pathSet.has(e.from) && pathSet.has(e.to);
    const isSel  = e.from===selId || e.to===selId;
    if ((selId || pathSet.size) && !isSel && !onPath) return;
    cx.beginPath(); cx.moveTo(a[0],a[1]); cx.lineTo(b[0],b[1]);
    cx.strokeStyle = onPath ? 'rgba(255,200,50,0.95)'
                   : isSel  ? 'rgba(140,170,255,0.85)'
                   :          'rgba(90,110,190,0.30)';
    cx.lineWidth   = onPath ? 2.5 : isSel ? 1.8 : 0.8;
    cx.stroke();
  }});

  // Nodes — back to front
  NODES.filter(n => pr[n.id])
       .sort((a,b) => pr[a.id][3] - pr[b.id][3])
       .forEach(n => {{
    if (activeIds && !activeIds.has(n.id)) return;
    const [sx, sy, sc] = pr[n.id];
    const r      = Math.max(n.r * sc * 2.4, 5);  // never below 5px
    const isSel  = n.id === selId;
    const isHL   = hlSet.has(n.id);
    const onPath = pathSet.has(n.id);
    const faded  = !!(selId || pathSet.size) && !isSel && !isHL && !onPath;

    cx.shadowColor = onPath ? '#ffcc33' : n.colour;
    cx.shadowBlur  = isSel ? 40 : onPath ? 28 : isHL ? 20 : faded ? 0 : 14;

    cx.beginPath();
    cx.arc(sx, sy, r, 0, Math.PI*2);
    cx.fillStyle = isSel   ? '#ffffff'
                 : onPath  ? '#ffcc33'
                 : faded   ? 'rgba(30,35,60,0.55)'
                 : n.colour;
    cx.fill();
    cx.shadowBlur = 0;

    // Labels
    if (r > 8 || isSel || isHL || onPath) {{
      const fs = Math.max(9, Math.min(13, r * 0.95));
      cx.font      = `bold ${{fs}}px monospace`;
      cx.textAlign = 'center';
      cx.fillStyle = isSel   ? '#ffffff'
                   : onPath  ? '#ffcc33'
                   : faded   ? 'rgba(40,50,80,0.4)'
                   : 'rgba(225,232,255,0.93)';
      cx.fillText(n.name, sx, sy - r - 3);
    }}
  }});

  requestAnimationFrame(draw);
}}

// ── Mouse / touch ─────────────────────────────────────────────────────────
let drag=false, mx=0, my=0, mxS=0, myS=0;

document.addEventListener('mousedown', e => {{
  if (e.target.closest('#panel,#left,#bar,#leg,#cdpanel')) return;
  drag=true; mx=mxS=e.clientX; my=myS=e.clientY;
  e.preventDefault();
}});
document.addEventListener('mousemove', e => {{
  if (!drag) return;
  ry += (e.clientX - mx) * 0.006;
  rx += (e.clientY - my) * 0.006;
  mx=e.clientX; my=e.clientY;
}});
document.addEventListener('mouseup', e => {{
  if (!drag) return; drag=false;
  if (Math.abs(e.clientX-mxS)<5 && Math.abs(e.clientY-myS)<5) click(e.clientX, e.clientY);
}});
document.addEventListener('wheel', e => {{
  if (e.target.closest('#panel,#left,#bar,#leg,#cdpanel')) return;
  zoom *= e.deltaY > 0 ? 0.91 : 1.10;
  zoom = Math.max(0.1, Math.min(8, zoom));
  e.preventDefault();
}}, {{passive:false}});

let lt=null, ld=null;
document.addEventListener('touchstart', e => {{
  if (e.target.closest('#panel,#left,#bar,#leg,#cdpanel')) return;
  if (e.touches.length===1) lt=[e.touches[0].clientX, e.touches[0].clientY];
  if (e.touches.length===2) {{
    const dx=e.touches[0].clientX-e.touches[1].clientX;
    const dy=e.touches[0].clientY-e.touches[1].clientY;
    ld=Math.sqrt(dx*dx+dy*dy);
  }}
}},{{passive:true}});
document.addEventListener('touchmove', e => {{
  if (e.target.closest('#panel,#left,#bar,#leg,#cdpanel')) return;
  if (e.touches.length===1 && lt) {{
    ry += (e.touches[0].clientX-lt[0])*0.006;
    rx += (e.touches[0].clientY-lt[1])*0.006;
    lt=[e.touches[0].clientX, e.touches[0].clientY];
  }}
  if (e.touches.length===2 && ld) {{
    const dx=e.touches[0].clientX-e.touches[1].clientX;
    const dy=e.touches[0].clientY-e.touches[1].clientY;
    const d=Math.sqrt(dx*dx+dy*dy);
    zoom *= d/ld; ld=d; zoom=Math.max(0.1,Math.min(8,zoom));
  }}
  e.preventDefault();
}},{{passive:false}});
document.addEventListener('touchend', ()=>{{lt=null;ld=null;}},{{passive:true}});

function click(cx2, cy2) {{
  const pr={{}};
  NODES.forEach(n=>{{ const p=getPos(n.id); if(p) pr[n.id]=proj(p); }});
  let best=null, bestD=28;
  NODES.forEach(n => {{
    const p=pr[n.id]; if(!p) return;
    const dx=p[0]-cx2, dy=p[1]-cy2;
    const d=Math.sqrt(dx*dx+dy*dy);
    const r=Math.max(n.r*p[2]*2.4, 5);
    if (d < Math.max(bestD, r+6)) {{ best=n; bestD=d; }}
  }});
  if (best) selectNode(best); else clearSel();
}}

// ── Node selection ────────────────────────────────────────────────────────
function selectNode(n) {{
  selId=n.id; hlSet=new Set([n.id]); pathSet=new Set();
  (NODE_EDGES[n.id]||[]).forEach(e => {{ hlSet.add(e.from); hlSet.add(e.to); }});
  document.getElementById('pn').textContent  = n.name;
  document.getElementById('pd').textContent  = '⬡ ' + n.domain;
  document.getElementById('pu').textContent  = n.unit ? 'unit: ' + n.unit : '';
  document.getElementById('pdm').textContent = 'SI [' + n.dim.join(',') + ']';
  document.getElementById('pds').textContent = n.desc;
  document.getElementById('pc').textContent  = n.connections + ' connections';
  document.getElementById('pe').innerHTML    = (NODE_EDGES[n.id]||[]).slice(0,8).map(e =>
    `<div style="border-top:1px solid #1a1a3a;padding-top:4px;margin-top:4px;font-size:10px;color:#778">
      <span style="color:#99bb66;display:block">${{e.name}}</span>${{e.formula}}</div>`
  ).join('');
  document.getElementById('pa').value = n.name;
}}

function clearSel() {{
  selId=null; hlSet=new Set(); pathSet=new Set();
  document.getElementById('pn').textContent = 'click a node to explore';
  ['pd','pu','pdm','pds','pc','pe'].forEach(id => document.getElementById(id).innerHTML='');
}}

function highlightBridge(id1, id2) {{
  selId=null; pathSet=new Set();
  hlSet=new Set([id1, id2]);
  const n1=byId[id1], n2=byId[id2];
  if (n1&&n2) {{
    document.getElementById('pn').textContent  = n1.name + ' ↔ ' + n2.name;
    document.getElementById('pd').textContent  = '⚠ undeclared cross-domain bridge';
    document.getElementById('pu').textContent  = '['+n1.domain+'] → ['+n2.domain+']';
    document.getElementById('pdm').textContent = 'shared dim: ['+n1.dim.join(',')+']';
    document.getElementById('pds').textContent = 'Same SI dimension across different domains. No mechanism declared yet — candidate knowledge hole.';
    document.getElementById('pc').textContent  = '';
    document.getElementById('pe').innerHTML    = '';
  }}
}}

// ── Path finder ───────────────────────────────────────────────────────────
function findPath() {{
  const aQ = document.getElementById('pa').value.toLowerCase().trim();
  const bQ = document.getElementById('pb').value.toLowerCase().trim();
  const find = q => NODES.find(n=>n.name.toLowerCase()===q)
                 || NODES.find(n=>n.name.toLowerCase().startsWith(q))
                 || NODES.find(n=>n.name.toLowerCase().includes(q));
  const nA=find(aQ), nB=find(bQ);
  const res=document.getElementById('pr');
  if (!nA||!nB) {{ res.textContent='concept not found'; return; }}
  if (nA.id===nB.id) {{ res.textContent='same concept'; return; }}

  const visited={{}}, queue=[[nA.id]];
  visited[nA.id]=true;
  let found=null;
  while (queue.length && !found) {{
    const path=queue.shift(), last=path[path.length-1];
    for (const nb of (ADJ[last]||[])) {{
      if (visited[nb]) continue;
      visited[nb]=true;
      const np=[...path, nb];
      if (nb===nB.id) {{ found=np; break; }}
      queue.push(np);
    }}
  }}
  if (!found) {{ res.innerHTML='<span style="color:#ff5555">no path found</span>'; pathSet=new Set(); return; }}
  pathSet=new Set(found); selId=null; hlSet=new Set();
  res.innerHTML='<b style="color:#ffcc33">'+(found.length-1)+' hops:</b><br>'+found.map(id=>byId[id].name).join(' → ');
}}

['pa','pb'].forEach(id => {{
  document.getElementById(id).addEventListener('keydown', e => {{ if(e.key==='Enter') findPath(); }});
}});

// ── Dimension filter ──────────────────────────────────────────────────────
function filterDim(v) {{
  if (!v) {{ dimFilter=null; return; }}
  dimFilter=DIM_FILTERS[parseInt(v)].ids;
  selId=null; hlSet=new Set(); pathSet=new Set();
}}
function clearDimFilter() {{ dimFilter=null; document.getElementById('dimsel').value=''; }}

// ── Controls ──────────────────────────────────────────────────────────────
function setView(m, btn) {{
  document.querySelectorAll('#bar button').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');
  currentPos=m;
}}
function toggleSpin(btn) {{ spinning=!spinning; btn.classList.toggle('on',spinning); }}
function toggleLegend() {{
  const el=document.getElementById('leg');
  el.style.display = el.style.display==='block' ? 'none' : 'block';
}}
function toggleBridges() {{
  const el=document.getElementById('cdpanel');
  el.style.display = el.style.display==='block' ? 'none' : 'block';
}}
function resetCam() {{ rx=0.30; ry=0.50; zoom=1.0; clearSel(); clearDimFilter(); }}

// ── Search ────────────────────────────────────────────────────────────────
document.getElementById('si').addEventListener('input', function() {{
  const q=this.value.toLowerCase(), el=document.getElementById('sres');
  if (!q) {{ el.innerHTML=''; return; }}
  el.innerHTML=NODES.filter(n=>n.name.includes(q)||n.domain.includes(q))
    .slice(0,7).map(n=>
      `<div onclick="selectNode(byId['${{n.id}}']);this.parentElement.innerHTML='';
        document.getElementById('si').value=''">
        ${{n.name}} <span style="color:#445">[${{n.domain}}]</span></div>`
    ).join('');
}});

// ── Go ────────────────────────────────────────────────────────────────────
draw();
</script>
</body>
</html>"""

with open(OUT, "w") as f:
    f.write(html)
print(f"Done: {OUT}  ({len(html)//1024}kb)  {len(nodes_data)} nodes  {len(edges_data)} edges")
