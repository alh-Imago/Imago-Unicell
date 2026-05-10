"""
imago CLI — command-line interface for the Imago UniCell VM.

Entry points (defined in pyproject.toml):
    imago-workbench          → launch browser UI at http://localhost:7420
    imago                    → general CLI: run, compile, examples, info

Usage:
    imago run not_gate.icm a=1
    imago run adder_int32.icm a=5 b=3
    imago compile "def add(a, b): return a and b" add
    imago examples
    imago info
    imago-workbench
    imago-workbench --port 8080 --cells 1024
"""

import sys
import os
import argparse
import json


def cmd_run(args):
    """Run a .icm file with optional named inputs."""
    from imago import VM

    # Parse inputs: a=5 b=3 → {a:5, b:3}
    inputs = {}
    for token in args.inputs:
        if "=" in token:
            k, v = token.split("=", 1)
            try:
                inputs[k] = int(v)
            except ValueError:
                inputs[k] = v
        else:
            print(f"Warning: '{token}' ignored (expected name=value)", file=sys.stderr)

    vm = VM(cell_count=args.cells)

    # Load from example name or file path
    if os.path.exists(args.program):
        r = vm.load(args.program)
    else:
        # Try as example name
        try:
            r = vm.load_example(args.program)
        except FileNotFoundError:
            print(f"Error: '{args.program}' not found as file or example name.", file=sys.stderr)
            print(f"Available examples: {', '.join(__import__('imago').examples())}", file=sys.stderr)
            sys.exit(1)

    if not r.get("ok"):
        print(f"Error: {r.get('error', 'Load failed')}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded '{r['name']}' — {r['cells']} cells")
    print(f"Inputs:  {r['inputs']}")
    print(f"Outputs: {r['outputs']}")

    if not inputs and r["inputs"]:
        # Interactive mode — prompt for each input
        print()
        for name in r["inputs"]:
            try:
                val = input(f"  {name} = ")
                inputs[name] = int(val.strip())
            except (EOFError, ValueError):
                inputs[name] = 0

    print()
    outputs = vm.run(**inputs)
    print("Result:")
    for k, v in outputs.items():
        print(f"  {k} = {v}")


def cmd_compile(args):
    """Compile Python source and show the result."""
    from imago import compile_function

    source  = args.source
    fn_name = args.function
    int32   = args.int32

    if os.path.exists(source):
        with open(source) as f:
            source = f.read()

    print(f"Compiling '{fn_name}'{'  [INT32]' if int32 else ''}...")
    try:
        vm = compile_function(source, fn_name, int32=int32, cell_count=args.cells)
        st = vm.status()
        print(f"OK — {st['cells']} cells")
        print(f"Inputs:  {st['inputs']}")
        print(f"Outputs: {st['outputs']}")

        if args.save:
            path = args.save
            # Export as icm
            import time
            ws = vm.workspace
            icm = {
                "program_id": fn_name + "_" + hex(int(time.time()))[-6:],
                "name": fn_name,
                "os_name": "Claudette", "os_version": "1.3",
                "created_at": time.time(),
                "inputs":  {k: v for k, v in zip(st["inputs"], [])},
                "outputs": {},
                "records": [
                    {"gs": getattr(r, "gate_state", 0),
                     "in": getattr(r, "input_address", 0),
                     "out": getattr(r, "output_address", 0),
                     "inB": getattr(r, "input_b_address", None),
                     "alt": None, "stor": False,
                     "init": getattr(r, "initial_value", None)}
                    for r in ws._records
                ],
                "models": [], "ranges": [], "security_context": None,
            }
            with open(path, "w") as f:
                json.dump(icm, f, indent=2)
            print(f"Saved to {path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_examples(args):
    """List bundled example programs."""
    from imago import examples, example_path
    print("Bundled examples:")
    for name in examples():
        path = example_path(name)
        with open(path) as f:
            icm = json.load(f)
        desc = icm.get("description", "")
        cells = len(icm.get("records", []))
        inputs  = list(icm.get("inputs", {}).keys())
        outputs = list(icm.get("outputs", {}).keys())
        print(f"  {name:<20} {cells:>5} cells  in={inputs} out={outputs}")
        if desc and not args.short:
            print(f"  {'':20} {desc[:60]}")


def cmd_info(args):
    """Show VM version and system info."""
    import imago
    print(f"imago-vm  v{imago.__version__}")
    print(f"Python    {sys.version.split()[0]}")

    # Check optional dependencies
    try:
        import llvmlite
        print(f"llvmlite  {llvmlite.__version__}  (LLVM frontend available)")
    except ImportError:
        print("llvmlite  not installed  (pip install llvmlite for C/C++/Rust support)")

    try:
        import serial
        print(f"pyserial  {serial.__version__}  (FPGA bridge available)")
    except ImportError:
        print("pyserial  not installed  (pip install pyserial for FPGA hardware)")


def cmd_workbench(args):
    """Launch the workbench browser UI."""
    import sys, os
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from workbench import Workbench
    from controller import ImagoController
    ctrl = ImagoController(cell_count=args.cells)
    wb   = Workbench(port=args.port, ctrl=ctrl)
    wb.serve(open_browser=not args.no_browser)


def main():
    """Main CLI entry point — `imago` command."""
    parser = argparse.ArgumentParser(
        prog="imago",
        description="Imago UniCell VM — run, compile, and explore UniCell programs",
    )
    parser.add_argument("--cells", type=int, default=4096,
                        help="Array cell count (default: 4096)")
    sub = parser.add_subparsers(dest="cmd", metavar="COMMAND")

    # imago run
    p_run = sub.add_parser("run", help="Run a .icm program")
    p_run.add_argument("program", help=".icm file path or example name")
    p_run.add_argument("inputs", nargs="*", metavar="name=value",
                       help="Named input values (e.g. a=5 b=3)")
    p_run.set_defaults(func=cmd_run)

    # imago compile
    p_compile = sub.add_parser("compile", help="Compile Python source to cells")
    p_compile.add_argument("source", help="Python source string or .py file path")
    p_compile.add_argument("function", help="Function name to compile")
    p_compile.add_argument("--int32", action="store_true", help="Use INT32 compiler")
    p_compile.add_argument("--save", metavar="FILE", help="Save result as .icm file")
    p_compile.set_defaults(func=cmd_compile)

    # imago examples
    p_ex = sub.add_parser("examples", help="List bundled example programs")
    p_ex.add_argument("--short", action="store_true", help="Short listing")
    p_ex.set_defaults(func=cmd_examples)

    # imago info
    p_info = sub.add_parser("info", help="Show version and dependency info")
    p_info.set_defaults(func=cmd_info)

    # imago workbench
    p_wb = sub.add_parser("workbench", help="Launch workbench browser UI")
    p_wb.add_argument("--port", type=int, default=7420)
    p_wb.add_argument("--no-browser", action="store_true")
    p_wb.set_defaults(func=cmd_workbench)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(0)

    args.func(args)


def workbench_main():
    """Entry point for `imago-workbench` command."""
    parser = argparse.ArgumentParser(
        prog="imago-workbench",
        description="Launch the Imago UniCell workbench browser UI",
    )
    parser.add_argument("--port", type=int, default=7420, help="HTTP port (default: 7420)")
    parser.add_argument("--cells", type=int, default=4096, help="Array cell count")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    import sys, os
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from workbench import Workbench
    from controller import ImagoController
    ctrl = ImagoController(cell_count=args.cells)
    wb   = Workbench(port=args.port, ctrl=ctrl)
    wb.serve(open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
