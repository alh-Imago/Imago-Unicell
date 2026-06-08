"""
unicell_model_library.py — Unified Model Library for UniCell Server
====================================================================
Two entry points, one interface:

  1. SYSTEM models — built-in, tile-based, registered in model_library.py
     These are compiled MathTrix/BioTrix/etc models. Immutable at runtime.
     Source: model_library.ModelLibrary (fp_tiles + compiler)

  2. USER models — JSON files in models/ directory
     Created by users via the API or by dropping JSON files in models/.
     Mutable: can be added, updated, deleted at runtime.
     Source: models/*.json

Both types are surfaced through the same API.
The server never needs to know which type it's dealing with.

User model JSON format:
-----------------------
{
  "id":          "my_reaction_diffusion",
  "name":        "My Reaction Diffusion",
  "domain":      "Custom",
  "description": "Custom Gray-Scott variant with different parameters",
  "author":      "alan",
  "created":     "2026-06-08T14:30:00",
  "tags":        ["reaction-diffusion", "custom"],
  "parameters": {
    "size":  {"type": "int",   "default": 32, "min": 8, "max": 128, "label": "Grid size"},
    "steps": {"type": "int",   "default": 50, "min": 1, "max": 500, "label": "Timesteps"},
    "F":     {"type": "float", "default": 0.04, "min": 0.01, "max": 0.1, "label": "Feed rate"},
    "k":     {"type": "float", "default": 0.06, "min": 0.04, "max": 0.08, "label": "Kill rate"}
  },
  "tile_config": {},
  "source":      "optional: Python source for hardware backend",
  "base_model":  "optional: ID of built-in model this extends"
}

API:
----
  GET  /api/library              All models (system + user), filterable
  GET  /api/library/<id>         Single model
  POST /api/library              Create user model
  PUT  /api/library/<id>         Update user model
  DELETE /api/library/<id>       Delete user model (user models only)
  GET  /api/library/domains      List domains (MathTrix, BioTrix, Custom...)
  GET  /api/library/tags         All tags across all models
"""

import json, time, uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────────
_ROOT       = Path(__file__).parent
_USER_DIR   = _ROOT / "models"
_USER_DIR.mkdir(exist_ok=True)

# ── System model definitions ──────────────────────────────────────────────────
# These mirror the built-in models in unicell_server.py but are now
# the canonical source. unicell_server.py load_models() will delegate here.

SYSTEM_MODELS = [
    {
        "id":          "laplacian_1d",
        "name":        "1D Laplacian",
        "domain":      "MathTrix",
        "description": "1D heat equation — temperature diffuses along a line",
        "author":      "system",
        "tags":        ["heat", "diffusion", "1D", "PDE"],
        "parameters": {
            "size":  {"type": "int",   "default": 64,  "min": 8,   "max": 512,  "label": "Grid size"},
            "steps": {"type": "int",   "default": 100, "min": 1,   "max": 1000, "label": "Timesteps"},
            "alpha": {"type": "float", "default": 0.1, "min": 0.01,"max": 0.49, "label": "Diffusion rate α"},
        },
        "tile_config": {},
        "system":      True,
    },
    {
        "id":          "laplacian_2d",
        "name":        "2D Laplacian",
        "domain":      "MathTrix",
        "description": "2D heat equation — radial diffusion on a grid",
        "author":      "system",
        "tags":        ["heat", "diffusion", "2D", "PDE"],
        "parameters": {
            "width":  {"type": "int",   "default": 32,  "min": 8,  "max": 128,  "label": "Width"},
            "height": {"type": "int",   "default": 32,  "min": 8,  "max": 128,  "label": "Height"},
            "steps":  {"type": "int",   "default": 50,  "min": 1,  "max": 500,  "label": "Timesteps"},
            "alpha":  {"type": "float", "default": 0.1, "min": 0.01,"max": 0.24,"label": "Diffusion rate α"},
        },
        "tile_config": {},
        "system":      True,
    },
    {
        "id":          "gray_scott",
        "name":        "Gray-Scott",
        "domain":      "MathTrix",
        "description": "Reaction-diffusion system producing Turing patterns",
        "author":      "system",
        "tags":        ["reaction-diffusion", "Turing", "patterns", "2D"],
        "parameters": {
            "size":  {"type": "int",   "default": 32,   "min": 8,   "max": 128, "label": "Grid size"},
            "steps": {"type": "int",   "default": 100,  "min": 1,   "max": 1000,"label": "Timesteps"},
            "F":     {"type": "float", "default": 0.055,"min": 0.01,"max": 0.1, "label": "Feed rate F"},
            "k":     {"type": "float", "default": 0.062,"min": 0.04,"max": 0.08,"label": "Kill rate k"},
        },
        "tile_config": {},
        "system":      True,
    },
    {
        "id":          "nbody",
        "name":        "N-Body Gravity",
        "domain":      "MathTrix",
        "description": "Gravitational N-body simulation — pairwise forces",
        "author":      "system",
        "tags":        ["gravity", "physics", "N-body", "particles"],
        "parameters": {
            "n":     {"type": "int",   "default": 8,   "min": 2,  "max": 32,  "label": "Body count"},
            "steps": {"type": "int",   "default": 50,  "min": 1,  "max": 500, "label": "Timesteps"},
            "dt":    {"type": "float", "default": 0.01,"min": 0.001,"max": 0.1,"label": "Timestep dt"},
        },
        "tile_config": {"MIF_DIV": "low_latency", "MIF_SQRT": "low_latency"},
        "system":      True,
    },
    {
        "id":          "pagerank",
        "name":        "PageRank",
        "domain":      "MathTrix",
        "description": "Graph diffusion / PageRank iteration",
        "author":      "system",
        "tags":        ["graph", "diffusion", "ranking", "network"],
        "parameters": {
            "nodes":   {"type": "int",   "default": 16,  "min": 4,  "max": 64,  "label": "Node count"},
            "steps":   {"type": "int",   "default": 20,  "min": 1,  "max": 200, "label": "Iterations"},
            "damping": {"type": "float", "default": 0.85,"min": 0.5,"max": 0.99,"label": "Damping factor d"},
        },
        "tile_config": {"MIF_DIV": "const_divisor"},
        "system":      True,
    },
    {
        "id":          "wave",
        "name":        "2D Wave Equation",
        "domain":      "MathTrix",
        "description": "2D wave propagation from a central Gaussian pulse",
        "author":      "system",
        "tags":        ["wave", "physics", "2D", "PDE"],
        "parameters": {
            "size":  {"type": "int",   "default": 32,  "min": 8,  "max": 128, "label": "Grid size"},
            "steps": {"type": "int",   "default": 50,  "min": 1,  "max": 500, "label": "Timesteps"},
            "c":     {"type": "float", "default": 0.3, "min": 0.1,"max": 0.7, "label": "Wave speed c"},
        },
        "tile_config": {},
        "system":      True,
    },
    {
        "id":          "ising",
        "name":        "Ising Model",
        "domain":      "MathTrix",
        "description": "2D Ising spin lattice — magnetic domain coarsening",
        "author":      "system",
        "tags":        ["spin", "physics", "2D", "statistical-mechanics"],
        "parameters": {
            "size":  {"type": "int",   "default": 32,  "min": 8,  "max": 128, "label": "Grid size"},
            "steps": {"type": "int",   "default": 100, "min": 1,  "max": 1000,"label": "Timesteps"},
            "T":     {"type": "float", "default": 2.5, "min": 0.5,"max": 5.0, "label": "Temperature T"},
        },
        "tile_config": {},
        "system":      True,
    },
    {
        "id":          "boids",
        "name":        "Boids Flocking",
        "domain":      "MathTrix",
        "description": "Reynolds boids — emergent flocking behaviour",
        "author":      "system",
        "tags":        ["flocking", "emergence", "agents", "swarm"],
        "parameters": {
            "n":     {"type": "int",   "default": 16, "min": 4,  "max": 64,  "label": "Boid count"},
            "steps": {"type": "int",   "default": 50, "min": 1,  "max": 500, "label": "Timesteps"},
        },
        "tile_config": {"MIF_DIV": "low_latency", "MIF_SQRT": "low_latency"},
        "system":      True,
    },
    {
        "id":          "conway",
        "name":        "Continuous Conway",
        "domain":      "MathTrix",
        "description": "Smooth Game of Life with continuous cell state",
        "author":      "system",
        "tags":        ["cellular-automata", "emergence", "2D", "Game-of-Life"],
        "parameters": {
            "size":  {"type": "int",   "default": 32, "min": 8,  "max": 128, "label": "Grid size"},
            "steps": {"type": "int",   "default": 50, "min": 1,  "max": 500, "label": "Timesteps"},
        },
        "tile_config": {},
        "system":      True,
    },
    {
        "id":          "fast_marching",
        "name":        "Fast Marching",
        "domain":      "MathTrix",
        "description": "Wavefront propagation — geodesic distance on a grid",
        "author":      "system",
        "tags":        ["wavefront", "geodesic", "pathfinding", "2D"],
        "parameters": {
            "size":  {"type": "int",   "default": 32, "min": 8,  "max": 128, "label": "Grid size"},
            "steps": {"type": "int",   "default": 50, "min": 1,  "max": 500, "label": "Timesteps"},
        },
        "tile_config": {},
        "system":      True,
    },
]


# ── User model CRUD ───────────────────────────────────────────────────────────

def _user_path(model_id: str) -> Path:
    """Return path for a user model JSON file."""
    # Sanitise ID — alphanumeric + underscore + hyphen only
    safe = "".join(c for c in model_id if c.isalnum() or c in "-_")
    return _USER_DIR / f"{safe}.json"


def load_user_models() -> dict:
    """Load all user models from models/ directory."""
    models = {}
    for f in sorted(_USER_DIR.glob("*.json")):
        try:
            with open(f) as fh:
                m = json.load(fh)
                if "id" in m:
                    m["system"] = False
                    models[m["id"]] = m
        except Exception as e:
            print(f"  Warning: could not load user model {f.name}: {e}")
    return models


def save_user_model(model: dict) -> dict:
    """Save a user model to models/ directory. Returns saved model."""
    model_id = model.get("id")
    if not model_id:
        raise ValueError("Model must have an 'id' field")

    # Prevent overwriting system models
    system_ids = {m["id"] for m in SYSTEM_MODELS}
    if model_id in system_ids:
        raise ValueError(f"Cannot overwrite system model '{model_id}'")

    # Stamp metadata
    now = datetime.utcnow().isoformat()
    if "created" not in model:
        model["created"] = now
    model["updated"]  = now
    model["system"]   = False

    path = _user_path(model_id)
    with open(path, "w") as f:
        json.dump(model, f, indent=2)

    return model


def delete_user_model(model_id: str) -> bool:
    """Delete a user model. Returns True if deleted, False if not found."""
    system_ids = {m["id"] for m in SYSTEM_MODELS}
    if model_id in system_ids:
        raise ValueError(f"Cannot delete system model '{model_id}'")

    path = _user_path(model_id)
    if path.exists():
        path.unlink()
        return True
    return False


# ── Unified library ───────────────────────────────────────────────────────────

def all_models(domain: Optional[str] = None,
               tag: Optional[str] = None,
               search: Optional[str] = None) -> list:
    """
    Return all models — system + user — with optional filtering.

    domain: filter by domain string (e.g. 'MathTrix', 'Custom')
    tag:    filter by tag (e.g. 'physics', '2D')
    search: filter by name/description substring (case-insensitive)

    System models come first, then user models alphabetically.
    """
    # System models (immutable)
    models = list(SYSTEM_MODELS)

    # User models (from models/ directory)
    user = load_user_models()
    # Don't include user models that shadow system IDs
    system_ids = {m["id"] for m in models}
    for mid, m in user.items():
        if mid not in system_ids:
            models.append(m)

    # Apply filters
    if domain:
        models = [m for m in models if m.get("domain", "") == domain]
    if tag:
        models = [m for m in models if tag in m.get("tags", [])]
    if search:
        s = search.lower()
        models = [m for m in models
                  if s in m.get("name", "").lower()
                  or s in m.get("description", "").lower()]

    return models


def get_model(model_id: str) -> Optional[dict]:
    """Return a single model by ID (system or user)."""
    # Check system first
    for m in SYSTEM_MODELS:
        if m["id"] == model_id:
            return m
    # Then user
    user = load_user_models()
    return user.get(model_id)


def all_domains() -> list:
    """Return sorted list of all domains across all models."""
    domains = set()
    for m in all_models():
        d = m.get("domain")
        if d:
            domains.add(d)
    return sorted(domains)


def all_tags() -> list:
    """Return sorted list of all tags across all models."""
    tags = set()
    for m in all_models():
        for t in m.get("tags", []):
            tags.add(t)
    return sorted(tags)


def create_user_model(spec: dict) -> dict:
    """
    Create a new user model.
    Generates an ID if not provided.
    Returns the saved model.
    """
    if "id" not in spec:
        # Generate ID from name or UUID
        name = spec.get("name", "")
        if name:
            base = name.lower().replace(" ", "_")
            base = "".join(c for c in base if c.isalnum() or c == "_")
            spec["id"] = base
        else:
            spec["id"] = f"model_{uuid.uuid4().hex[:8]}"

    # Ensure required fields
    spec.setdefault("name",        spec["id"])
    spec.setdefault("domain",      "Custom")
    spec.setdefault("description", "")
    spec.setdefault("author",      "user")
    spec.setdefault("tags",        [])
    spec.setdefault("parameters",  {})
    spec.setdefault("tile_config", {})

    return save_user_model(spec)


def update_user_model(model_id: str, updates: dict) -> dict:
    """
    Update an existing user model.
    Raises ValueError if model not found or is a system model.
    """
    existing = get_model(model_id)
    if existing is None:
        raise ValueError(f"Model '{model_id}' not found")
    if existing.get("system"):
        raise ValueError(f"Cannot modify system model '{model_id}'")

    merged = {**existing, **updates, "id": model_id}
    return save_user_model(merged)


# ── Setup instructions ────────────────────────────────────────────────────────

SETUP_INSTRUCTIONS = """
UniCell Model Library — Two Entry Points
=========================================

1. SYSTEM MODELS (built-in, read-only)
   Defined in unicell_model_library.py → SYSTEM_MODELS list.
   These are the 9 MathTrix demos plus any domain-specific models.
   To add a new system model: add an entry to SYSTEM_MODELS (no restart needed).

   Example entry:
   {
     "id":          "my_physics_model",
     "name":        "My Physics Model",
     "domain":      "PhysTrix",
     "description": "Custom physics simulation",
     "tags":        ["physics", "custom"],
     "parameters":  {"steps": {"type": "int", "default": 50, ...}},
     "tile_config": {"MIF_DIV": "low_latency"},
     "system":      True
   }

2. USER MODELS (dynamic, stored in models/ directory)
   Created via the API or by dropping JSON files in models/.
   Live-reload: changes are picked up immediately, no restart needed.

   Via API:
     POST /api/library
     Body: {"name": "My Model", "domain": "Custom", "parameters": {...}}

   Via file:
     Drop a JSON file in models/my_model.json
     See models/example_user_model.json for the format

   Via curl:
     curl -X POST http://localhost:5000/api/library \\
       -H 'Content-Type: application/json' \\
       -d '{"name":"My Model","domain":"Custom","parameters":{}}'

EXTENDING TO NEW DOMAINS
   Add a new domain (BioTrix, ChemTrix, AstroTrix) by:
   1. Adding system models with "domain": "BioTrix" to SYSTEM_MODELS
   2. Adding a runner in unicell_server.py (like run_laplacian_1d)
   3. That's it — the frontend shows the new domain automatically

   Or via user models: just set "domain": "BioTrix" in your JSON.
"""


# ── Example user model ────────────────────────────────────────────────────────

EXAMPLE_USER_MODEL = {
    "id":          "example_custom",
    "name":        "Example Custom Model",
    "domain":      "Custom",
    "description": "Example showing the user model format. Delete or replace this.",
    "author":      "user",
    "tags":        ["example", "custom"],
    "parameters": {
        "size":  {"type": "int",   "default": 32,  "min": 8,  "max": 128, "label": "Grid size"},
        "steps": {"type": "int",   "default": 50,  "min": 1,  "max": 500, "label": "Timesteps"},
        "speed": {"type": "float", "default": 1.0, "min": 0.1,"max": 10.0,"label": "Speed multiplier"},
    },
    "tile_config": {},
    "base_model":  "laplacian_2d",
    "_notes": [
        "base_model: if set, this model uses the same runner as the base",
        "tile_config: override strategy for specific tiles",
        "source: optional Python source for hardware backend compilation",
        "domain: any string — creates a new domain tab in the frontend",
    ]
}


def write_example():
    """Write example_user_model.json to models/ if it doesn't exist."""
    path = _USER_DIR / "example_user_model.json"
    if not path.exists():
        with open(path, "w") as f:
            json.dump(EXAMPLE_USER_MODEL, f, indent=2)
        print(f"  Created example user model: {path}")


# Auto-create example on import
write_example()
