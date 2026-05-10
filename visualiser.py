import imago_log
"""
visualiser.py — Imago UniCell Array Visualiser

Opens a local web server and launches a browser showing a live grid
of the UniCell array. Each cell is a coloured block. Click any cell
to expand its state in the side panel. Step or run the simulation
with controls in the browser.

Usage:
    from visualiser import Visualiser
    from unicell_array import UniCellArray
    from controller import ImagoController

    ctrl = ImagoController(cell_count=64)
    # ... load a program ...
    vis = Visualiser(ctrl.array, grid_cols=8)
    vis.serve()   # opens browser and blocks until window closed

Or run standalone for a demo:
    python3 visualiser.py
"""

import json
import math
import threading
import webbrowser
import time
import http.server
import urllib.parse
from typing import Optional

from unicell_array import UniCellArray
from unicell import UniCell

# ── cell state classification ─────────────────────────────────────────────────

def cell_state(cell: UniCell) -> str:
    """Classify a cell into a display state."""
    if cell._config_mode:
        return "configuring"
    if cell.is_loopback and cell.start_flag:
        return "memory"
    if cell.start_flag and cell.data is not None:
        return "fired"
    if cell.start_flag:
        return "waiting"
    if cell.gate_state == 0 and cell.input_address == 0 and cell.output_address == 0:
        return "blank"
    return "halted"


def gate_state_description(gs: int) -> list[str]:
    """Describe which gates are active in a gate state value."""
    gate_names = [
        "G0: NOT(A,A)",
        "G1: NOT(A,A)",
        "G2: NOR(G1,G2)",
        "G3: NOR(G3,A)",
        "G4: NOR(G3,A)",
        "G5: NOR(G4,G5)",
        "G6: NOR(G6,A)",
        "G7: SR-latch Q",
        "G8: Buffer/inv",
    ]
    active = []
    for i, name in enumerate(gate_names):
        if (gs >> i) & 1:
            active.append(f"[ON]  {name}")
        else:
            active.append(f"[off] {name}")
    return active


# ── array snapshot ────────────────────────────────────────────────────────────

def array_snapshot(array: UniCellArray, recently_fired: set) -> dict:
    """Capture current array state as a JSON-serialisable dict."""
    cells = []
    for addr in sorted(array.cells.keys()):
        cell = array.cells[addr]
        state = cell_state(cell)
        if addr in recently_fired:
            state = "fired"
        cells.append({
            "address":      addr,
            "address_hex":  f"0x{addr:08X}",
            "gate_state":   cell.gate_state,
            "gate_state_bin": f"0b{cell.gate_state:09b}",
            "input_address":  f"0x{cell.input_address:08X}",
            "output_address": f"0x{cell.output_address:08X}",
            "is_loopback":  cell.is_loopback,
            "start_flag":   cell.start_flag,
            "data":         int(cell.data) if cell.data is not None else None,
            "config_mode":  cell._config_mode,
            "state":        state,
            "gate_details": gate_state_description(cell.gate_state),
        })
    bus = {
        f"0x{addr:08X}": val
        for addr, val in array.bus.items()
    }
    return {
        "cells":          cells,
        "bus":            bus,
        "total_cells":    array._cell_count,
        "allocated":      len(array.cells),
        "defective":      len(array.defect_map),
    }


# ── HTML page ─────────────────────────────────────────────────────────────────

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Imago UniCell Visualiser</title>
<style>
  :root {
    --bg:        #0d1117;
    --panel:     #161b22;
    --border:    #30363d;
    --text:      #c9d1d9;
    --muted:     #8b949e;
    --accent:    #58a6ff;

    --c-blank:      #21262d;
    --c-blank-b:    #30363d;
    --c-waiting:    #1f6feb;
    --c-waiting-b:  #388bfd;
    --c-fired:      #238636;
    --c-fired-b:    #3fb950;
    --c-memory:     #9a6700;
    --c-memory-b:   #d29922;
    --c-halted:     #6e4a7e;
    --c-halted-b:   #a371f7;
    --c-config:     #b08800;
    --c-config-b:   #f0d000;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }

  /* ── header ── */
  header {
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 16px;
    flex-shrink: 0;
  }
  header h1 {
    font-size: 15px;
    color: var(--accent);
    letter-spacing: 1px;
  }
  .stat { color: var(--muted); font-size: 12px; }
  .stat span { color: var(--text); }

  /* ── controls ── */
  .controls {
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    padding: 8px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }
  button {
    background: #21262d;
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 5px 14px;
    cursor: pointer;
    font-family: inherit;
    font-size: 12px;
    transition: background 0.1s;
  }
  button:hover  { background: #30363d; }
  button.active { background: #238636; border-color: #3fb950; color: #fff; }
  button.danger { border-color: #f85149; color: #f85149; }
  button.danger:hover { background: #3d1c1c; }

  label { color: var(--muted); font-size: 12px; }
  input[type=range] { width: 100px; accent-color: var(--accent); }

  #cycle-display {
    margin-left: auto;
    color: var(--muted);
    font-size: 12px;
  }
  #cycle-display span { color: var(--accent); font-weight: bold; }

  /* ── legend ── */
  .legend {
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
  }
  .legend-item {
    display: flex; align-items: center; gap: 4px; font-size: 11px;
    color: var(--muted);
  }
  .legend-dot {
    width: 10px; height: 10px; border-radius: 2px;
  }

  /* ── main area ── */
  .main {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  /* ── grid area ── */
  #grid-wrap {
    flex: 1;
    overflow: auto;
    padding: 16px;
    display: flex;
    align-items: flex-start;
    justify-content: flex-start;
  }
  #grid {
    display: grid;
    gap: 3px;
  }

  /* ── cell block ── */
  .cell {
    width: 32px; height: 32px;
    border-radius: 4px;
    border: 1.5px solid transparent;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    font-size: 9px;
    color: rgba(255,255,255,0.4);
    transition: transform 0.05s, filter 0.05s;
    position: relative;
  }
  .cell:hover { transform: scale(1.18); filter: brightness(1.3); z-index: 10; }
  .cell.selected { outline: 2px solid var(--accent); outline-offset: 1px; z-index: 11; }

  .cell[data-state="blank"]       { background: var(--c-blank);   border-color: var(--c-blank-b); }
  .cell[data-state="waiting"]     { background: var(--c-waiting); border-color: var(--c-waiting-b); }
  .cell[data-state="fired"]       { background: var(--c-fired);   border-color: var(--c-fired-b); animation: pulse 0.3s; }
  .cell[data-state="memory"]      { background: var(--c-memory);  border-color: var(--c-memory-b); }
  .cell[data-state="halted"]      { background: var(--c-halted);  border-color: var(--c-halted-b); }
  .cell[data-state="configuring"] { background: var(--c-config);  border-color: var(--c-config-b); }

  @keyframes pulse {
    0%   { filter: brightness(2.5); }
    100% { filter: brightness(1);   }
  }

  /* ── side panel ── */
  #side-panel {
    width: 300px;
    flex-shrink: 0;
    background: var(--panel);
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  #side-panel h2 {
    padding: 12px 14px;
    font-size: 12px;
    color: var(--accent);
    border-bottom: 1px solid var(--border);
    letter-spacing: 1px;
    text-transform: uppercase;
  }
  #cell-detail {
    flex: 1;
    overflow-y: auto;
    padding: 12px 14px;
    font-size: 12px;
    line-height: 1.7;
  }
  .detail-row {
    display: flex;
    gap: 8px;
    border-bottom: 1px solid #21262d;
    padding: 4px 0;
  }
  .detail-label {
    color: var(--muted);
    width: 120px;
    flex-shrink: 0;
  }
  .detail-value { color: var(--text); word-break: break-all; }
  .detail-value.on  { color: #3fb950; }
  .detail-value.off { color: #6e7681; }
  .gate-list { margin-top: 8px; }
  .gate-item { font-size: 11px; padding: 1px 0; }
  .gate-item.active { color: #d29922; }
  .gate-item.inactive { color: #6e7681; }
  #no-selection {
    color: var(--muted);
    padding: 16px 14px;
    font-size: 12px;
    line-height: 1.6;
  }

  /* ── bus panel ── */
  #bus-panel {
    border-top: 1px solid var(--border);
    padding: 10px 14px;
    max-height: 140px;
    overflow-y: auto;
  }
  #bus-panel h3 {
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
  }
  .bus-entry {
    display: flex; gap: 8px; font-size: 11px; padding: 1px 0;
  }
  .bus-addr { color: var(--accent); }
  .bus-val  { color: #3fb950; }
  #bus-empty { color: var(--muted); font-size: 11px; font-style: italic; }

  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
</head>
<body>

<header>
  <h1>⬡ IMAGO UNICELL VISUALISER</h1>
  <div class="stat">Total: <span id="stat-total">—</span></div>
  <div class="stat">Allocated: <span id="stat-alloc">—</span></div>
  <div class="stat">Bus values: <span id="stat-bus">—</span></div>
</header>

<div class="controls">
  <button id="btn-step"  onclick="step()">Step ▶</button>
  <button id="btn-run"   onclick="toggleRun()">Run ▶▶</button>
  <button id="btn-reset" class="danger" onclick="resetView()">Reset ↺</button>
  <label>Speed:
    <input type="range" id="speed-slider" min="1" max="20" value="5">
  </label>
  <label>Zoom:
    <input type="range" id="zoom-slider"  min="16" max="56" value="32">
  </label>

  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#21262d;border:1.5px solid #30363d"></div>Blank</div>
    <div class="legend-item"><div class="legend-dot" style="background:#1f6feb"></div>Waiting</div>
    <div class="legend-item"><div class="legend-dot" style="background:#238636"></div>Fired</div>
    <div class="legend-item"><div class="legend-dot" style="background:#9a6700"></div>Memory</div>
    <div class="legend-item"><div class="legend-dot" style="background:#6e4a7e"></div>Halted</div>
    <div class="legend-item"><div class="legend-dot" style="background:#b08800"></div>Config</div>
  </div>

  <div id="cycle-display">Cycle: <span id="cycle-count">0</span></div>
</div>

<div class="main">
  <div id="grid-wrap">
    <div id="grid"></div>
  </div>

  <div id="side-panel">
    <h2>Cell Inspector</h2>
    <div id="cell-detail">
      <div id="no-selection">
        Click any cell to inspect its state.<br><br>
        Colour key:<br>
        Blue = configured, waiting for data<br>
        Green = fired this tick<br>
        Gold = loopback memory cell<br>
        Purple = halted (one-fire complete)<br>
        Dark = unallocated
      </div>
    </div>
    <div id="bus-panel">
      <h3>Bus State</h3>
      <div id="bus-content"><span id="bus-empty">Bus is empty</span></div>
    </div>
  </div>
</div>

<script>
let state       = null;
let cycleCount  = 0;
let running     = false;
let runTimer    = null;
let selectedIdx = null;
let cols        = 8;

// ── fetch state from server ──────────────────────────────────────────────────
async function fetchState() {
  try {
    const r = await fetch('/state');
    if (!r.ok) return null;
    return await r.json();
  } catch(e) { return null; }
}

async function sendCommand(cmd, body={}) {
  try {
    const r = await fetch('/cmd/' + cmd, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    return await r.json();
  } catch(e) { return null; }
}

// ── grid rendering ───────────────────────────────────────────────────────────
function renderGrid(data) {
  if (!data) return;
  state = data;

  const cells   = data.cells;
  const grid    = document.getElementById('grid');
  const zoom    = parseInt(document.getElementById('zoom-slider').value);
  const ncols   = Math.max(1, Math.floor((window.innerWidth - 320) / (zoom + 3)));
  cols          = ncols;

  grid.style.gridTemplateColumns = `repeat(${ncols}, ${zoom}px)`;

  // Add or update cell elements
  while (grid.children.length < cells.length) {
    const el = document.createElement('div');
    el.className = 'cell';
    const idx = grid.children.length;
    el.addEventListener('click', () => selectCell(idx));
    grid.appendChild(el);
  }
  while (grid.children.length > cells.length) {
    grid.removeChild(grid.lastChild);
  }

  cells.forEach((cell, i) => {
    const el = grid.children[i];
    el.setAttribute('data-state', cell.state);
    el.setAttribute('data-idx',   i);
    el.title = cell.address_hex;
    el.style.width  = zoom + 'px';
    el.style.height = zoom + 'px';
    el.style.fontSize = Math.max(7, zoom * 0.25) + 'px';

    // Show last nibble of address as label when zoomed in
    if (zoom >= 28) {
      el.textContent = cell.address_hex.slice(-3);
    } else {
      el.textContent = '';
    }

    if (i === selectedIdx) {
      el.classList.add('selected');
    } else {
      el.classList.remove('selected');
    }
  });

  // Update stats
  document.getElementById('stat-total').textContent = data.total_cells.toLocaleString();
  document.getElementById('stat-alloc').textContent = data.allocated;
  document.getElementById('stat-bus').textContent   = Object.keys(data.bus).length;

  // Update bus panel
  renderBus(data.bus);

  // Refresh inspector if something is selected
  if (selectedIdx !== null && cells[selectedIdx]) {
    renderInspector(cells[selectedIdx]);
  }
}

function renderBus(bus) {
  const content = document.getElementById('bus-content');
  const entries = Object.entries(bus);
  if (entries.length === 0) {
    content.innerHTML = '<span id="bus-empty">Bus is empty</span>';
    return;
  }
  content.innerHTML = entries.map(([addr, val]) =>
    `<div class="bus-entry">
      <span class="bus-addr">${addr}</span>
      <span class="bus-val">= ${val}</span>
    </div>`
  ).join('');
}

// ── cell inspector ───────────────────────────────────────────────────────────
function selectCell(idx) {
  selectedIdx = idx;
  const cells = state ? state.cells : [];
  if (!cells[idx]) return;

  // Update selection highlight
  document.querySelectorAll('.cell').forEach((el, i) => {
    el.classList.toggle('selected', i === idx);
  });

  renderInspector(cells[idx]);
}

function renderInspector(cell) {
  const detail = document.getElementById('cell-detail');

  const stateColour = {
    blank:       '#6e7681',
    waiting:     '#388bfd',
    fired:       '#3fb950',
    memory:      '#d29922',
    halted:      '#a371f7',
    configuring: '#f0d000',
  }[cell.state] || '#c9d1d9';

  const rows = [
    ['Address',     `<span style="color:#58a6ff">${cell.address_hex}</span>`],
    ['State',       `<span style="color:${stateColour}">${cell.state.toUpperCase()}</span>`],
    ['Gate state',  `<span style="color:#d29922">${cell.gate_state_bin}</span> (${cell.gate_state})`],
    ['Input addr',  cell.input_address],
    ['Output addr', cell.output_address],
    ['Is loopback', cell.is_loopback
        ? '<span class="on">YES — memory mode</span>'
        : '<span class="off">no</span>'],
    ['Start flag',  cell.start_flag
        ? '<span class="on">ASSERTED</span>'
        : '<span class="off">not asserted</span>'],
    ['Data',        cell.data !== null
        ? `<span class="on">${cell.data}</span>`
        : '<span class="off">None</span>'],
    ['Config mode', cell.config_mode
        ? '<span style="color:#f0d000">ACTIVE</span>'
        : '<span class="off">no</span>'],
  ];

  const gateHtml = cell.gate_details.map(g => {
    const on = g.startsWith('[ON]');
    return `<div class="gate-item ${on ? 'active' : 'inactive'}">${g}</div>`;
  }).join('');

  detail.innerHTML = rows.map(([label, value]) => `
    <div class="detail-row">
      <span class="detail-label">${label}</span>
      <span class="detail-value">${value}</span>
    </div>
  `).join('') + `
    <div style="margin-top:10px;color:#8b949e;font-size:11px;letter-spacing:1px;text-transform:uppercase">
      Gate topology
    </div>
    <div class="gate-list">${gateHtml}</div>
  `;
}

// ── simulation controls ───────────────────────────────────────────────────────
async function step() {
  const result = await sendCommand('step');
  if (result) {
    cycleCount++;
    document.getElementById('cycle-count').textContent = cycleCount;
    renderGrid(result);
  }
}

function toggleRun() {
  running = !running;
  const btn = document.getElementById('btn-run');
  if (running) {
    btn.textContent = 'Pause ⏸';
    btn.classList.add('active');
    scheduleRun();
  } else {
    btn.textContent = 'Run ▶▶';
    btn.classList.remove('active');
    if (runTimer) { clearTimeout(runTimer); runTimer = null; }
  }
}

async function scheduleRun() {
  if (!running) return;
  const speed = parseInt(document.getElementById('speed-slider').value);
  const delay = Math.round(1000 / speed);
  const result = await sendCommand('step');
  if (result) {
    cycleCount++;
    document.getElementById('cycle-count').textContent = cycleCount;
    renderGrid(result);
    // Stop automatically when no cells active
    const anyActive = result.cells.some(c =>
      c.state === 'waiting' || c.state === 'fired' || c.state === 'memory');
    if (!anyActive) {
      toggleRun();
      return;
    }
  }
  runTimer = setTimeout(scheduleRun, delay);
}

async function resetView() {
  await sendCommand('reset');
  cycleCount  = 0;
  selectedIdx = null;
  document.getElementById('cycle-count').textContent = '0';
  document.getElementById('cell-detail').innerHTML =
    '<div id="no-selection">Array reset. Load a program to begin.</div>';
  const data = await fetchState();
  renderGrid(data);
}

// ── zoom and resize ───────────────────────────────────────────────────────────
document.getElementById('zoom-slider').addEventListener('input', () => {
  if (state) renderGrid(state);
});
window.addEventListener('resize', () => {
  if (state) renderGrid(state);
});

// ── initial load ──────────────────────────────────────────────────────────────
(async () => {
  const data = await fetchState();
  renderGrid(data);
})();
</script>
</body>
</html>"""


# ── HTTP server ───────────────────────────────────────────────────────────────

class VisualiserHandler(http.server.BaseHTTPRequestHandler):
    """Minimal HTTP handler serving the visualiser page and API."""

    vis = None   # set by Visualiser before serving

    def log_message(self, fmt, *args):
        pass   # suppress access log noise

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self._send_html(HTML_PAGE)
        elif self.path == '/state':
            self._send_json(self.vis._snapshot())
        else:
            self._send_404()

    def do_POST(self):
        if self.path == '/cmd/step':
            self.vis._step()
            self._send_json(self.vis._snapshot())
        elif self.path == '/cmd/reset':
            self.vis._reset()
            self._send_json(self.vis._snapshot())
        else:
            self._send_404()

    def _send_html(self, html: str):
        body = html.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: dict):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _send_404(self):
        self.send_response(404)
        self.end_headers()


# ── Visualiser ────────────────────────────────────────────────────────────────

class Visualiser:
    """
    Attaches to a UniCellArray and serves a live visualiser in the browser.

    Usage:
        vis = Visualiser(array)
        vis.serve()           # blocks — opens browser, serves until Ctrl+C

    Or non-blocking:
        vis = Visualiser(array)
        vis.start_server()    # returns immediately
        # ... run simulation steps ...
        vis.stop_server()
    """

    def __init__(
        self,
        array: UniCellArray,
        port: int = 7420,
        initial_inputs: Optional[dict[int, int]] = None,
    ):
        self.array          = array
        self.port           = port
        self._initial_inputs = initial_inputs or {}
        self._recently_fired: set[int] = set()
        self._server        = None
        self._server_thread = None
        self._snapshot_cache = None

    # ── snapshot ──────────────────────────────────────────────────────────────

    def _snapshot(self) -> dict:
        snap = array_snapshot(self.array, self._recently_fired)
        self._recently_fired.clear()
        return snap

    # ── simulation step ───────────────────────────────────────────────────────

    def _step(self):
        """Execute one clock tick and record which cells fired."""
        # Track cells that were about to fire (had data + start_flag)
        about_to_fire = set()
        for addr, cell in self.array.cells.items():
            if cell.start_flag and cell.data is not None and not cell._config_mode:
                about_to_fire.add(addr)

        self.array.tick()

        # Cells that fired are those that were about to fire
        self._recently_fired = about_to_fire

    # ── reset ─────────────────────────────────────────────────────────────────

    def _reset(self):
        """Reset the array to its post-load state (re-assert start flag)."""
        self.array.assert_start_flag()
        if self._initial_inputs:
            for addr, val in self._initial_inputs.items():
                self.array.bus[addr] = val
        self._recently_fired.clear()

    # ── server lifecycle ──────────────────────────────────────────────────────

    def start_server(self):
        """Start the HTTP server in a background thread."""
        VisualiserHandler.vis = self

        self._server = http.server.HTTPServer(
            ('localhost', self.port), VisualiserHandler
        )
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
        )
        self._server_thread.start()
        imago_log.info(f"[VISUALISER] Serving at http://localhost:{self.port}")

    def stop_server(self):
        """Stop the HTTP server."""
        if self._server:
            self._server.shutdown()
            self._server = None
            imago_log.info("[VISUALISER] Server stopped")

    def serve(self, open_browser: bool = True):
        """
        Start the server and block until Ctrl+C.
        Opens the browser automatically unless open_browser=False.
        """
        self.start_server()
        url = f"http://localhost:{self.port}"

        if open_browser:
            # Give the server a moment to start
            time.sleep(0.3)
            webbrowser.open(url)
            imago_log.info(f"[VISUALISER] Browser opened at {url}")
        else:
            imago_log.info(f"[VISUALISER] Open {url} in your browser")

        imago_log.info("[VISUALISER] Press Ctrl+C to stop")
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print()
        finally:
            self.stop_server()


# ── standalone demo ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')

    from unicell import VAR_TRUE, VAR_FALSE
    from unicell_array import UniCellArray
    from controller import ImagoController, CellMapRecord
    from compiler import ImagoCompiler

    print("Building demo: XOR(1,0) through a 3-stage pipeline")

    # Compile XOR
    src = "def xor_demo(a, b):\n    return a ^ b\n"
    compiler = ImagoCompiler()
    records, graph, input_map, output_addrs = compiler.compile_function(
        src, "xor_demo", ["a", "b"]
    )

    # Load into controller
    ctrl = ImagoController(cell_count=200)
    rid = ctrl.load_map(records, "xor_demo")

    # Inject inputs
    ctrl.array.bus[input_map["a"]] = VAR_TRUE
    ctrl.array.bus[input_map["b"]] = VAR_FALSE
    ctrl.array.assert_start_flag()

    print(f"Loaded {len(records)} cells")
    print(f"Input a at 0x{input_map['a']:04X}, b at 0x{input_map['b']:04X}")
    print(f"Output at {[hex(a) for a in output_addrs]}")
    print()

    # Launch visualiser
    vis = Visualiser(
        ctrl.array,
        initial_inputs={
            input_map["a"]: VAR_TRUE,
            input_map["b"]: VAR_FALSE,
        }
    )
    vis.serve()
