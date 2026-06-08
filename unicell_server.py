"""
UniCell REST Server
===================
Exposes the UniCell compiler, TileLibrary, and execution backends
via a simple REST API. Clients are plain browser pages — no FPGA
drivers, no Python, no installation required on the client side.

Usage:
    python unicell_server.py [--host 0.0.0.0] [--port 5000]

Backends (selected per-request or auto):
    vm          Software simulation (always available)
    icebreaker  iCEBreaker iCE40UP5K (requires hardware)
    arria10     Arria 10 GX660 Mustang-F100 (requires hardware + programmer)

API:
    GET  /api/status                   Server and backend status
    GET  /api/backends                 Available backends
    GET  /api/models                   List all models
    GET  /api/models/<id>              Get model definition
    POST /api/run/<id>                 Run model with parameters
    GET  /api/job/<job_id>             Poll job status / get results
    GET  /                             Frontend HTML page
"""

import os, sys, json, uuid, time, threading, traceback, argparse
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory

# ── path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# ── UniCell imports ───────────────────────────────────────────────────────────
from fp_tiles import TileLibrary
from compiler_int32 import run_int32_function, Int32Compiler
from controller import ImagoController

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=str(ROOT / "frontend"))

# ── Global state ─────────────────────────────────────────────────────────────
_lib      = None   # TileLibrary singleton
_jobs     = {}     # {job_id: {status, result, error, started, finished}}
_jobs_lock = threading.Lock()

def get_library():
    global _lib
    if _lib is None:
        _lib = TileLibrary()
    return _lib


# ── Backend detection ─────────────────────────────────────────────────────────

# ── Hardware backend configuration ───────────────────────────────────────────
#
# Hardware backends communicate via serial port (UART bridge).
# Set the port for each card in hardware_config.json (auto-created on first run)
# or pass --icebreaker-port / --arria10-port on the command line.
#
# iCEBreaker setup:
#   1. Flash uart_bridge bitstream:  iceprog fpga/verilog/uart_bridge.bin
#   2. Find port:  ls /dev/ttyUSB*  (Linux)  or  Device Manager (Windows)
#   3. Set in hardware_config.json: {"icebreaker_port": "/dev/ttyUSB0"}
#   4. Restart server — iCEBreaker backend will show as available
#
# Arria 10 setup:
#   1. Program uart_bridge bitstream via Quartus Programmer (JTAG)
#   2. Find port: same as above — UART bridge exposes a serial port
#   3. Set in hardware_config.json: {"arria10_port": "/dev/ttyUSB1"}
#   4. Restart server — Arria 10 backend will show as available
#
# Same process for any future card — add a port entry, restart.
# The serial port is the universal hardware interface regardless of card type.

_HW_CONFIG_PATH = Path(__file__).parent / "hardware_config.json"

def load_hw_config() -> dict:
    """Load hardware_config.json — serial port assignments per backend."""
    if _HW_CONFIG_PATH.exists():
        try:
            with open(_HW_CONFIG_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_hw_config(cfg: dict):
    """Save hardware_config.json."""
    with open(_HW_CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"  Saved hardware config: {_HW_CONFIG_PATH}")


def _port_available(port: str) -> bool:
    """Check if a serial port exists and can be opened."""
    if not port:
        return False
    import serial
    try:
        s = serial.Serial(port, timeout=0.1)
        s.close()
        return True
    except Exception:
        return False


def detect_backends() -> dict:
    """
    Detect which backends are currently available.

    VM is always available. Hardware backends require a serial port
    configured in hardware_config.json and the UART bridge bitstream
    flashed to the card.
    """
    cfg = load_hw_config()

    backends = {
        "vm": {
            "id":          "vm",
            "name":        "Software VM",
            "description": "Software simulation — always available, no hardware required",
            "available":   True,
            "speed":       "slow",
            "scale":       "unlimited",
            "port":        None,
            "setup":       None,
        }
    }

    # ── iCEBreaker ────────────────────────────────────────────────────────────
    ice_port = cfg.get("icebreaker_port", "")
    ice_avail = _port_available(ice_port) if ice_port else False
    backends["icebreaker"] = {
        "id":          "icebreaker",
        "name":        "iCEBreaker (iCE40UP5K)",
        "description": (f"iCEBreaker on {ice_port}" if ice_avail
                        else "iCEBreaker — serial port not configured"),
        "available":   ice_avail,
        "speed":       "fast",
        "scale":       "~1000 cells",
        "port":        ice_port or None,
        "setup":       (None if ice_avail else
                        "Flash uart_bridge bitstream, then set "
                        "icebreaker_port in hardware_config.json"),
    }

    # ── Arria 10 ──────────────────────────────────────────────────────────────
    a10_port = cfg.get("arria10_port", "")
    a10_avail = _port_available(a10_port) if a10_port else False
    backends["arria10"] = {
        "id":          "arria10",
        "name":        "Arria 10 GX660",
        "description": (f"Arria 10 on {a10_port}" if a10_avail
                        else "Arria 10 — serial port not configured"),
        "available":   a10_avail,
        "speed":       "very fast",
        "scale":       "~660K cells",
        "port":        a10_port or None,
        "setup":       (None if a10_avail else
                        "Program uart_bridge bitstream via Quartus, then set "
                        "arria10_port in hardware_config.json"),
    }

    # Future cards follow the same pattern:
    # Add an entry in hardware_config.json, detect port here, done.

    return backends


# ── Model registry ────────────────────────────────────────────────────────────

def load_models():
    """Load model definitions from models/ directory."""
    models_dir = ROOT / "models"
    models_dir.mkdir(exist_ok=True)

    models = {}

    # Built-in models from MathTrix demo scripts
    builtin = [
        {
            "id":          "laplacian_1d",
            "name":        "1D Laplacian (Heat Diffusion)",
            "domain":      "MathTrix",
            "description": "1D heat equation — temperature diffuses along a line",
            "parameters": {
                "size":   {"type": "int",   "default": 64,  "min": 8,   "max": 512, "label": "Grid size"},
                "steps":  {"type": "int",   "default": 100, "min": 1,   "max": 1000,"label": "Timesteps"},
                "alpha":  {"type": "float", "default": 0.1, "min": 0.01,"max": 0.49,"label": "Diffusion rate"},
            },
            "tile_config": {},
            "tags": ["heat", "diffusion", "1D"],
        },
        {
            "id":          "laplacian_2d",
            "name":        "2D Laplacian (Heat Diffusion)",
            "domain":      "MathTrix",
            "description": "2D heat equation — radial diffusion on a grid",
            "parameters": {
                "width":  {"type": "int",   "default": 32,  "min": 8,  "max": 128, "label": "Width"},
                "height": {"type": "int",   "default": 32,  "min": 8,  "max": 128, "label": "Height"},
                "steps":  {"type": "int",   "default": 50,  "min": 1,  "max": 500, "label": "Timesteps"},
                "alpha":  {"type": "float", "default": 0.1, "min": 0.01,"max": 0.24,"label": "Diffusion rate"},
            },
            "tile_config": {},
            "tags": ["heat", "diffusion", "2D"],
        },
        {
            "id":          "gray_scott",
            "name":        "Gray-Scott (Turing Patterns)",
            "domain":      "MathTrix",
            "description": "Reaction-diffusion system producing Turing patterns",
            "parameters": {
                "size":   {"type": "int",   "default": 32,  "min": 8,  "max": 128, "label": "Grid size"},
                "steps":  {"type": "int",   "default": 100, "min": 1,  "max": 1000,"label": "Timesteps"},
                "F":      {"type": "float", "default": 0.055,"min": 0.01,"max": 0.1,"label": "Feed rate F"},
                "k":      {"type": "float", "default": 0.062,"min": 0.04,"max": 0.08,"label": "Kill rate k"},
            },
            "tile_config": {},
            "tags": ["reaction-diffusion", "patterns", "2D"],
        },
        {
            "id":          "nbody",
            "name":        "N-Body Gravity",
            "domain":      "MathTrix",
            "description": "Gravitational N-body simulation — pairwise forces",
            "parameters": {
                "n":      {"type": "int",   "default": 8,   "min": 2,  "max": 32,  "label": "Body count"},
                "steps":  {"type": "int",   "default": 50,  "min": 1,  "max": 500, "label": "Timesteps"},
                "dt":     {"type": "float", "default": 0.01,"min": 0.001,"max": 0.1,"label": "Timestep dt"},
            },
            "tile_config": {"MIF_DIV": "low_latency", "MIF_SQRT": "low_latency"},
            "tags": ["gravity", "physics", "N-body"],
        },
        {
            "id":          "pagerank",
            "name":        "PageRank",
            "domain":      "MathTrix",
            "description": "Graph diffusion / PageRank iteration",
            "parameters": {
                "nodes":  {"type": "int",   "default": 16,  "min": 4,  "max": 64,  "label": "Node count"},
                "steps":  {"type": "int",   "default": 20,  "min": 1,  "max": 200, "label": "Iterations"},
                "damping":{"type": "float", "default": 0.85,"min": 0.5,"max": 0.99,"label": "Damping factor"},
            },
            "tile_config": {"MIF_DIV": "const_divisor"},
            "tags": ["graph", "diffusion", "ranking"],
        },
        {
            "id":          "wave",
            "name":        "2D Wave Equation",
            "domain":      "MathTrix",
            "description": "2D wave propagation from a central Gaussian pulse",
            "parameters": {
                "size":   {"type": "int",   "default": 32,  "min": 8,  "max": 128, "label": "Grid size"},
                "steps":  {"type": "int",   "default": 50,  "min": 1,  "max": 500, "label": "Timesteps"},
                "c":      {"type": "float", "default": 0.3, "min": 0.1,"max": 0.7, "label": "Wave speed c"},
            },
            "tile_config": {},
            "tags": ["wave", "physics", "2D"],
        },
        {
            "id":          "ising",
            "name":        "Ising Model",
            "domain":      "MathTrix",
            "description": "2D Ising spin lattice — magnetic domain formation",
            "parameters": {
                "size":   {"type": "int",   "default": 32,  "min": 8,  "max": 128, "label": "Grid size"},
                "steps":  {"type": "int",   "default": 100, "min": 1,  "max": 1000,"label": "Timesteps"},
                "T":      {"type": "float", "default": 2.5, "min": 0.5,"max": 5.0, "label": "Temperature T"},
            },
            "tile_config": {},
            "tags": ["spin", "physics", "2D", "statistical"],
        },
        {
            "id":          "boids",
            "name":        "Boids Flocking",
            "domain":      "MathTrix",
            "description": "Reynolds boids — emergent flocking behaviour",
            "parameters": {
                "n":      {"type": "int",   "default": 16,  "min": 4,  "max": 64,  "label": "Boid count"},
                "steps":  {"type": "int",   "default": 50,  "min": 1,  "max": 500, "label": "Timesteps"},
            },
            "tile_config": {"MIF_DIV": "low_latency", "MIF_SQRT": "low_latency"},
            "tags": ["flocking", "emergence", "agents"],
        },
        {
            "id":          "conway",
            "name":        "Continuous Conway",
            "domain":      "MathTrix",
            "description": "Smooth Game of Life with continuous state",
            "parameters": {
                "size":   {"type": "int",   "default": 32,  "min": 8,  "max": 128, "label": "Grid size"},
                "steps":  {"type": "int",   "default": 50,  "min": 1,  "max": 500, "label": "Timesteps"},
            },
            "tile_config": {},
            "tags": ["cellular-automata", "emergence", "2D"],
        },
    ]

    for m in builtin:
        models[m["id"]] = m

    # Load any user-defined models from models/ directory
    for f in models_dir.glob("*.json"):
        try:
            with open(f) as fh:
                m = json.load(fh)
                if "id" in m:
                    models[m["id"]] = m
        except Exception as e:
            app.logger.warning(f"Could not load model {f}: {e}")

    return models


# ── Job execution ─────────────────────────────────────────────────────────────

def run_job(job_id, model_id, params, backend_id):
    """Execute a model run in a background thread."""
    with _jobs_lock:
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["started"] = time.time()

    try:
        models = load_models()
        if model_id not in models:
            raise ValueError(f"Unknown model: {model_id}")

        model       = models[model_id]
        lib         = get_library()
        tile_config = model.get("tile_config", {})

        # Dispatch to backend
        backends = detect_backends()
        if backend_id not in backends:
            raise ValueError(f"Unknown backend: {backend_id}")
        if not backends[backend_id]["available"]:
            setup = backends[backend_id].get("setup", "Check hardware_config.json")
            raise RuntimeError(
                f"Backend '{backend_id}' is not available. {setup}"
            )

        if backend_id == "vm":
            result = run_model_vm(model, params, lib, tile_config)
        else:
            port = backends[backend_id]["port"]
            result = run_model_hardware(model, params, lib, tile_config,
                                        backend_id=backend_id, port=port)

        with _jobs_lock:
            _jobs[job_id]["status"]   = "complete"
            _jobs[job_id]["result"]   = result
            _jobs[job_id]["finished"] = time.time()

    except Exception as e:
        with _jobs_lock:
            _jobs[job_id]["status"]   = "error"
            _jobs[job_id]["error"]    = str(e)
            _jobs[job_id]["trace"]    = traceback.format_exc()
            _jobs[job_id]["finished"] = time.time()


def run_model_hardware(model, params, lib, tile_config,
                       backend_id="icebreaker", port="/dev/ttyUSB0"):
    """
    Run a model on real FPGA hardware via the UART bridge.

    The UART bridge bitstream must already be flashed to the card.
    The serial port must be set in hardware_config.json.

    Flow:
      1. Compile model source to cell map using compiler + tile library
      2. Configure cells via FPGABridge.configure()
      3. Inject inputs via FPGABridge.inject()
      4. Read outputs via FPGABridge.read_output()
      5. Return results in same format as run_model_vm()

    This is the same interface regardless of card — iCEBreaker, Arria 10,
    or any future UniCell hardware. The port is the only difference.
    """
    from fpga_bridge import FPGABridge, FPGABridgeError
    from compiler_int32 import run_int32_function, Int32Compiler
    from controller import ImagoController

    start = time.time()
    model_id = model["id"]

    # ── Step 1: Compile model to cell map ─────────────────────────────────────
    # Models define their source and operands in their definition.
    # For MathTrix models, we compile a representative step function
    # and use the hardware to execute one timestep at a time.
    model_source  = model.get("source")
    model_fn      = model.get("function", "step")
    model_operands = model.get("default_operands", {})

    if not model_source:
        raise ValueError(
            f"Model '{model_id}' has no 'source' field — "
            f"hardware backend requires compiled source. "
            f"Use VM backend for models without explicit source."
        )

    compiler = Int32Compiler(tile_library=lib, tile_config=tile_config)
    records, graph, inputs, outputs, spans = \
        compiler.compile_int32_function(model_source, model_fn)

    num_cells = len(records)

    # ── Step 2: Open UART bridge and configure cells ───────────────────────────
    with FPGABridge(port=port, num_cells=num_cells) as bridge:

        # Configure each cell
        for rec in records:
            bridge.configure(
                cell_id    = rec.output_address,
                gate_state = rec.gate_state,
                input_addr = rec.input_address,
            )

        # Apply preloads
        for addr, val in (compiler._tile_preloads or {}).items():
            bridge.inject(addr, val)
        for addr, val in (compiler.known_values or {}).items():
            bridge.inject(addr, val)

        # ── Step 3: Inject inputs and run ─────────────────────────────────────
        # Use params to build input values
        input_vals = {}
        for param, bit_addrs in inputs.items():
            val = int(params.get(param, model_operands.get(param, 0)))
            for i, addr in enumerate(bit_addrs):
                bit = (val >> i) & 1
                input_vals[addr] = 0xFFFFFFFF if bit else 0

        for addr, val in input_vals.items():
            bridge.inject(addr, val)

        # ── Step 4: Read outputs ───────────────────────────────────────────────
        out_val = 0
        for i, addr in enumerate(outputs):
            result_bit = bridge.read_output(addr)
            if result_bit:
                out_val |= (1 << i)
        if out_val >= 2**31:
            out_val -= 2**32

    return {
        "model_id":   model_id,
        "backend":    backend_id,
        "port":       port,
        "params":     params,
        "elapsed_s":  round(time.time() - start, 3),
        "cells":      num_cells,
        "output": {
            "type":   "scalar",
            "value":  out_val,
            "title":  model["name"],
        },
    }


# ── Hardware config API endpoint ──────────────────────────────────────────────
# Allows the frontend to show setup instructions and port configuration.


def run_model_vm(model, params, lib, tile_config):
    """
    Run a model using the software VM backend.
    Returns a result dict with metadata and output data.
    """
    model_id = model["id"]
    start    = time.time()

    # Dispatch to per-model runner
    runners = {
        "laplacian_1d": run_laplacian_1d,
        "laplacian_2d": run_laplacian_2d,
        "gray_scott":   run_gray_scott,
        "nbody":        run_nbody,
        "pagerank":     run_pagerank,
        "wave":         run_wave,
        "ising":        run_ising,
        "boids":        run_boids,
        "conway":       run_conway,
    }

    if model_id not in runners:
        raise ValueError(f"No runner implemented for model: {model_id}")

    output = runners[model_id](params, lib, tile_config)

    return {
        "model_id":   model_id,
        "backend":    "vm",
        "params":     params,
        "elapsed_s":  round(time.time() - start, 3),
        "output":     output,
    }


# ── Per-model runners ─────────────────────────────────────────────────────────
# These are lightweight wrappers that call the existing MathTrix demo logic
# and return serialisable result dicts.

def run_laplacian_1d(params, lib, tile_config):
    size  = int(params.get("size", 64))
    steps = int(params.get("steps", 100))
    alpha = float(params.get("alpha", 0.1))

    # Initial condition: Gaussian pulse at centre
    import math
    u = [math.exp(-((i - size//2)**2) / (2*(size//8)**2)) for i in range(size)]

    # Simple finite-difference (VM mode — no fabric needed for demo)
    frames = [u[:]]
    for _ in range(steps):
        u_new = u[:]
        for i in range(1, size-1):
            u_new[i] = u[i] + alpha * (u[i-1] - 2*u[i] + u[i+1])
        u = u_new
        if _ % max(1, steps//10) == 0:
            frames.append(u[:])

    return {
        "type":   "timeseries_1d",
        "size":   size,
        "steps":  steps,
        "frames": frames,
        "xlabel": "Position",
        "ylabel": "Temperature",
        "title":  "1D Heat Diffusion",
    }


def run_laplacian_2d(params, lib, tile_config):
    import math
    w = int(params.get("width", 32))
    h = int(params.get("height", 32))
    steps = int(params.get("steps", 50))
    alpha = float(params.get("alpha", 0.1))

    u = [[math.exp(-((i-h//2)**2+(j-w//2)**2)/(2*(min(w,h)//6)**2))
          for j in range(w)] for i in range(h)]

    frames = [[row[:] for row in u]]
    for s in range(steps):
        u_new = [[0.0]*w for _ in range(h)]
        for i in range(1, h-1):
            for j in range(1, w-1):
                u_new[i][j] = u[i][j] + alpha*(
                    u[i-1][j]+u[i+1][j]+u[i][j-1]+u[i][j+1]-4*u[i][j])
        for i in range(h):
            u[i] = u_new[i][:]
        if s % max(1, steps//5) == 0:
            frames.append([row[:] for row in u])

    return {
        "type":   "timeseries_2d",
        "width":  w, "height": h,
        "steps":  steps,
        "frames": frames,
        "title":  "2D Heat Diffusion",
    }


def run_gray_scott(params, lib, tile_config):
    import math, random
    size  = int(params.get("size", 32))
    steps = int(params.get("steps", 100))
    F     = float(params.get("F", 0.055))
    k     = float(params.get("k", 0.062))
    Du, Dv = 0.16, 0.08

    u = [[1.0]*size for _ in range(size)]
    v = [[0.0]*size for _ in range(size)]
    # Seed
    for i in range(size//2-3, size//2+3):
        for j in range(size//2-3, size//2+3):
            u[i][j] = 0.5 + random.uniform(-0.01, 0.01)
            v[i][j] = 0.25 + random.uniform(-0.01, 0.01)

    frames = [[row[:] for row in v]]
    for s in range(steps):
        u_new = [[0.0]*size for _ in range(size)]
        v_new = [[0.0]*size for _ in range(size)]
        for i in range(size):
            for j in range(size):
                ip=(i+1)%size; im=(i-1)%size
                jp=(j+1)%size; jm=(j-1)%size
                lap_u = u[ip][j]+u[im][j]+u[i][jp]+u[i][jm]-4*u[i][j]
                lap_v = v[ip][j]+v[im][j]+v[i][jp]+v[i][jm]-4*v[i][j]
                uvv = u[i][j]*v[i][j]*v[i][j]
                u_new[i][j] = u[i][j] + Du*lap_u - uvv + F*(1-u[i][j])
                v_new[i][j] = v[i][j] + Dv*lap_v + uvv - (F+k)*v[i][j]
        u, v = u_new, v_new
        if s % max(1, steps//5) == 0:
            frames.append([row[:] for row in v])

    return {"type":"timeseries_2d","width":size,"height":size,
            "steps":steps,"frames":frames,"title":"Gray-Scott Turing Patterns"}


def run_nbody(params, lib, tile_config):
    import math, random
    n     = int(params.get("n", 8))
    steps = int(params.get("steps", 50))
    dt    = float(params.get("dt", 0.01))

    random.seed(42)
    pos = [[random.uniform(-1,1), random.uniform(-1,1)] for _ in range(n)]
    vel = [[0.0, 0.0] for _ in range(n)]
    mass = [1.0]*n

    trajectories = [[p[:] for p in pos]]
    for _ in range(steps):
        forces = [[0.0,0.0] for _ in range(n)]
        for i in range(n):
            for j in range(i+1,n):
                dx=pos[j][0]-pos[i][0]; dy=pos[j][1]-pos[i][1]
                r=math.sqrt(dx*dx+dy*dy+0.01)
                f=mass[i]*mass[j]/(r*r*r)
                forces[i][0]+=f*dx; forces[i][1]+=f*dy
                forces[j][0]-=f*dx; forces[j][1]-=f*dy
        for i in range(n):
            vel[i][0]+=forces[i][0]*dt/mass[i]
            vel[i][1]+=forces[i][1]*dt/mass[i]
            pos[i][0]+=vel[i][0]*dt
            pos[i][1]+=vel[i][1]*dt
        trajectories.append([p[:] for p in pos])

    return {"type":"trajectories","n":n,"steps":steps,
            "trajectories":trajectories,"title":"N-Body Gravity"}


def run_pagerank(params, lib, tile_config):
    import random
    nodes   = int(params.get("nodes", 16))
    steps   = int(params.get("steps", 20))
    damping = float(params.get("damping", 0.85))

    random.seed(42)
    # Random graph
    edges = {i: [j for j in range(nodes) if j!=i and random.random()<0.3]
             for i in range(nodes)}
    for i in range(nodes):
        if not edges[i]: edges[i] = [(i+1)%nodes]

    rank = [1.0/nodes]*nodes
    history = [rank[:]]
    for _ in range(steps):
        new_rank = [(1-damping)/nodes]*nodes
        for i in range(nodes):
            for j in edges[i]:
                new_rank[j] += damping * rank[i] / len(edges[i])
        rank = new_rank
        history.append(rank[:])

    return {"type":"rank_history","nodes":nodes,"steps":steps,
            "history":history,"title":"PageRank Convergence"}


def run_wave(params, lib, tile_config):
    import math
    size  = int(params.get("size", 32))
    steps = int(params.get("steps", 50))
    c     = float(params.get("c", 0.3))

    u     = [[math.exp(-((i-size//2)**2+(j-size//2)**2)/(2*(size//8)**2))
              for j in range(size)] for i in range(size)]
    u_prev = [row[:] for row in u]

    frames = [[row[:] for row in u]]
    for s in range(steps):
        u_new = [[0.0]*size for _ in range(size)]
        for i in range(1,size-1):
            for j in range(1,size-1):
                lap = u[i-1][j]+u[i+1][j]+u[i][j-1]+u[i][j+1]-4*u[i][j]
                u_new[i][j] = 2*u[i][j] - u_prev[i][j] + c*c*lap
        u_prev = [row[:] for row in u]
        u = u_new
        if s % max(1,steps//5) == 0:
            frames.append([row[:] for row in u])

    return {"type":"timeseries_2d","width":size,"height":size,
            "steps":steps,"frames":frames,"title":"2D Wave Equation"}


def run_ising(params, lib, tile_config):
    import math, random
    size  = int(params.get("size", 32))
    steps = int(params.get("steps", 100))
    T     = float(params.get("T", 2.5))

    random.seed(42)
    spins = [[random.choice([-1,1]) for _ in range(size)] for _ in range(size)]

    frames = [[row[:] for row in spins]]
    for s in range(steps):
        for _ in range(size*size):
            i=random.randint(0,size-1); j=random.randint(0,size-1)
            nb = (spins[(i-1)%size][j]+spins[(i+1)%size][j]+
                  spins[i][(j-1)%size]+spins[i][(j+1)%size])
            dE = 2*spins[i][j]*nb
            if dE<0 or random.random()<math.exp(-dE/T):
                spins[i][j]*=-1
        if s % max(1,steps//5) == 0:
            frames.append([row[:] for row in spins])

    return {"type":"timeseries_2d","width":size,"height":size,
            "steps":steps,"frames":frames,"title":"Ising Model"}


def run_boids(params, lib, tile_config):
    import math, random
    n     = int(params.get("n", 16))
    steps = int(params.get("steps", 50))

    random.seed(42)
    pos = [[random.uniform(0,1), random.uniform(0,1)] for _ in range(n)]
    vel = [[random.uniform(-0.02,0.02), random.uniform(-0.02,0.02)] for _ in range(n)]

    frames = [[p[:] for p in pos]]
    for _ in range(steps):
        for i in range(n):
            sep=[0.0,0.0]; aln=[0.0,0.0]; coh=[0.0,0.0]; cnt=0
            for j in range(n):
                if i==j: continue
                dx=pos[j][0]-pos[i][0]; dy=pos[j][1]-pos[i][1]
                d=math.sqrt(dx*dx+dy*dy)+1e-6
                if d<0.1:
                    sep[0]-=dx/d; sep[1]-=dy/d
                if d<0.2:
                    aln[0]+=vel[j][0]; aln[1]+=vel[j][1]
                    coh[0]+=pos[j][0]; coh[1]+=pos[j][1]; cnt+=1
            if cnt:
                coh[0]=coh[0]/cnt-pos[i][0]; coh[1]=coh[1]/cnt-pos[i][1]
            vel[i][0]+=0.05*sep[0]+0.05*aln[0]+0.01*coh[0]
            vel[i][1]+=0.05*sep[1]+0.05*aln[1]+0.01*coh[1]
            spd=math.sqrt(vel[i][0]**2+vel[i][1]**2)+1e-6
            if spd>0.03: vel[i][0]*=0.03/spd; vel[i][1]*=0.03/spd
            pos[i][0]=(pos[i][0]+vel[i][0])%1.0
            pos[i][1]=(pos[i][1]+vel[i][1])%1.0
        frames.append([p[:] for p in pos])

    return {"type":"trajectories","n":n,"steps":steps,
            "trajectories":frames,"title":"Boids Flocking"}


def run_conway(params, lib, tile_config):
    import random
    size  = int(params.get("size", 32))
    steps = int(params.get("steps", 50))

    random.seed(42)
    grid = [[random.random() for _ in range(size)] for _ in range(size)]

    frames = [[row[:] for row in grid]]
    for s in range(steps):
        new_grid = [[0.0]*size for _ in range(size)]
        for i in range(size):
            for j in range(size):
                nb=sum(grid[(i+di)%size][(j+dj)%size]
                       for di in[-1,0,1] for dj in[-1,0,1] if (di,dj)!=(0,0))
                c=grid[i][j]
                if c>0.5:
                    new_grid[i][j]=1.0 if 1.5<nb<3.5 else max(0.0,c-0.1)
                else:
                    new_grid[i][j]=min(1.0,c+0.05) if 2.5<nb<3.5 else max(0.0,c-0.05)
        grid=new_grid
        if s % max(1,steps//5) == 0:
            frames.append([row[:] for row in grid])

    return {"type":"timeseries_2d","width":size,"height":size,
            "steps":steps,"frames":frames,"title":"Continuous Conway"}


# ── REST API endpoints ────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    backends = detect_backends()
    available = [b["id"] for b in backends.values() if b["available"]]
    return jsonify({
        "status":    "ok",
        "version":   "1.0.0",
        "backends":  backends,
        "available": available,
        "jobs":      len(_jobs),
    })


@app.route("/api/backends")
def api_backends():
    return jsonify(detect_backends())


@app.route("/api/hardware", methods=["GET", "POST"])
def api_hardware():
    """
    GET  /api/hardware  — return current hardware config + setup instructions
    POST /api/hardware  — update hardware config (set port for a backend)

    POST body: {"backend": "icebreaker", "port": "/dev/ttyUSB0"}
    """
    if request.method == "POST":
        body    = request.json or {}
        backend = body.get("backend")
        port    = body.get("port", "")
        if backend not in ("icebreaker", "arria10"):
            return jsonify({"error": "Unknown backend"}), 400
        cfg = load_hw_config()
        cfg[f"{backend}_port"] = port
        save_hw_config(cfg)
        # Re-detect to confirm
        backends = detect_backends()
        return jsonify({
            "ok":      True,
            "backend": backends.get(backend),
        })
    else:
        cfg      = load_hw_config()
        backends = detect_backends()
        return jsonify({
            "config":   cfg,
            "backends": backends,
            "instructions": {
                "icebreaker": [
                    "1. Flash UART bridge bitstream:",
                    "   iceprog fpga/verilog/uart_bridge.bin",
                    "2. Find serial port:",
                    "   Linux:   ls /dev/ttyUSB*",
                    "   Windows: Device Manager → Ports (COM & LPT)",
                    "3. Set port via POST /api/hardware or edit hardware_config.json:",
                    '   {"icebreaker_port": "/dev/ttyUSB0"}',
                    "4. Restart server",
                ],
                "arria10": [
                    "1. Program UART bridge bitstream via Quartus Programmer",
                    "   (requires Waveshare USB Blaster V2 + JST SH cable)",
                    "2. Find serial port (same as iCEBreaker above)",
                    "3. Set port via POST /api/hardware or edit hardware_config.json:",
                    '   {"arria10_port": "/dev/ttyUSB1"}',
                    "4. Restart server",
                ],
                "future_cards": [
                    "Any UniCell hardware with a UART bridge follows the same steps.",
                    "Add a new port entry to hardware_config.json and restart.",
                ],
            },
        })


@app.route("/api/models")
def api_models():
    models = load_models()
    # Return summary list (no full runner code)
    summary = [{
        "id":          m["id"],
        "name":        m["name"],
        "domain":      m.get("domain", "General"),
        "description": m["description"],
        "tags":        m.get("tags", []),
        "parameters":  m["parameters"],
    } for m in models.values()]
    return jsonify(summary)


@app.route("/api/models/<model_id>")
def api_model(model_id):
    models = load_models()
    if model_id not in models:
        return jsonify({"error": f"Model '{model_id}' not found"}), 404
    return jsonify(models[model_id])


@app.route("/api/run/<model_id>", methods=["POST"])
def api_run(model_id):
    params     = request.json or {}
    backend_id = params.pop("backend", "vm")

    job_id = str(uuid.uuid4())[:8]
    with _jobs_lock:
        _jobs[job_id] = {
            "status":   "queued",
            "model_id": model_id,
            "backend":  backend_id,
            "params":   params,
            "result":   None,
            "error":    None,
            "queued":   time.time(),
            "started":  None,
            "finished": None,
        }

    t = threading.Thread(target=run_job, args=(job_id, model_id, params, backend_id), daemon=True)
    t.start()

    return jsonify({"job_id": job_id, "status": "queued"})


@app.route("/api/job/<job_id>")
def api_job(job_id):
    with _jobs_lock:
        if job_id not in _jobs:
            return jsonify({"error": "Job not found"}), 404
        job = dict(_jobs[job_id])
    return jsonify(job)


@app.route("/")
def frontend():
    frontend_dir = ROOT / "frontend"
    if (frontend_dir / "index.html").exists():
        return send_from_directory(str(frontend_dir), "index.html")
    # Fallback inline page if frontend/ not yet built
    return _inline_frontend()


def _inline_frontend():
    """Minimal inline frontend — replaced by proper frontend/index.html."""
    return """<!DOCTYPE html>
<html>
<head>
<title>UniCell Compute</title>
<style>
  body { font-family: sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; background: #0a0a0a; color: #e0e0e0; }
  h1 { color: #00aaff; } h2 { color: #888; font-size: 1em; font-weight: normal; margin-top: 0; }
  .card { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 20px; margin: 16px 0; cursor: pointer; }
  .card:hover { border-color: #00aaff; }
  .card h3 { margin: 0 0 8px 0; color: #fff; }
  .tag { background: #222; border: 1px solid #444; border-radius: 4px; padding: 2px 8px; font-size: 0.75em; margin-right: 4px; }
  .status { padding: 12px; background: #1a1a1a; border-radius: 6px; margin-bottom: 20px; font-size: 0.9em; }
  .ok { color: #00cc66; } .warn { color: #ffaa00; }
  button { background: #00aaff; color: #000; border: none; padding: 10px 24px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 1em; }
  button:hover { background: #0088dd; }
  canvas { border: 1px solid #333; border-radius: 4px; }
  #result { margin-top: 20px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
</style>
</head>
<body>
<h1>⬡ UniCell Compute</h1>
<h2>Parallel fabric compute — browser interface</h2>
<div class="status" id="status">Connecting...</div>
<div id="view-list">
  <div class="grid" id="model-grid"></div>
</div>
<div id="view-run" style="display:none">
  <button onclick="showList()">← Back</button>
  <h3 id="run-title"></h3>
  <div id="param-form"></div><br>
  <button onclick="runModel()">▶ Run</button>
  <div id="result"></div>
</div>
<script>
let currentModel = null;

async function loadStatus() {
  const r = await fetch('/api/status');
  const d = await r.json();
  const avail = d.available.join(', ');
  document.getElementById('status').innerHTML =
    '<span class="ok">●</span> Server online &nbsp;|&nbsp; Backends: ' + avail;
}

async function loadModels() {
  const r = await fetch('/api/models');
  const models = await r.json();
  const grid = document.getElementById('model-grid');
  grid.innerHTML = '';
  models.forEach(m => {
    const div = document.createElement('div');
    div.className = 'card';
    div.onclick = () => showRun(m);
    div.innerHTML = '<h3>' + m.name + '</h3>' +
      '<p style="font-size:0.85em;color:#aaa;margin:4px 0 10px">' + m.description + '</p>' +
      m.tags.map(t => '<span class="tag">' + t + '</span>').join('');
    grid.appendChild(div);
  });
}

function showRun(model) {
  currentModel = model;
  document.getElementById('run-title').textContent = model.name;
  const form = document.getElementById('param-form');
  form.innerHTML = Object.entries(model.parameters).map(([k,p]) =>
    '<label style="display:block;margin:8px 0">' + p.label +
    ': <input id="p_' + k + '" type="' + (p.type==='int'||p.type==='float'?'number':'text') +
    '" value="' + p.default + '" step="' + (p.type==='float'?'any':'1') +
    '" style="background:#222;color:#fff;border:1px solid #444;border-radius:4px;padding:4px 8px;margin-left:8px"></label>'
  ).join('');
  document.getElementById('view-list').style.display = 'none';
  document.getElementById('view-run').style.display = 'block';
  document.getElementById('result').innerHTML = '';
}

function showList() {
  document.getElementById('view-list').style.display = 'block';
  document.getElementById('view-run').style.display = 'none';
}

async function runModel() {
  const params = {};
  Object.keys(currentModel.parameters).forEach(k => {
    const el = document.getElementById('p_' + k);
    const p = currentModel.parameters[k];
    params[k] = p.type === 'int' ? parseInt(el.value) :
                p.type === 'float' ? parseFloat(el.value) : el.value;
  });
  document.getElementById('result').innerHTML = '<p style="color:#888">Running...</p>';
  const r = await fetch('/api/run/' + currentModel.id, {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify(params)
  });
  const job = await r.json();
  pollJob(job.job_id);
}

async function pollJob(jobId) {
  const r = await fetch('/api/job/' + jobId);
  const job = await r.json();
  if (job.status === 'complete') {
    renderResult(job.result);
  } else if (job.status === 'error') {
    document.getElementById('result').innerHTML =
      '<p style="color:#ff4444">Error: ' + job.error + '</p>';
  } else {
    setTimeout(() => pollJob(jobId), 500);
  }
}

function renderResult(result) {
  const div = document.getElementById('result');
  if (!result) { div.innerHTML = '<p>No result</p>'; return; }

  const info = '<p style="color:#888;font-size:0.85em">Completed in ' +
    result.elapsed_s + 's on ' + result.backend + ' backend</p>';

  if (result.output.type === 'timeseries_2d') {
    const frames = result.output.frames;
    const w = result.output.width, h = result.output.height;
    const scale = Math.max(1, Math.floor(280/Math.max(w,h)));
    div.innerHTML = info + '<canvas id="c" width="' + w*scale + '" height="' + h*scale + '"></canvas>' +
      '<br><input type="range" id="frame-slider" min="0" max="' + (frames.length-1) + '" value="0" style="width:' + w*scale + 'px">';
    const ctx = document.getElementById('c').getContext('2d');
    function drawFrame(fi) {
      const frame = frames[fi];
      let mn=Infinity, mx=-Infinity;
      frame.forEach(row => row.forEach(v => { if(v<mn)mn=v; if(v>mx)mx=v; }));
      const rng = mx-mn || 1;
      const img = ctx.createImageData(w*scale, h*scale);
      for(let i=0;i<h;i++) for(let j=0;j<w;j++) {
        const t = (frame[i][j]-mn)/rng;
        const r = Math.round(t*255), b = Math.round((1-t)*255);
        for(let di=0;di<scale;di++) for(let dj=0;dj<scale;dj++) {
          const idx=((i*scale+di)*w*scale+(j*scale+dj))*4;
          img.data[idx]=r; img.data[idx+1]=0; img.data[idx+2]=b; img.data[idx+3]=255;
        }
      }
      ctx.putImageData(img,0,0);
    }
    drawFrame(0);
    document.getElementById('frame-slider').oninput = e => drawFrame(+e.target.value);

  } else if (result.output.type === 'timeseries_1d') {
    const frames = result.output.frames;
    div.innerHTML = info + '<canvas id="c" width="400" height="200"></canvas>' +
      '<br><input type="range" id="frame-slider" min="0" max="' + (frames.length-1) + '" value="0" style="width:400px">';
    const ctx = document.getElementById('c').getContext('2d');
    function drawFrame(fi) {
      const frame = frames[fi];
      ctx.fillStyle='#111'; ctx.fillRect(0,0,400,200);
      ctx.strokeStyle='#00aaff'; ctx.lineWidth=2;
      ctx.beginPath();
      frame.forEach((v,i) => {
        const x=i/frame.length*400, y=200-(v+0.1)/1.2*180;
        i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
      });
      ctx.stroke();
    }
    drawFrame(0);
    document.getElementById('frame-slider').oninput = e => drawFrame(+e.target.value);

  } else if (result.output.type === 'trajectories') {
    const frames = result.output.trajectories;
    div.innerHTML = info + '<canvas id="c" width="300" height="300"></canvas>' +
      '<br><input type="range" id="frame-slider" min="0" max="' + (frames.length-1) + '" value="0" style="width:300px">';
    const ctx = document.getElementById('c').getContext('2d');
    const colors=['#00aaff','#ff6600','#00cc66','#ff00aa','#ffcc00','#aa00ff','#00ffcc','#ff3333'];
    function drawFrame(fi) {
      ctx.fillStyle='#111'; ctx.fillRect(0,0,300,300);
      frames[fi].forEach((p,i) => {
        ctx.fillStyle=colors[i%colors.length];
        ctx.beginPath();
        ctx.arc((p[0]%1+1)%1*280+10, (p[1]%1+1)%1*280+10, 5, 0, Math.PI*2);
        ctx.fill();
      });
    }
    drawFrame(0);
    document.getElementById('frame-slider').oninput = e => drawFrame(+e.target.value);

  } else if (result.output.type === 'rank_history') {
    const history = result.output.history;
    const n = result.output.nodes;
    div.innerHTML = info + '<canvas id="c" width="400" height="200"></canvas>';
    const ctx = document.getElementById('c').getContext('2d');
    const colors=['#00aaff','#ff6600','#00cc66','#ff00aa','#ffcc00'];
    ctx.fillStyle='#111'; ctx.fillRect(0,0,400,200);
    for(let i=0;i<Math.min(n,5);i++) {
      ctx.strokeStyle=colors[i%colors.length]; ctx.lineWidth=1.5;
      ctx.beginPath();
      history.forEach((ranks,s) => {
        const x=s/history.length*400, y=200-ranks[i]*180*n;
        s===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
      });
      ctx.stroke();
    }
  } else {
    div.innerHTML = info + '<pre style="font-size:0.75em;color:#888">' +
      JSON.stringify(result.output, null, 2).slice(0, 500) + '</pre>';
  }
}

loadStatus();
loadModels();
</script>
</body>
</html>""", 200, {'Content-Type': 'text/html'}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UniCell REST Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Flask debug mode")
    args = parser.parse_args()

    print(f"\n  ⬡ UniCell Compute Server")
    print(f"  ─────────────────────────")
    print(f"  Listening on http://{args.host}:{args.port}")
    print(f"  Open http://localhost:{args.port} in a browser")
    print(f"  On your tablet: http://<this-machine-ip>:{args.port}\n")

    # Pre-load the tile library
    print("  Loading TileLibrary...", end=" ", flush=True)
    get_library()
    print("ready.")

    # Show backend status
    backends = detect_backends()
    print(f"\n  Backends:")
    for b in backends.values():
        avail = "✓" if b["available"] else "✗"
        port  = f"  [{b['port']}]" if b.get("port") else ""
        setup = f"  → {b['setup']}" if b.get("setup") else ""
        print(f"    {avail} {b['name']}{port}{setup}")

    hw_available = any(b["available"] for k, b in backends.items() if k != "vm")
    if not hw_available:
        print(f"\n  Hardware backends: none configured")
        print(f"  To add hardware: edit hardware_config.json or GET /api/hardware")
        print(f"  All jobs will run on the VM backend until hardware is configured.")
    print()

    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
