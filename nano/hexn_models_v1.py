"""hexn_models_v1.py - the four Hex-N models as things a user can PICK and BUILD from the front panel (12 Nov 2026; Alan 08:56: 'edit the front end system to incorporate the models, so a user can just pick and build
as they want from the 4 models'). Used by nano/hexn_tab_v3.py (the page) and nano/frontend_v4.py (the server). No HTTP here, so it can be tested without a socket.

What 'build' means here, stated plainly:
  - a CARD build (a bitstream for the Kintex card) is never started by the page: it needs the openXC7 shell and takes minutes to an hour. The page writes the BUILD SHEET: the exact commands, in order, with the
    result on record for that choice and where it was measured. Nothing is sent to a card.
  - a PYTHON model or a small match can be run from the page (button 'Run it now'): the same tool the command line uses, started with the options chosen, its printout shown as it is.
Every item names its state (on the card / simulated / Python model) and its base document (docs/hex-n/MODEL_*_v1.md). Figures quoted are copied from those documents, not measured by this module."""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOLS = os.path.join(ROOT, "tools")

ARRAYS = ("hex7_off2_mix", "hex6", "hex5")
SHAPES = {"2:8:16:2": "2 buses x 8 cells per layer (48 cells), 16 input lines", "4:16:48:3": "4 buses x 16 cells per layer (192 cells), 48 input lines", "8:8:48:3": "8 buses x 8 cells per layer (192 cells), 48 input lines"}
NETV = ("v5", "v4", "v3", "v2")
SHAPE_RECORD = {("2:8:16:2", "v2"): "7,313 LUT sites, 2,071 flip-flops, 84.3 MHz estimate (section 47)",
                ("4:16:48:3", "v2"): "34,777 LUT sites, 9,081 flip-flops, 58.1 MHz estimate; loaded on the card, runs (sections 47b, 71)",
                ("8:8:48:3", "v2"): "70,994 LUT sites, 49.4 MHz estimate: FAILS 50 MHz, no bitstream (section 47b)",
                ("8:8:48:3", "v4"): "44,334 LUT sites, 39.16 MHz estimate: FAILS 50 MHz (section 68)",
                ("8:8:48:3", "v5"): "43,741 LUT sites, 15,595 flip-flops, 65.6 MHz estimate; loaded on the card, runs (section 72)"}

MODELS = [
    dict(n=1, name="The layered model", doc="docs/hex-n/MODEL_1_LAYERED_v1.md",
         what="Nested layers: detectors, history and prediction, a strategist that looks ahead, a helper and the batch judge. Played Connect Four and draughts.",
         state="Layers 1 and 2, the batch judge and the memory tier ran on boards; layers 3 and 4 and the helper are Python models."),
    dict(n=2, name="The detector system and the speech chain", doc="docs/hex-n/MODEL_2_DETECTOR_v1.md",
         what="Detectors with three-valued weights taught by counting, widened into a chain that recognises spoken digits.",
         state="On the Kintex card on real data: 936 of 1,079 test recordings right (86.7%)."),
    dict(n=3, name="The neural bus network", doc="docs/hex-n/MODEL_3_NEURAL_BUS_v1.md",
         what="Neuron-like cells on small shared buses; the answer is a map of which cells fired.",
         state="Works on made-up test patterns; built as logic and loaded on the card; at chance on real speech."),
    dict(n=4, name="The upper logic", doc="docs/hex-n/MODEL_4_UPPER_LOGIC_v1.md",
         what="Stored maps beside the cells, four banks around a shared memory (the tile), a monitor, an input check, an anomaly store, identification by parts.",
         state="Python models on test patterns only; not in hardware."),
]

# key -> item. kind: 'card' (build sheet only), 'run' (a tool the page may start), 'sim' (a simulation test: commands only, it needs iverilog and minutes)
ITEMS = [
    dict(key="m1_c4", model=1, kind="run", label="Connect Four match: plain search against the Hex-N search", opts=("games", "seeds"), tag="Python model",
         record="Recorded: the plain search was better at first; against opponents with habits the learned model predicts about 60% of replies and still lowers the score (Model 1 section 4).", time="under a second per game"),
    dict(key="m1_dr", model=1, kind="run", label="Draughts match: plain search against the Hex-N search", opts=("games", "seeds"), tag="Python model",
         record="Recorded: equal to the plain search at depth 3 and 4 with the hit-rate blend (Model 1 section 4).", time="well under a second per game at depth 2"),
    dict(key="m1_base", model=1, kind="card", label="Card build: the base (pattern arrays, batch judge, stores) without the speech chain", opts=("arrays", "out"), tag="on the card (base v1 to v3); v4 simulated",
         record="Recorded: base v3 19,100 LUT sites, clock estimate 79 to 93 MHz (HEXN_KINTEX_BASE_PICTURE_v1.md)."),
    dict(key="m2_card", model=2, kind="card", label="Card build: the base WITH the speech chain and its on-chip event memory, and a run of the test set", opts=("arrays", "out", "speech_test"), tag="on the card",
         record="Recorded: 23,346 LUT sites, clock estimate 90.68 MHz; 936 of 1,079 right, 286 clocks per recording counted on the chip (Model 2 section 4)."),
    dict(key="m2_kit", model=2, kind="card", label="Card build: the stand-alone speech kit (300 recordings baked in, exact count over JTAG)", opts=("out",), tag="on the card",
         record="Recorded: 262 of 300; 2,888 LUT sites; clock estimate 200 MHz (direction doc sections 73, 75)."),
    dict(key="m2_sim", model=2, kind="sim", label="Simulation: the chain and the base controller checked against the Python model", opts=(), tag="simulated",
         record="Recorded: all pass; the kit's 300 recordings give 262; about 9 minutes in all."),
    dict(key="m2_err", model=2, kind="run", label="Where the chain's errors go (needs the speech data files)", opts=("data",), tag="Python model",
         record="Recorded: 'one' answered as 'nine' 36 of its 40 errors; training set 78.0% (direction doc section 93).", time="about 20 seconds"),
    dict(key="m3_card", model=3, kind="card", label="Card build: the bus network as a stand-alone design", opts=("shape", "netv", "out"), tag="loaded on the card (runs; function not checked on the card)",
         record=None),
    dict(key="m3_sim", model=3, kind="sim", label="Simulation: the network logic checked clock for clock against the Python model", opts=(), tag="simulated", record="Recorded: passes (versions v3, v4, v5)."),
    dict(key="m3_layers", model=3, kind="run", label="Python model: recall from the layer 2 map, the layer 3 map and both", opts=(), tag="Python model",
         record="Recorded: layer 2 map 97 / 92 / 76 / 46, layer 3 map 78 / 65 / 50 / 25 at 10 / 30 / 50 / 70% of events dropped (direction doc section 49).", time="not recorded (5 seeds, fixed)"),
    dict(key="m3_compete", model=3, kind="run", label="Python model: competition between cells (first to fire)", opts=("seeds",), tag="Python model",
         record="Recorded: never better; tested and found wanting (direction doc section 96).", time="about 7 minutes for 5 seeds"),
    dict(key="m4_maps", model=4, kind="run", label="Stored maps beside the cells: recall, replay, hint and rank", opts=("seeds",), tag="Python model",
         record="Recorded: cells alone 70 / 61 / 45 / 22, recall and replay 87 / 82 / 69 / 40 (direction doc section 77).", time="about 2.5 minutes for 5 seeds"),
    dict(key="m4_tile", model=4, kind="run", label="The tile: four banks, the shared memory and the monitor", opts=("seeds",), tag="Python model",
         record="Recorded: a nearly blind bank goes from 14.6% to 86.9% right with the help of the other three (direction doc section 80).", time="about 8.5 minutes for 5 seeds"),
    dict(key="m4_damage", model=4, kind="run", label="The tile with 1, 2, 3 or 4 banks damaged", opts=("seeds",), tag="Python model",
         record="Recorded: damaged banks right after the monitor 85.9 / 67.0 / 32.8% with 1 / 2 / 3 damaged (direction doc section 86).", time="about 9 minutes for 5 seeds"),
    dict(key="m4_conf", model=4, kind="run", label="The tile with confidence-weighted votes and the input check", opts=("seeds",), tag="Python model",
         record="Recorded: two blind banks of four: 67.3% plain, 86.5% with the input check (direction doc section 87).", time="about 8.5 minutes for 5 seeds"),
    dict(key="m4_anom", model=4, kind="run", label="The anomaly store: a hidden weak pattern in the noise", opts=("seeds",), tag="Python model",
         record="Recorded: found in 30 of 30 streams (6 lines x 2 events, report at 8 hits) (direction doc section 89).", time="under 3 minutes for 5 seeds"),
    dict(key="m4_compare", model=4, kind="run", label="The anomaly store with the compare step, the weak table and promotion", opts=("seeds",), tag="Python model",
         record="Recorded: new pattern found in 9 of 10 streams; a faint copy of a known pattern never called new (direction doc section 91).", time="about 4 minutes for 5 seeds"),
    dict(key="m4_parts", model=4, kind="run", label="Identifying a thing from its parts", opts=("seeds",), tag="Python model",
         record="Recorded: named right 99.9%; one aspect missing 98.6%; a changed part called new 99.6% (direction doc section 97).", time="about 4 minutes for 5 seeds"),
    dict(key="m4_speech", model=4, kind="run", label="The memory of wholes on top of the speech chain (needs the speech data files)", opts=("data",), tag="Python model, real data",
         record="Recorded: 855 to 880 right against the chain's 936: it does not beat the chain (direction doc section 99).", time="about 16 seconds"),
]
BYKEY = {i["key"]: i for i in ITEMS}
TOOL = {"m1_c4": "hexn_connect4_blend_v2.py", "m1_dr": "hexn_draughts_match_v3.py", "m2_err": "hexn_chain_confusion_v1.py", "m3_layers": "hexn_busnet_layermatch_v1.py", "m3_compete": "hexn_busnet_compete_v1.py",
        "m4_maps": "hexn_recall_blocks_v1.py", "m4_tile": "hexn_recall_pool_v1.py", "m4_damage": "hexn_recall_pool_v2.py", "m4_conf": "hexn_recall_pool_v3.py", "m4_anom": "hexn_anomaly_tile_v1.py",
        "m4_compare": "hexn_anomaly_tile_v3.py", "m4_parts": "hexn_parts_v2.py", "m4_speech": "hexn_chain_parts_v1.py"}
SPEECH_TESTS = {"full": ("hexn_chain_host_v3.py full ~/hexn-wt/fpga/ypcb/hexn_speech/data_full", "right 936 (86.7%) and 'expected 936 (Python reference): PASS; per digit: all equal'"),
                "kitram": ("hexn_chain_host_v2.py kitram ~/hexn-wt/fpga/ypcb/hexn_speech/data --repeat 3", "three lines with '86079 clocks counted on the chip' and 'right 262 of 300', then PASS"),
                "kit": ("hexn_chain_host_v1.py kit ~/hexn-wt/fpga/ypcb/hexn_speech/data", "right 262 (87.3%) and 'expected 262 (Python reference): PASS'")}
_PATH_OK = re.compile(r"^[A-Za-z0-9_./~-]{1,200}$")


def _int(f, name, lo, hi, default):
    try:
        v = int(str(f.get(name, default)).strip() or default)
    except ValueError:
        raise ValueError("%s must be a whole number" % name)
    if not lo <= v <= hi:
        raise ValueError("%s must be between %d and %d" % (name, lo, hi))
    return v


def _path(f, name, default):
    v = str(f.get(name) or default).strip()
    if not _PATH_OK.match(v):
        raise ValueError("%s: use letters, digits and . _ - / ~ only" % name)
    return v


def _arrays(f):
    got = [a for a in ARRAYS if f.get("arr_" + a)]
    return got or ["hex7_off2_mix", "hex6"]


class ModelsController:
    def options(self, f):
        """the options a request carries, checked; raises ValueError with a plain message"""
        o = dict(seeds=_int(f, "seeds", 1, 5, 1), games=_int(f, "games", 2, 200, 20), out=_path(f, "out", "/media/alan/InternalHDD/hexn_builds"), data=_path(f, "data", "~/shd"), arrays=_arrays(f),
                 shape=f.get("shape") or "8:8:48:3", netv=f.get("netv") or "v5", speech_test=f.get("speech_test") or "full")
        if o["shape"] not in SHAPES: raise ValueError("unknown shape")
        if o["netv"] not in NETV: raise ValueError("unknown network version")
        if o["speech_test"] not in SPEECH_TESTS: raise ValueError("unknown speech test")
        return o

    def argv(self, key, o):
        """the command of a runnable item as an argument list (no shell)"""
        t = os.path.join("tools", TOOL[key])
        if key == "m1_c4": return ["python3", t, "habit2", "plain3", "hex3", "--games", str(o["games"]), "--seeds", str(o["seeds"])]
        if key == "m1_dr": return ["python3", t, "noisy2", "plain2", "hex2", "--games", str(o["games"]), "--seeds", str(o["seeds"])]
        if key in ("m2_err", "m4_speech"): return ["python3", t, o["data"]]
        if key == "m3_layers": return ["python3", t, "4", "16"]
        return ["python3", t, str(o["seeds"])]

    def sheet_item(self, key, o):
        it = BYKEY[key]; cmds = []; notes = []; expect = it.get("record")
        pull = "git -C ~/hexn-wt pull origin Hex-N"; nixs = "# open the openXC7 shell, then give the lines after it one at a time:\nnix develop github:openxc7/toolchain-nix"
        ocd = "cd ~/ypcb-00338-1p1 && nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 ~/hexn-wt/tools/"
        load = "# ordinary terminal, card on; this loads into working memory only, nothing is written to flash:\n~/openFPGALoader/build/openFPGALoader -c digilent_hs2 %s"
        if it["kind"] == "run":
            cmds = [" ".join(self.argv(key, o))]
            notes.append("Run from the repository folder. Time on record: %s." % it["time"])
            if "data" in it["opts"]: notes.append("The folder must hold shd_train.h5 and shd_test.h5 (the Heidelberg spoken digits).")
        elif key in ("m1_base", "m2_card"):
            ver = "6" if key == "m2_card" else "4"; folder = "%s/arr_base_b%s_noram" % (o["out"], ver)
            cmds = [pull, nixs, "cd ~/ypcb-00338-1p1", "OUT=%s HEXN_BASE=%s HEXN_BASE_VER=%s HEXN_NORAM=1 bash ~/hexn-wt/fpga/ypcb/hexn_arr/run_arr.sh" % (o["out"], ",".join(o["arrays"]), ver), load % (folder + "/hexn_arr.bit")]
            if key == "m2_card":
                tool, exp = SPEECH_TESTS[o["speech_test"]]; cmds.append(ocd + tool); expect = "A good run ends with: %s. %s" % (exp, it["record"])
                notes.append("Built and run on the card with the arrays hex7_off2_mix and hex6 (11 Nov 2026). Other array choices build the same way but were not run with the chain.")
            else:
                cmds.append(ocd + "hexn_kxbase_host_v1.py info")
                notes.append("Controller v4 (the weight store) passed in simulation; on the card the base ran as v1 to v3 and, with the chain added, as v5 and v6. A v4 build has not been run on the card.")
            notes.append("If the load printout does not end with 'done 1', run the load line again.")
        elif key == "m2_kit":
            cmds = [pull, nixs, "cd ~/ypcb-00338-1p1 && ln -sfn ~/hexn-wt/fpga/ypcb/hexn_speech2 designs/hexn_speech2", "HEXN_OUT=%s bash ~/hexn-wt/fpga/ypcb/hexn_speech2/run_speech2.sh" % o["out"],
                    load % (o["out"] + "/speech2/hexn_speech2.bit"), "cd ~/ypcb-00338-1p1 && nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_REPO=$HOME/hexn-wt python3 ~/hexn-wt/fpga/ypcb/hexn_speech2/check.py"]
            expect = "A good run prints: correct 262, total 300, PASS. " + it["record"]
        elif key == "m3_card":
            g, per, nin, sql = o["shape"].split(":"); name = "bnet_%sx%s_n%s_q%s" % (g, per, nin, sql)
            cmds = [pull, nixs, "cd ~/ypcb-00338-1p1 && ln -sfn ~/hexn-wt/fpga/ypcb/hexn_bnet designs/hexn_bnet", "HEXN_OUT=%s HEXN_NETV=%s bash ~/hexn-wt/fpga/ypcb/hexn_bnet/run_bnet.sh %s" % (o["out"], o["netv"], o["shape"]),
                    load % ("%s/%s/hexn_bnet.bit" % (o["out"], name))]
            rec = SHAPE_RECORD.get((o["shape"], o["netv"]))
            expect = ("Recorded for this shape and version: " + rec) if rec else "No build of this shape with this version is on record: size and clock are unknown until it is built."
            notes.append("%s; network version %s. The test design drives the network from a random source and shows a heartbeat light: a card run shows that it loads and runs, not that it computes correctly." % (SHAPES[o["shape"]], o["netv"]))
            notes.append("The network is not joined to the base controller and there is no PC program that loads weights into it on the card.")
        elif key == "m2_sim":
            cmds = ["python3 -m pytest tests/vm/test_hexn_speech_chain_v1.py tests/vm/test_hexn_base_v5_chain_v1.py tests/vm/test_hexn_base_v6_evram_v1.py tests/vm/test_hexn_chain_host_v3.py -q"]
            notes.append("Needs iverilog; without it these tests fail and do not skip.")
        elif key == "m3_sim":
            cmds = ["python3 -m pytest tests/vm/test_hexn_bnet_net_v5.py tests/vm/test_hexn_bnet_map_v1.py -q"]; notes.append("Needs iverilog.")
        return dict(key=key, label=it["label"], model=it["model"], kind=it["kind"], tag=it["tag"], commands=cmds, expect=expect, notes=notes, runnable=it["kind"] == "run")

    def sheet(self, f):
        """the build sheet for the ticked items -> dict(ok, items | error)"""
        try:
            o = self.options(f)
        except ValueError as e:
            return dict(ok=False, error=str(e))
        keys = [i["key"] for i in ITEMS if f.get("pick_" + i["key"])]
        if not keys:
            return dict(ok=False, error="nothing was ticked: tick at least one item")
        return dict(ok=True, items=[self.sheet_item(k, o) for k in keys], options=o)

    def run(self, f, timeout=900):
        """start one runnable item with the options given and return its printout -> dict(ok, key, label, command, output, code | error)"""
        key = f.get("key", "")
        if key not in BYKEY or BYKEY[key]["kind"] != "run":
            return dict(ok=False, error="this item cannot be run from the page")
        try:
            o = self.options(f)
        except ValueError as e:
            return dict(ok=False, error=str(e))
        argv = self.argv(key, o); argv = [sys.executable] + [os.path.expanduser(a) for a in argv[1:]]
        if "data" in BYKEY[key]["opts"]:
            d = os.path.expanduser(o["data"])
            if not (os.path.isfile(os.path.join(d, "shd_train.h5")) and os.path.isfile(os.path.join(d, "shd_test.h5"))):
                return dict(ok=False, error="the folder %s does not hold shd_train.h5 and shd_test.h5" % o["data"])
        try:
            p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return dict(ok=False, error="stopped after %d seconds without finishing; run it from the command line: %s" % (timeout, " ".join(self.argv(key, o))))
        return dict(ok=True, key=key, label=BYKEY[key]["label"], command=" ".join(self.argv(key, o)), output=(p.stdout + ("\n" + p.stderr if p.returncode else ""))[-20000:], code=p.returncode)
