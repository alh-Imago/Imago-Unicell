"""
run_companion.py — Imago System Runner

Boots the full Imago system:
  - UniCellArray (the NOR gate fabric)
  - ImagoController
  - ShoreV2 (system registry)
  - Companion (base OS — keys, tiles, regions, Ward escalation)
  - Optional: TinyLlama AI bridge on GPU

Usage:
  # Basic boot (no AI)
  python3 run_companion.py

  # With TinyLlama on GPU
  python3 run_companion.py --ai

  # With TinyLlama on CPU (slower but no GPU needed)
  python3 run_companion.py --ai --cpu

  # Run a simple demo program after boot
  python3 run_companion.py --demo

Requirements (base):
  pip install torch transformers accelerate

GPU note:
  TinyLlama-1.1B requires ~2.2GB VRAM in float16.
  A 4GB GPU (e.g. RTX 3050) has comfortable headroom.
  First run downloads ~2.2GB from HuggingFace automatically.
"""

import argparse
import sys
import time


# ── Model choice ──────────────────────────────────────────────────────────────

TINYLLAMA_MODEL  = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
DISTILGPT2_MODEL = "distilgpt2"   # tiny fallback (~300MB)


# ── Boot ──────────────────────────────────────────────────────────────────────

def boot_system(cell_count: int = 5000,
                load_image: str = None):
    """
    Boot the full Imago system and return all components.

    load_image: path to a .img or .img.gz file to restore from.
                If given, the system state is loaded instead of
                booted fresh. Shore/Companion/SearchIndex are all
                restored from the image.
    """
    from unicell_array import UniCellArray
    from controller import ImagoController
    from shore_v2 import ShoreV2
    from companion import Companion

    print("=" * 60)
    print("  Imago UniCell System")
    print("=" * 60)
    print()

    # Array and controller
    print(f"[BOOT] Initialising array ({cell_count} cells)...")
    arr  = UniCellArray(cell_count)
    ctrl = ImagoController(cell_count=cell_count)
    print(f"[BOOT] Array ready")

    # Shore — system registry
    print(f"[BOOT] Starting Shore registry...")
    shore = ShoreV2(
        shore_id       = "shore_0",
        base_address   = 0x00500000,
        initial_capacity = 64,
        controller     = ctrl,
        array          = arr,
    )
    print(f"[BOOT] Shore ready")

    # COMPANION — base OS
    print(f"[BOOT] Starting COMPANION...")
    companion = Companion.boot(arr, shore, ctrl)
    print(f"[BOOT] COMPANION ready")

    # Wire Shore → Companion escalation loop
    shore.attach_companion(companion.handle_ward_flag)
    print(f"[BOOT] Shore → Companion escalation wired")

    # Device bridges — keyboard, storage, network, console
    print(f"[BOOT] Starting device bridges...")
    from device_bridge import DeviceManager, KeyboardBridge
    from device_bridge import StorageBridge, NetworkBridge, ConsoleBridge
    devices = DeviceManager(controller=ctrl, shore=shore)
    devices.add(ConsoleBridge,  base_address=0x00C00000, name="console")
    devices.add(StorageBridge,  base_address=0x00D00000, name="storage")
    devices.add(NetworkBridge,  base_address=0x00E00000, name="network")
    # Keyboard needs a real TTY — skip silently if not available
    try:
        devices.add(KeyboardBridge, base_address=0x00B00000, name="keyboard")
    except Exception as e:
        print(f"[BOOT] Keyboard bridge unavailable: {e}")
    print(f"[BOOT] Device bridges ready")

    # Search index — empty at fresh boot, populated from image if restoring
    from fs_search import SearchIndex
    search_index = SearchIndex(shore=shore)
    print(f"[BOOT] Search index ready")

    # Restore from image if requested
    if load_image is not None:
        print(f"[BOOT] Restoring from image: {load_image}")
        from vm_image import VMImage
        ctrl2, shore2, companion2, search2 = VMImage.load(
            load_image, cell_count=cell_count)
        # Wire companion callback on restored shore
        shore2.attach_companion(companion2.handle_ward_flag)
        if search2 is not None:
            search_index = search2
            print(f"[BOOT] Search index restored: {search_index}")
        print(f"[BOOT] Restore complete")
        return arr, ctrl2, shore2, companion2, devices, search_index

    print()
    print("[BOOT] System online.")
    print()

    return arr, ctrl, shore, companion, devices, search_index


def save_system(path: str, ctrl, shore, companion,
                search_index=None) -> None:
    """Save the running system to a VM image file."""
    from vm_image import save_image
    save_image(path, ctrl, shore, companion, search_index=search_index)
    print(f"[BOOT] System saved to '{path}'")


def watch_cycle(shore, pond_manager=None) -> list:
    """
    Run one Ward watch cycle:
      1. Update Shore registry with current Ward states from live Ponds
      2. Call shore.watch_wards() to escalate any anomalies to COMPANION

    pond_manager: optional PondManager — if provided, syncs all Pond
    Ward states into the Shore registry before watching.

    Returns list of escalations raised.
    """
    if pond_manager is not None:
        for pond in pond_manager._ponds.values():
            if pond.ward is None:
                continue
            entry = shore.lookup(pond.name)
            if entry:
                shore.update(pond.name, ward_state=pond.ward.state)

    return shore.watch_wards()


# ── AI attachment ─────────────────────────────────────────────────────────────

def attach_ai(companion, device: str = "cuda",
              model: str = TINYLLAMA_MODEL):
    """
    Attach TinyLlama (or DistilGPT2) to the COMPANION AI bridge.
    """
    print(f"[AI] Loading {model} on {device}...")
    print(f"[AI] This will download ~2.2GB on first run.")
    print()

    ok = companion.attach_ai(model, device=device)
    if ok:
        print(f"[AI] Model attached successfully.")
    else:
        print(f"[AI] Model failed to load — COMPANION running on rule engine.")
    print()
    return ok


# ── Demo ──────────────────────────────────────────────────────────────────────

def run_demo(arr, ctrl, shore, companion):
    """
    Run a simple demonstration of the system.
    Shows: tile provision, region allocation, Ward escalation.
    """
    from companion import KEY_ADMIN, KEY_TILE, ACTION_RESTART, ACTION_EXPAND

    print("=" * 60)
    print("  Demo")
    print("=" * 60)
    print()

    # Get the admin key
    admin_key = next(
        k for k in companion._keys.values()
        if k.key_type == KEY_ADMIN and k.holder_id == "companion"
    )
    print(f"Admin key: {admin_key.key_id[:8]}...")

    # Issue a tile key and request a tile
    print()
    print("--- Tile provision ---")
    tile_key = companion.issue_tile_key("demo_pond", "INT32_ADD",
                                         admin_key.key_id)
    print(f"Tile key issued to demo_pond: {tile_key.key_id[:8]}...")

    tile = companion.request_tile("INT32_ADD", "demo_pond", tile_key.key_id)
    if tile:
        print(f"Tile received: {tile.metadata.operation} "
              f"({tile.metadata.cell_count} cells, "
              f"depth {tile.metadata.pipeline_depth})")

    # Available tiles
    print()
    print(f"Available tiles: {companion.available_tiles()}")

    # Allocate a region
    print()
    print("--- Region allocation ---")
    region = companion.allocate_region(size=512, owner_id="demo_pond")
    if region:
        print(f"Region: 0x{region.base:08X} — 0x{region.end:08X} "
              f"({region.size} slots)")
        companion.free_region(region.base, "demo_pond")
        print(f"Region freed.")

    # Simulate Ward escalation
    print()
    print("--- Ward escalation (rule engine) ---")
    scenarios = [
        ("demo_pond_1", "STALLED",   {}),
        ("demo_pond_2", "OFFLINE",   {}),
        ("demo_pond_3", "DEGRADED",  {"is_throttled": True}),
        ("demo_pond_4", "SILENT",    {}),
    ]
    for pond_id, state, ctx in scenarios:
        action = companion.handle_ward_flag(pond_id, state, ctx)
        print(f"  {pond_id} [{state}] → {action.action}: {action.reason}")

    # Shore status
    print()
    print("--- Shore registry ---")
    st = shore.status()
    print(f"Registered entries: {st['total_entries']}")
    print(shore.dump())

    # COMPANION status
    print()
    print("--- COMPANION status ---")
    cs = companion.status()
    for k, v in cs.items():
        print(f"  {k}: {v}")

    # Ward watch cycle demo — registers Ponds with anomalous states,
    # then shows Shore → Companion escalation happening automatically
    print()
    print("--- Shore → Companion watch loop ---")
    from shore_v2 import ShoreEntry

    # Register a couple of synthetic Ponds with Ward anomalies
    shore.register(ShoreEntry("proc_pond_1", "POND", 0x00700000, 0x00700000,
                               pond_id=101, ward_state="STALLED"))
    shore.register(ShoreEntry("proc_pond_2", "POND", 0x00800000, 0x00800000,
                               pond_id=102, ward_state="OFFLINE"))
    shore.register(ShoreEntry("proc_pond_3", "POND", 0x00900000, 0x00900000,
                               pond_id=103, ward_state="HEALTHY"))

    escalations = watch_cycle(shore)
    print(f"  Watch cycle raised {len(escalations)} escalation(s):")
    for e in escalations:
        print(f"    {e['name']} [{e['ward_state']}]")

    # A second cycle should NOT re-escalate (flag is set)
    escalations2 = watch_cycle(shore)
    print(f"  Second cycle (same states): {len(escalations2)} escalations "
          f"(de-duplicated ✓)")

    # Clear one and show it re-escalates
    shore.clear_escalation("proc_pond_1")
    escalations3 = watch_cycle(shore)
    print(f"  After clearing proc_pond_1: {len(escalations3)} escalation(s)")

    print()
    print("Demo complete.")


# ── Interactive Ward simulation ───────────────────────────────────────────────

def interactive_ward(companion):
    """
    Simple interactive loop — simulate Ward flags and see COMPANION respond.
    """
    print()
    print("=" * 60)
    print("  Interactive Ward Simulator")
    print("  Type: <pond_id> <ward_state>  e.g.  pond_7 STALLED")
    print("  Ward states: STALLED OFFLINE DEGRADED SILENT HEALTHY")
    print("  Type 'quit' to exit")
    print("=" * 60)
    print()

    while True:
        try:
            line = input("Ward flag> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not line or line.lower() == "quit":
            break

        parts = line.split()
        if len(parts) < 2:
            print("Usage: <pond_id> <ward_state>")
            continue

        pond_id, ward_state = parts[0], parts[1].upper()
        context = {}
        if len(parts) > 2:
            # Extra context as key=value pairs
            for part in parts[2:]:
                if "=" in part:
                    k, v = part.split("=", 1)
                    try:
                        context[k] = int(v)
                    except ValueError:
                        context[k] = v

        action = companion.handle_ward_flag(pond_id, ward_state, context)
        print(f"  → {action.action}: {action.reason} [{action.source}]")
        print()


# ── Ollama alternative ────────────────────────────────────────────────────────

def attach_ollama(companion, model: str = "tinyllama"):
    """
    Alternative AI attachment using Ollama HTTP API instead of
    loading the model directly via HuggingFace.

    Requires Ollama running locally:
      brew install ollama  (macOS)
      ollama serve
      ollama pull tinyllama

    This replaces the CompanionAI class with an Ollama-backed version.
    """
    import urllib.request
    import json as json_lib

    # Test Ollama is running
    try:
        req = urllib.request.urlopen(
            "http://localhost:11434/api/tags", timeout=3)
        tags = json_lib.loads(req.read())
        available = [m["name"] for m in tags.get("models", [])]
        print(f"[OLLAMA] Connected. Available models: {available}")
    except Exception as e:
        print(f"[OLLAMA] Cannot connect to Ollama: {e}")
        print(f"[OLLAMA] Make sure Ollama is running: ollama serve")
        return False

    # Check requested model is available
    if model not in available and f"{model}:latest" not in available:
        print(f"[OLLAMA] Model '{model}' not found.")
        print(f"[OLLAMA] Pull it first: ollama pull {model}")
        return False

    # Attach an Ollama-backed AI bridge
    companion._ai = OllamaAI(model=model)
    print(f"[OLLAMA] AI bridge ready: {model}")
    return True


class OllamaAI:
    """
    Ollama-backed AI bridge for COMPANION.
    Drop-in replacement for CompanionAI.
    Calls Ollama's local HTTP API instead of loading model directly.
    """

    SYSTEM_PROMPT = (
        "You are the COMPANION base OS for an Imago UniCell array. "
        "Respond with ONLY a JSON object: "
        '{"action": "RESTART|MIGRATE|EXPAND|REVOKE|ISOLATE|NOOP|ESCALATE", '
        '"target": "pond_id", "reason": "brief reason"}'
    )

    def __init__(self, model: str = "tinyllama"):
        self._model = model

    def decide(self, status_text: str) -> dict:
        import urllib.request
        import json as json_lib

        payload = json_lib.dumps({
            "model":  self._model,
            "prompt": (f"System: {self.SYSTEM_PROMPT}\n\n"
                       f"Status:\n{status_text}\n\n"
                       f"Action JSON:"),
            "stream": False,
        }).encode()

        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=30)
            data = json_lib.loads(resp.read())
            response = data.get("response", "")
            return self._parse(response)
        except Exception as e:
            return {"action": "NOOP", "target": "unknown",
                    "reason": f"Ollama error: {e}"}

    def _parse(self, response: str) -> dict:
        import json as json_lib
        try:
            start = response.find("{")
            end   = response.rfind("}") + 1
            if start >= 0 and end > start:
                data = json_lib.loads(response[start:end])
                if "action" in data:
                    return data
        except Exception:
            pass
        return {"action": "NOOP", "target": "unknown",
                "reason": f"Unparseable: {response[:60]}"}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Imago UniCell System with COMPANION base OS"
    )
    parser.add_argument("--ai",     action="store_true",
                        help="Attach TinyLlama AI bridge (HuggingFace)")
    parser.add_argument("--ollama", action="store_true",
                        help="Attach AI via Ollama instead of HuggingFace")
    parser.add_argument("--cpu",    action="store_true",
                        help="Use CPU instead of GPU (slower)")
    parser.add_argument("--model",  default=TINYLLAMA_MODEL,
                        help=f"Model to use (default: {TINYLLAMA_MODEL})")
    parser.add_argument("--demo",   action="store_true",
                        help="Run demo after boot")
    parser.add_argument("--interactive", action="store_true",
                        help="Interactive Ward simulation")
    parser.add_argument("--cells",  type=int, default=5000,
                        help="Array cell count (default: 5000)")
    parser.add_argument("--save",   default=None,
                        help="Save system image to this path on exit "
                             "(e.g. system.img or system.img.gz)")
    parser.add_argument("--load",   default=None,
                        help="Restore system from a saved image file")
    args = parser.parse_args()

    # Boot (or restore from image)
    arr, ctrl, shore, companion, devices, search_index = boot_system(
        cell_count=args.cells,
        load_image=args.load,
    )

    # AI attachment
    if args.ollama:
        model_name = args.model if args.model != TINYLLAMA_MODEL else "tinyllama"
        attach_ollama(companion, model=model_name)
    elif args.ai:
        device = "cpu" if args.cpu else "cuda"
        attach_ai(companion, device=device, model=args.model)

    # Demo
    if args.demo:
        run_demo(arr, ctrl, shore, companion)

    # Interactive
    if args.interactive:
        interactive_ward(companion)

    # Save on exit if requested
    if args.save:
        save_system(args.save, ctrl, shore, companion,
                    search_index=search_index)

    # If nothing specified just print status and exit
    if not args.demo and not args.interactive:
        print(f"System status:")
        cs = companion.status()
        for k, v in cs.items():
            print(f"  {k}: {v}")
        print()
        print(f"Devices:      {list(devices._bridges.keys())}")
        print(f"Search ponds: {list(search_index._ponds.keys())}")
        if args.load:
            print(f"Loaded from:  {args.load}")
        print()
        print("Run with --demo or --interactive to do more.")
        print("Run with --save PATH to snapshot the system on exit.")
        print("Run with --load PATH to restore from a snapshot.")
        print("Run with --ai to attach TinyLlama (requires transformers + torch).")
        print("Run with --ollama to use Ollama instead.")


if __name__ == "__main__":
    main()
