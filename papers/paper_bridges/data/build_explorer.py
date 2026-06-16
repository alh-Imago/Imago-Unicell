import sqlite3, json, math

conn = sqlite3.connect("concept_graph.db")
cur = conn.cursor()

concepts = cur.execute("""
    SELECT c.id, c.name, c.domain_id, c.unit_id, c.dimension, c.description
    FROM concepts c
""").fetchall()

edges_raw = cur.execute("""
    SELECT DISTINCT ec1.concept_id, ec2.concept_id, e.display_name, e.formula
    FROM equation_components ec1
    JOIN equation_components ec2 ON ec1.equation_id = ec2.equation_id
        AND ec1.concept_id < ec2.concept_id
    JOIN equations e ON ec1.equation_id = e.id
    WHERE ec1.role IN ('input','output') AND ec2.role IN ('input','output')
""").fetchall()

# Hub counts
hub = {}
for e in edges_raw:
    hub[e[0]] = hub.get(e[0],0)+1
    hub[e[1]] = hub.get(e[1],0)+1

COLOURS = {
    "kinematics":"#00d4ff","dynamics":"#0099ff","energy_domain":"#ff6600",
    "rotation":"#ffcc00","gravitation":"#aa77ff","oscillations":"#66ffcc",
    "fluids":"#00ffaa","thermodynamics":"#ff4455","heat_transfer":"#ff8888",
    "waves":"#44ffff","optics":"#88eeff","electrostatics":"#ffff44",
    "circuits":"#ffee44","magnetism":"#ff88ff","electromagnetism":"#ffaa00",
    "relativity":"#ff44aa","quantum":"#cc44ff","nuclear":"#ff2200",
    "chem_kinetics":"#44ff44","thermochem":"#88ff44",
    "genomics":"#44ff88","biochemistry":"#00ff66","momentum_domain":"#ff9900",
}

nodes_data = []
for c in concepts:
    cid,name,domain,unit,dim_json,desc = c
    dim = json.loads(dim_json)
    conn_count = hub.get(cid,0)
    nodes_data.append({
        "id":cid, "name":name, "domain":domain,
        "unit":unit or "", "dim":dim,
        "desc":desc or "",
        "connections":conn_count,
        "size": max(7, 5 + conn_count * 2.2),
        "colour": COLOURS.get(domain,"#888888"),
    })

edges_data = []
seen = set()
for e in edges_raw:
    k = f"{e[0]}-{e[1]}"
    if k not in seen:
        seen.add(k)
        edges_data.append({"from":e[0],"to":e[1],"name":e[2],"formula":e[3]})

conn.close()

nodes_json = json.dumps(nodes_data)
edges_json = json.dumps(edges_data)

# Domain legend entries
domains_seen = sorted(set(n["domain"] for n in nodes_data))
legend_items = ""
for d in domains_seen:
    col = COLOURS.get(d,"#888888")
    legend_items += f'<div class="leg-item"><span class="leg-dot" style="background:{col}"></span>{d}</div>\n'

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Imago Concept Graph Explorer</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0a0a1a; color:#e0e0f0; font-family:'Courier New',monospace; overflow:hidden; }}
#canvas {{ display:block; width:100vw; height:100vh; cursor:grab; }}
#canvas:active {{ cursor:grabbing; }}

#ui {{
  position:fixed; top:0; left:0; width:100vw; height:100vh;
  pointer-events:none;
}}

#title {{
  position:absolute; top:20px; left:50%; transform:translateX(-50%);
  font-size:13px; letter-spacing:4px; color:#667; text-transform:uppercase;
  pointer-events:none;
}}

#panel {{
  position:absolute; top:20px; right:20px; width:280px;
  background:rgba(5,5,20,0.92); border:1px solid #223;
  padding:16px; pointer-events:all;
  font-size:11px; line-height:1.7;
}}
#panel h2 {{ font-size:13px; color:#88aaff; margin-bottom:10px; letter-spacing:2px; }}
#panel-name {{ font-size:15px; color:#fff; font-weight:bold; margin-bottom:4px; }}
#panel-domain {{ color:#667; margin-bottom:6px; }}
#panel-unit {{ color:#44ffcc; margin-bottom:6px; }}
#panel-dim {{ color:#778; font-size:10px; margin-bottom:8px; }}
#panel-desc {{ color:#aab; margin-bottom:10px; line-height:1.5; }}
#panel-connections {{ color:#88aaff; }}
#panel-eqs {{ margin-top:8px; }}
.eq-item {{ 
  padding:4px 0; border-top:1px solid #112; 
  color:#889; font-size:10px;
}}
.eq-name {{ color:#aacc88; }}
.eq-formula {{ color:#667; font-style:italic; }}

#search-box {{
  position:absolute; top:20px; left:20px;
  pointer-events:all;
}}
#search {{
  background:rgba(5,5,20,0.92); border:1px solid #334;
  color:#e0e0f0; padding:8px 12px; font-family:'Courier New',monospace;
  font-size:12px; width:200px; outline:none;
  letter-spacing:1px;
}}
#search::placeholder {{ color:#445; }}
#search-results {{
  background:rgba(5,5,20,0.95); border:1px solid #223;
  max-height:200px; overflow-y:auto;
}}
.sr-item {{
  padding:6px 12px; font-size:11px; cursor:pointer; color:#aab;
  border-bottom:1px solid #112;
}}
.sr-item:hover {{ background:#112; color:#fff; }}

#controls {{
  position:absolute; bottom:20px; left:50%; transform:translateX(-50%);
  display:flex; gap:8px; pointer-events:all;
}}
.ctrl-btn {{
  background:rgba(5,5,20,0.92); border:1px solid #334;
  color:#889; padding:6px 14px; font-family:'Courier New',monospace;
  font-size:10px; letter-spacing:2px; cursor:pointer;
  text-transform:uppercase;
}}
.ctrl-btn:hover {{ border-color:#88aaff; color:#88aaff; }}
.ctrl-btn.active {{ border-color:#ff6600; color:#ff6600; }}

#legend {{
  position:absolute; bottom:60px; left:20px;
  background:rgba(5,5,20,0.88); border:1px solid #223;
  padding:12px; max-height:300px; overflow-y:auto;
  pointer-events:all;
  display:none;
}}
#legend h3 {{ font-size:10px; color:#667; letter-spacing:2px; margin-bottom:8px; }}
.leg-item {{ display:flex; align-items:center; gap:8px; font-size:10px; color:#778; margin:3px 0; }}
.leg-dot {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}

#stats {{
  position:absolute; bottom:20px; left:20px;
  font-size:10px; color:#334; letter-spacing:1px;
  pointer-events:none;
}}

#hint {{
  position:absolute; bottom:20px; right:20px;
  font-size:10px; color:#334; letter-spacing:1px;
  pointer-events:none; text-align:right;
}}
</style>
</head>
<body>
<canvas id="canvas"></canvas>
<div id="ui">
  <div id="title">IMAGO · CONCEPT GRAPH · PHYSICS SEED</div>

  <div id="search-box">
    <input id="search" type="text" placeholder="search concepts..." autocomplete="off">
    <div id="search-results"></div>
  </div>

  <div id="panel">
    <h2>CONCEPT</h2>
    <div id="panel-name">— click a node —</div>
    <div id="panel-domain"></div>
    <div id="panel-unit"></div>
    <div id="panel-dim"></div>
    <div id="panel-desc"></div>
    <div id="panel-connections"></div>
    <div id="panel-eqs"></div>
  </div>

  <div id="controls">
    <button class="ctrl-btn active" onclick="setLayout('force')">FORCE</button>
    <button class="ctrl-btn" onclick="setLayout('sphere')">SPHERE</button>
    <button class="ctrl-btn" onclick="setLayout('domain')">DOMAIN</button>
    <button class="ctrl-btn" onclick="toggleSpin()">AUTO-SPIN</button>
    <button class="ctrl-btn" onclick="document.getElementById('legend').style.display = document.getElementById('legend').style.display==='none'?'block':'none'">LEGEND</button>
    <button class="ctrl-btn" onclick="resetView()">RESET</button>
  </div>

  <div id="legend">
    <h3>DOMAINS</h3>
    {legend_items}
  </div>

  <div id="stats">{len(nodes_data)} concepts · {len(edges_data)} connections · physics seed</div>
  <div id="hint">drag to rotate · scroll to zoom · click node to explore</div>
</div>

<script>
const NODES = {nodes_json};
const EDGES = {edges_json};

// ── 3D Graph Engine ────────────────────────────────────────────────────────

const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

let W, H;
function resize() {{
  W = canvas.width  = window.innerWidth;
  H = canvas.height = window.innerHeight;
}}
resize();
window.addEventListener('resize', resize);

// Camera state
let rotX = 0.3, rotY = 0.5, rotZ = 0;
let zoom = 1;
let dragging = false, lastMX = 0, lastMY = 0;
let autoSpin = false;
let selectedId = null;
let highlightSet = new Set();

// 3D positions per node
let pos3D = {{}};  // id -> [x,y,z]
let vel3D = {{}};  // id -> [vx,vy,vz]

function initForce() {{
  // Random initial positions on a sphere
  NODES.forEach(n => {{
    const theta = Math.random() * Math.PI * 2;
    const phi   = Math.acos(2 * Math.random() - 1);
    const r     = 200 + Math.random() * 100;
    pos3D[n.id] = [
      r * Math.sin(phi) * Math.cos(theta),
      r * Math.sin(phi) * Math.sin(theta),
      r * Math.cos(phi)
    ];
    vel3D[n.id] = [0, 0, 0];
  }});
}}

function initSphere() {{
  // Evenly distributed on sphere
  NODES.forEach((n, i) => {{
    const golden = Math.PI * (3 - Math.sqrt(5));
    const y = 1 - (i / (NODES.length - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const theta = golden * i;
    const rad = 250;
    pos3D[n.id] = [rad * r * Math.cos(theta), rad * y, rad * r * Math.sin(theta)];
    vel3D[n.id] = [0,0,0];
  }});
}}

function initDomain() {{
  // Group by domain on concentric rings
  const domains = [...new Set(NODES.map(n => n.domain))];
  const nodesByDomain = {{}};
  NODES.forEach(n => {{
    if (!nodesByDomain[n.domain]) nodesByDomain[n.domain] = [];
    nodesByDomain[n.domain].push(n);
  }});
  domains.forEach((d, di) => {{
    const nodes = nodesByDomain[d];
    const ringR  = 80 + di * 40;
    const ringY  = (di - domains.length/2) * 30;
    nodes.forEach((n, ni) => {{
      const angle = (ni / nodes.length) * Math.PI * 2;
      pos3D[n.id] = [ringR * Math.cos(angle), ringY, ringR * Math.sin(angle)];
      vel3D[n.id] = [0,0,0];
    }});
  }});
}}

let layoutMode = 'force';
let forceRunning = false;
let forceIter = 0;

function setLayout(mode) {{
  layoutMode = mode;
  document.querySelectorAll('.ctrl-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  forceIter = 0;
  if (mode === 'force') {{ initForce(); forceRunning = true; }}
  else if (mode === 'sphere') {{ initSphere(); forceRunning = false; }}
  else if (mode === 'domain') {{ initDomain(); forceRunning = false; }}
}}

function stepForce() {{
  if (!forceRunning || forceIter > 300) {{ forceRunning = false; return; }}
  forceIter++;
  const ids = NODES.map(n => n.id);
  const REPEL = 2500, ATTRACT = 0.008, DAMP = 0.85, CENTER = 0.001;
  const edgeSet = new Set(EDGES.map(e => e.from+'-'+e.to));

  ids.forEach(a => {{
    const va = vel3D[a];
    const pa = pos3D[a];
    // Centering
    va[0] -= pa[0] * CENTER;
    va[1] -= pa[1] * CENTER;
    va[2] -= pa[2] * CENTER;
    // Repulsion
    ids.forEach(b => {{
      if (a >= b) return;
      const pb = pos3D[b];
      const dx = pa[0]-pb[0], dy = pa[1]-pb[1], dz = pa[2]-pb[2];
      const d2 = dx*dx+dy*dy+dz*dz+0.1;
      const f  = REPEL / d2;
      const vb = vel3D[b];
      va[0] += dx*f; va[1] += dy*f; va[2] += dz*f;
      vb[0] -= dx*f; vb[1] -= dy*f; vb[2] -= dz*f;
    }});
  }});

  EDGES.forEach(e => {{
    const pa = pos3D[e.from], pb = pos3D[e.to];
    const va = vel3D[e.from], vb = vel3D[e.to];
    if (!pa||!pb) return;
    const dx = pb[0]-pa[0], dy = pb[1]-pa[1], dz = pb[2]-pa[2];
    const d  = Math.sqrt(dx*dx+dy*dy+dz*dz)+0.01;
    const f  = (d - 120) * ATTRACT;
    va[0] += dx*f; va[1] += dy*f; va[2] += dz*f;
    vb[0] -= dx*f; vb[1] -= dy*f; vb[2] -= dz*f;
  }});

  ids.forEach(a => {{
    const v = vel3D[a], p = pos3D[a];
    v[0]*=DAMP; v[1]*=DAMP; v[2]*=DAMP;
    p[0]+=v[0]; p[1]+=v[1]; p[2]+=v[2];
  }});
}}

// ── 3D → 2D projection ────────────────────────────────────────────────────

function project([x,y,z]) {{
  // Rotate around Y (left-right)
  const cosY = Math.cos(rotY), sinY = Math.sin(rotY);
  const x1 = x*cosY - z*sinY, z1 = x*sinY + z*cosY;
  // Rotate around X (up-down)
  const cosX = Math.cos(rotX), sinX = Math.sin(rotX);
  const y2 = y*cosX - z1*sinX, z2 = y*sinX + z1*cosX;
  // Perspective
  const fov = 600 * zoom;
  const scale = fov / (fov + z2 + 400);
  return [W/2 + x1*scale, H/2 + y2*scale, scale, z2];
}}

// ── Render ────────────────────────────────────────────────────────────────

function render() {{
  if (autoSpin) rotY += 0.003;
  if (forceRunning) stepForce();

  ctx.fillStyle = '#0a0a1a';
  ctx.fillRect(0,0,W,H);

  // Project all nodes
  const projected = {{}};
  NODES.forEach(n => {{
    if (pos3D[n.id]) projected[n.id] = project(pos3D[n.id]);
  }});

  // Sort by depth (back to front)
  const sorted = NODES.filter(n => projected[n.id])
    .sort((a,b) => projected[a.id][3] - projected[b.id][3]);

  // Draw edges first
  EDGES.forEach(e => {{
    const pa = projected[e.from], pb = projected[e.to];
    if (!pa||!pb) return;
    const isHighlit = highlightSet.has(e.from) && highlightSet.has(e.to);
    const isSelected = e.from===selectedId || e.to===selectedId;
    if (selectedId && !isSelected) return;
    ctx.beginPath();
    ctx.moveTo(pa[0],pa[1]);
    ctx.lineTo(pb[0],pb[1]);
    if (isSelected || isHighlit) {{
      ctx.strokeStyle = 'rgba(136,170,255,0.7)';
      ctx.lineWidth = 1.2;
    }} else {{
      ctx.strokeStyle = 'rgba(80,100,160,0.5)';
      ctx.lineWidth = 0.8;
    }}
    ctx.stroke();
  }});

  // Draw nodes back to front
  sorted.forEach(n => {{
    const [sx,sy,scale] = projected[n.id];
    const r = n.size * scale * 1.8;
    const isSelected = n.id === selectedId;
    const isHighlit  = highlightSet.has(n.id);

    ctx.beginPath();
    ctx.arc(sx,sy,r,0,Math.PI*2);

    if (isSelected) {{
      ctx.fillStyle = '#ffffff';
      ctx.shadowColor = n.colour;
      ctx.shadowBlur  = 30;
    }} else if (isHighlit) {{
      ctx.fillStyle = n.colour;
      ctx.shadowColor = n.colour;
      ctx.shadowBlur  = 30;
    }} else if (selectedId) {{
      ctx.fillStyle = 'rgba(30,35,60,0.6)';
      ctx.shadowBlur = 0;
    }} else {{
      ctx.fillStyle = n.colour;
      ctx.shadowColor = n.colour;
      ctx.shadowBlur  = 15;
    }}
    ctx.fill();
    ctx.shadowBlur = 0;

    // Label for larger/selected nodes
    if (r > 5 || isSelected || isHighlit) {{
      ctx.fillStyle = isSelected ? '#fff' : (isHighlit ? n.colour : 'rgba(200,210,240,0.9)');
      ctx.font = `${{Math.max(8, Math.min(12, r*1.2))}}px 'Courier New'`;
      ctx.textAlign = 'center';
      ctx.fillText(n.name, sx, sy - r - 3);
    }}
  }});

  requestAnimationFrame(render);
}}

// ── Interaction ────────────────────────────────────────────────────────────

canvas.addEventListener('mousedown', e => {{ dragging=true; lastMX=e.clientX; lastMY=e.clientY; }});
canvas.addEventListener('mouseup',   () => dragging=false);
canvas.addEventListener('mousemove', e => {{
  if (!dragging) return;
  rotY += (e.clientX - lastMX) * 0.005;
  rotX += (e.clientY - lastMY) * 0.005;
  lastMX=e.clientX; lastMY=e.clientY;
}});
canvas.addEventListener('wheel', e => {{
  zoom *= e.deltaY > 0 ? 0.93 : 1.07;
  zoom = Math.max(0.2, Math.min(5, zoom));
  e.preventDefault();
}}, {{passive:false}});

// Touch support
let lastTouch = null, lastDist = null;
canvas.addEventListener('touchstart', e => {{
  if (e.touches.length===1) {{ lastTouch=[e.touches[0].clientX,e.touches[0].clientY]; }}
  if (e.touches.length===2) {{
    const dx=e.touches[0].clientX-e.touches[1].clientX;
    const dy=e.touches[0].clientY-e.touches[1].clientY;
    lastDist=Math.sqrt(dx*dx+dy*dy);
  }}
}}, {{passive:true}});
canvas.addEventListener('touchmove', e => {{
  if (e.touches.length===1 && lastTouch) {{
    rotY += (e.touches[0].clientX-lastTouch[0]) * 0.005;
    rotX += (e.touches[0].clientY-lastTouch[1]) * 0.005;
    lastTouch=[e.touches[0].clientX,e.touches[0].clientY];
  }}
  if (e.touches.length===2 && lastDist) {{
    const dx=e.touches[0].clientX-e.touches[1].clientX;
    const dy=e.touches[0].clientY-e.touches[1].clientY;
    const d=Math.sqrt(dx*dx+dy*dy);
    zoom *= d/lastDist; lastDist=d;
    zoom = Math.max(0.2, Math.min(5, zoom));
  }}
  e.preventDefault();
}}, {{passive:false}});

canvas.addEventListener('click', e => {{
  // Find closest node to click
  let best = null, bestD = 20;
  NODES.forEach(n => {{
    const p = pos3D[n.id] ? project(pos3D[n.id]) : null;
    if (!p) return;
    const dx=p[0]-e.clientX, dy=p[1]-e.clientY;
    const d=Math.sqrt(dx*dx+dy*dy);
    const r=n.size*p[2]*1.8;
    if (d < Math.max(bestD, r+4)) {{ best=n; bestD=d; }}
  }});
  if (best) selectNode(best);
  else clearSelection();
}});

function selectNode(n) {{
  selectedId = n.id;
  // Find connected nodes
  highlightSet = new Set([n.id]);
  const connectedEqs = [];
  EDGES.forEach(e => {{
    if (e.from===n.id || e.to===n.id) {{
      highlightSet.add(e.from);
      highlightSet.add(e.to);
      connectedEqs.push(e);
    }}
  }});

  document.getElementById('panel-name').textContent = n.name;
  document.getElementById('panel-domain').textContent = '⬡ ' + n.domain;
  document.getElementById('panel-unit').textContent = n.unit ? 'unit: ' + n.unit : '';
  document.getElementById('panel-dim').textContent = 'SI: [' + n.dim.join(', ') + ']  m·kg·s·A·K·mol·cd';
  document.getElementById('panel-desc').textContent = n.desc;
  document.getElementById('panel-connections').textContent = `${{n.connections}} direct connections`;

  const eqsDiv = document.getElementById('panel-eqs');
  eqsDiv.innerHTML = connectedEqs.slice(0,8).map(e =>
    `<div class="eq-item"><div class="eq-name">${{e.name}}</div><div class="eq-formula">${{e.formula}}</div></div>`
  ).join('');
}}

function clearSelection() {{
  selectedId = null;
  highlightSet = new Set();
  document.getElementById('panel-name').textContent = '— click a node —';
  ['panel-domain','panel-unit','panel-dim','panel-desc','panel-connections','panel-eqs']
    .forEach(id => document.getElementById(id).textContent = '');
}}

function toggleSpin() {{
  autoSpin = !autoSpin;
  event.target.classList.toggle('active', autoSpin);
}}

function resetView() {{
  rotX=0.3; rotY=0.5; zoom=1; clearSelection();
}}

// ── Search ────────────────────────────────────────────────────────────────

const searchEl = document.getElementById('search');
const resultsEl = document.getElementById('search-results');

searchEl.addEventListener('input', () => {{
  const q = searchEl.value.toLowerCase().trim();
  if (!q) {{ resultsEl.innerHTML=''; return; }}
  const hits = NODES.filter(n => n.name.includes(q) || n.domain.includes(q) || n.desc.toLowerCase().includes(q)).slice(0,8);
  resultsEl.innerHTML = hits.map(n =>
    `<div class="sr-item" onclick="selectNode(NODES.find(x=>x.id==='${{n.id}}')); document.getElementById('search').value=''; document.getElementById('search-results').innerHTML='';">
      ${{n.name}} <span style="color:#445">[${{n.domain}}]</span>
    </div>`
  ).join('');
}});

// ── Init ──────────────────────────────────────────────────────────────────

initForce();
forceRunning = true;
render();
</script>
</body>
</html>"""

with open("concept_graph_explorer.html", "w") as f:
    f.write(html)
print(f"Written: concept_graph_explorer.html ({len(html)//1024}kb)")
