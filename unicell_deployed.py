"""
unicell_deployed.py — UniCell Deployed System Server
=====================================================
Lightweight server for deployed UniCell systems. Reads PTT output
only — no compiler, no tile library, no workbench. Just the fabric
running and the PTT reporting results.

Usage:
    python unicell_deployed.py --model <model.isi> [--host 0.0.0.0] [--port 5100]

For development/VM use (no hardware):
    python unicell_deployed.py --vm --model models/laplacian_2d.json

API (read-only):
    GET /api/ptt              All PTT entries and their current values
    GET /api/ptt/<index>      Single PTT entry
    GET /api/status           System status
    GET /api/output           Structured output (model-defined format)
    GET /                     Lightweight viewer page
"""

import os, sys, json, time, argparse, threading
from pathlib import Path
from flask import Flask, jsonify, request

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

app  = Flask(__name__)
_ptt = None   # PTT instance — set at startup
_lock = threading.Lock()
_meta = {}    # model metadata (name, output format, etc.)


# ── PTT reader ────────────────────────────────────────────────────────────────

def read_ptt():
    """Read all current PTT entry values. Returns list of dicts."""
    with _lock:
        if _ptt is None:
            return []
        entries = []
        for idx, entry in _ptt._entries.items():
            entries.append({
                "index":       idx,
                "label":       entry.label or f"entry_{idx}",
                "status":      entry.status_name,
                "value":       entry.last_tick_value,
                "tick_count":  entry.tick_count,
                "is_stale":    entry.is_stale,
                "type":        entry.type_name,
                "updated_at":  entry.updated_at,
            })
        return entries


def read_ptt_entry(index):
    """Read a single PTT entry by index."""
    with _lock:
        if _ptt is None:
            return None
        entry = _ptt._entries.get(index)
        if entry is None:
            return None
        return {
            "index":       index,
            "label":       entry.label or f"entry_{index}",
            "status":      entry.status_name,
            "value":       entry.last_tick_value,
            "tick_count":  entry.tick_count,
            "is_stale":    entry.is_stale,
            "type":        entry.type_name,
            "updated_at":  entry.updated_at,
        }


# ── REST API ──────────────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    with _lock:
        ptt_count = len(_ptt._entries) if _ptt else 0
    return jsonify({
        "status":    "ok",
        "model":     _meta.get("name", "unknown"),
        "backend":   _meta.get("backend", "vm"),
        "ptt_entries": ptt_count,
        "time":      time.time(),
    })


@app.route("/api/ptt")
def api_ptt():
    return jsonify(read_ptt())


@app.route("/api/ptt/<int:index>")
def api_ptt_entry(index):
    entry = read_ptt_entry(index)
    if entry is None:
        return jsonify({"error": f"PTT entry {index} not found"}), 404
    return jsonify(entry)


@app.route("/api/output")
def api_output():
    """
    Structured output in model-defined format.
    The output format is described in model metadata.
    Default: flat list of {label, value} pairs from all PTT entries.
    """
    entries = read_ptt()
    output_format = _meta.get("output_format", "flat")

    if output_format == "flat":
        return jsonify({
            "format":  "flat",
            "model":   _meta.get("name", "unknown"),
            "time":    time.time(),
            "values":  [{"label": e["label"], "value": e["value"]}
                        for e in entries if e["status"] == "ACTIVE"],
        })

    elif output_format == "grid_2d":
        # PTT entries are labelled "cell_i_j" — reconstruct grid
        w = _meta.get("width", 1)
        h = _meta.get("height", 1)
        grid = [[0] * w for _ in range(h)]
        for e in entries:
            parts = e["label"].split("_")
            if len(parts) == 3:
                try:
                    i, j = int(parts[1]), int(parts[2])
                    if 0 <= i < h and 0 <= j < w:
                        grid[i][j] = e["value"]
                except ValueError:
                    pass
        return jsonify({
            "format": "grid_2d",
            "model":  _meta.get("name", "unknown"),
            "width":  w, "height": h,
            "time":   time.time(),
            "grid":   grid,
        })

    elif output_format == "vector":
        # PTT entries are labelled "out_N" — reconstruct ordered vector
        n = _meta.get("n", len(entries))
        vec = [0] * n
        for e in entries:
            parts = e["label"].split("_")
            if len(parts) == 2:
                try:
                    idx = int(parts[1])
                    if 0 <= idx < n:
                        vec[idx] = e["value"]
                except ValueError:
                    pass
        return jsonify({
            "format": "vector",
            "model":  _meta.get("name", "unknown"),
            "n":      n,
            "time":   time.time(),
            "values": vec,
        })

    else:
        return jsonify({"error": f"Unknown output format: {output_format}"}), 400


@app.route("/")
def frontend():
    """Lightweight read-only viewer — just PTT output."""
    return _viewer_page(), 200, {"Content-Type": "text/html"}


def _viewer_page():
    model_name = _meta.get("name", "UniCell")
    return f"""<!DOCTYPE html>
<html>
<head>
<title>{model_name} — UniCell</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, sans-serif; background: #0a0a0a; color: #e0e0e0;
          padding: 16px; max-width: 800px; margin: 0 auto; }}
  h1 {{ color: #00aaff; font-size: 1.3em; margin-bottom: 4px; }}
  .sub {{ color: #666; font-size: 0.8em; margin-bottom: 20px; }}
  .status {{ display: flex; gap: 16px; margin-bottom: 20px; font-size: 0.85em; }}
  .pill {{ background: #1a1a1a; border: 1px solid #333; border-radius: 20px;
           padding: 4px 12px; }}
  .ok {{ color: #00cc66; }} .warn {{ color: #ffaa00; }} .err {{ color: #ff4444; }}
  canvas {{ width: 100%; border: 1px solid #222; border-radius: 6px;
            display: block; margin-bottom: 12px; background: #111; }}
  #ptt-table {{ width: 100%; border-collapse: collapse; font-size: 0.8em; }}
  #ptt-table th {{ text-align: left; color: #666; padding: 4px 8px;
                   border-bottom: 1px solid #222; }}
  #ptt-table td {{ padding: 4px 8px; border-bottom: 1px solid #1a1a1a;
                   font-family: monospace; }}
  .active {{ color: #00cc66; }} .idle {{ color: #444; }} .stale {{ color: #ffaa00; }}
  #poll-rate {{ color: #666; font-size: 0.75em; text-align: right; margin-top: 8px; }}
</style>
</head>
<body>
<h1>⬡ {model_name}</h1>
<div class="sub">UniCell deployed system — PTT output view</div>

<div class="status">
  <span class="pill" id="sys-status">Connecting...</span>
  <span class="pill" id="ptt-count">— entries</span>
  <span class="pill" id="last-update">—</span>
</div>

<canvas id="canvas" height="200"></canvas>

<table id="ptt-table">
  <thead><tr><th>Index</th><th>Label</th><th>Status</th>
  <th>Value</th><th>Ticks</th></tr></thead>
  <tbody id="ptt-body"></tbody>
</table>
<div id="poll-rate"></div>

<script>
let lastPoll = Date.now();
let pollCount = 0;

async function poll() {{
  try {{
    const [status, ptt] = await Promise.all([
      fetch('/api/status').then(r => r.json()),
      fetch('/api/ptt').then(r => r.json()),
    ]);

    document.getElementById('sys-status').innerHTML =
      '<span class="ok">●</span> ' + status.model;
    document.getElementById('ptt-count').textContent =
      status.ptt_entries + ' PTT entries';
    document.getElementById('last-update').textContent =
      'Updated ' + new Date().toLocaleTimeString();

    renderPTT(ptt);
    renderCanvas(ptt);

    pollCount++;
    const elapsed = (Date.now() - lastPoll);
    document.getElementById('poll-rate').textContent =
      'Poll ' + pollCount + ' — ' + elapsed + 'ms';
    lastPoll = Date.now();
  }} catch(e) {{
    document.getElementById('sys-status').innerHTML =
      '<span class="err">●</span> Disconnected';
  }}
  setTimeout(poll, 200);
}}

function renderPTT(entries) {{
  const tbody = document.getElementById('ptt-body');
  tbody.innerHTML = entries.map(e => {{
    const cls = e.is_stale ? 'stale' : e.status === 'ACTIVE' ? 'active' : 'idle';
    return '<tr><td>' + e.index + '</td>' +
      '<td>' + e.label + '</td>' +
      '<td class="' + cls + '">' + e.status + '</td>' +
      '<td>0x' + (e.value >>> 0).toString(16).padStart(8,'0') + '</td>' +
      '<td>' + e.tick_count + '</td></tr>';
  }}).join('');
}}

function renderCanvas(entries) {{
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d');
  canvas.width = canvas.offsetWidth;
  const w = canvas.width, h = canvas.height;
  ctx.fillStyle = '#111';
  ctx.fillRect(0, 0, w, h);

  const active = entries.filter(e => e.status === 'ACTIVE');
  if (active.length === 0) {{
    ctx.fillStyle = '#333';
    ctx.font = '14px sans-serif';
    ctx.fillText('No active PTT entries', w/2 - 80, h/2);
    return;
  }}

  // Simple bar chart of active entry values
  const barW = Math.max(2, Math.floor(w / active.length) - 2);
  const maxVal = Math.max(...active.map(e => e.value >>> 0), 1);
  active.forEach((e, i) => {{
    const val = (e.value >>> 0) / maxVal;
    const bh = Math.floor(val * (h - 20));
    const x = i * (barW + 2) + 4;
    const hue = Math.floor(val * 220);
    ctx.fillStyle = `hsl(${{hue}}, 80%, 50%)`;
    ctx.fillRect(x, h - bh - 10, barW, bh);
  }});
}}

poll();
</script>
</body>
</html>"""


# ── VM mode — run a model and expose its PTT ──────────────────────────────────

def setup_vm_ptt(model_path):
    """
    For VM/development use: load a model JSON, run it, expose the PTT.
    In production this isn't used — the hardware PTT is already running.
    """
    global _ptt, _meta

    with open(model_path) as f:
        model = json.load(f)

    _meta = {
        "name":          model.get("name", Path(model_path).stem),
        "backend":       "vm",
        "output_format": model.get("output_format", "flat"),
        "width":         model.get("width"),
        "height":        model.get("height"),
    }

    # Create a minimal PTT for VM output
    from pond_ptt import PondPTT as PTT
    ptt = PTT(pond_id="deployed_vm")
    _ptt = ptt

    print(f"  Model: {_meta['name']}")
    print(f"  Output format: {_meta['output_format']}")
    print(f"  PTT ready ({len(ptt._entries)} entries)")


def attach_hardware_ptt(ptt_instance, meta):
    """
    For production use: attach an already-running PTT from the hardware system.
    Call this from your hardware bring-up code:

        from unicell_deployed import attach_hardware_ptt
        attach_hardware_ptt(my_ptt, {"name": "MyModel", "backend": "arria10"})
    """
    global _ptt, _meta
    with _lock:
        _ptt = ptt_instance
        _meta = meta
    print(f"  Attached hardware PTT: {meta.get('name')} on {meta.get('backend')}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UniCell Deployed Server")
    parser.add_argument("--host",  default="0.0.0.0")
    parser.add_argument("--port",  type=int, default=5100)
    parser.add_argument("--model", help="Model JSON path (VM mode)")
    parser.add_argument("--vm",    action="store_true", help="VM mode")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    print(f"\n  ⬡ UniCell Deployed Server")
    print(f"  ──────────────────────────")

    if args.model:
        print(f"  Loading model: {args.model}")
        setup_vm_ptt(args.model)
    else:
        # No model — start with empty PTT, wait for hardware attach
        from pond_ptt import PondPTT as PTT
        _ptt = PTT(pond_id="deployed")
        _meta = {"name": "UniCell", "backend": "hardware"}
        print(f"  Waiting for hardware PTT attach...")
        print(f"  Call attach_hardware_ptt(ptt, meta) from your bring-up code")

    print(f"\n  Listening on http://{args.host}:{args.port}")
    print(f"  Open http://localhost:{args.port} in a browser\n")

    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
