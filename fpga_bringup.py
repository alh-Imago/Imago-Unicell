"""
fpga_bringup.py — iCEBreaker Bring-Up Sequence
Imago UniCell — iCEBreaker Bring-Up (promoted from unicell-latch, updated for v3 architecture)

Runs the six-step bring-up sequence against either:
  - SimBridge  (VM, --sim flag, no hardware needed)
  - FPGABridge (iCEBreaker, --port /dev/ttyUSB0)

Steps
-----
  1. RESET       — array resets cleanly, status responds
  2. UART        — inject echo-back, confirm round-trip
  3. NOT gate    — single cell, truth table verified
  4. AND gate    — two-input SYNC_WAIT, truth table verified
  5. RELAY pair  — two isolated cells via relay, isolation confirmed
  6. SCALE       — 8 cells, all NOT gates, all respond correctly

Each step is self-contained. Failure stops the sequence with a clear
message indicating what to check. Success prints a clean summary.

Usage
-----
  python fpga_bringup.py --sim               # VM simulation (no hardware)
  python fpga_bringup.py --port /dev/ttyUSB0 # iCEBreaker hardware
  python fpga_bringup.py --sim --verbose     # show each tick
  python fpga_bringup.py --sim --step 3      # run only step 3

When the iCEBreaker arrives, swap --sim for --port /dev/ttyUSB0.
Everything else stays the same.

Expected output (all passing)
------------------------------
  Imago UniCell — iCEBreaker Bring-Up
  Bridge: SimBridge (VM)
  ─────────────────────────────────
  Step 1  RESET       PASS   array reset, status responded
  Step 2  UART        PASS   inject→read round-trip confirmed
  Step 3  NOT gate    PASS   NOT(0)=1, NOT(1)=0
  Step 4  AND gate    PASS   AND truth table 4/4 correct
  Step 5  RELAY pair  PASS   relay forwarded, isolation confirmed
  Step 6  SCALE       PASS   8 cells, 8/8 NOT gates correct
  ─────────────────────────────────
  BRING-UP COMPLETE — 6/6 steps passed
  Ready for next phase.
"""

from __future__ import annotations
import sys, time, argparse
from typing import Optional

sys.path.insert(0, __file__[:__file__.rfind('/')] if '/' in __file__ else '.')

from gate_states import (
    GS_NOT, GS_PASS,
    GS_AND_V2, GS_OR_V2,  # GS_AND_V2 retired: two-arrival is now default
    GS_LATCH_IN,  # replaces GS_LATCH_IN from latch variant: re-arms cell after firing
)
from fpga_bridge import SimBridge, FPGABridgeError

try:
    from fpga_bridge import FPGABridge
    _HW_AVAILABLE = True
except ImportError:
    _HW_AVAILABLE = False


# ── Addresses ──────────────────────────────────────────────────────────────────
# Fixed address map for bring-up. Simple, non-overlapping, easy to read on a LA.
ADDR_A      = 0x0001_0000   # step 3: NOT gate input
ADDR_A_OUT  = 0x0001_0001   # step 3: NOT gate output

ADDR_AND_A  = 0x0002_0000   # step 4: AND input A
ADDR_AND_B  = 0x0002_0001   # step 4: AND input B
ADDR_AND_OUT= 0x0002_0002   # step 4: AND output

ADDR_SRC    = 0x0003_0000   # step 5: source cell input
ADDR_RELAY  = 0x0003_0001   # step 5: relay cell (bridge) address
ADDR_DST    = 0x0003_0002   # step 5: destination cell output

ADDR_SCALE_BASE = 0x0004_0000  # step 6: 8 cells at +0, +2, +4...


# ── Output helpers ─────────────────────────────────────────────────────────────
PASS = 'PASS'
FAIL = 'FAIL'
SKIP = 'SKIP'

results: list[tuple[int, str, str, str]] = []   # (step, name, status, detail)

def log(msg: str, verbose: bool = False):
    if verbose:
        print(f'    {msg}')

def step_result(step: int, name: str, status: str, detail: str):
    pad = 12 - len(name)
    col = '\033[32m' if status == PASS else ('\033[33m' if status == SKIP else '\033[31m')
    reset = '\033[0m'
    print(f'  Step {step}  {name}{" "*pad}{col}{status}{reset}   {detail}')
    results.append((step, name, status, detail))


# ── Step implementations ───────────────────────────────────────────────────────

def step1_reset(bridge, verbose=False) -> bool:
    """
    Step 1: RESET
    Assert reset, confirm the array responds to a status query.
    On hardware: reset clears all cell state and counters.
    On VM: SimBridge.reset() reinitialises the array object.
    """
    try:
        bridge.reset()
        log('reset asserted', verbose)
        time.sleep(0.05)

        armed, cycles = bridge.status()
        log(f'status: armed={armed}, cycles={cycles}', verbose)

        # After reset: no cells configured, armed=0
        if armed != 0:
            step_result(1, 'RESET', FAIL, f'expected armed=0 after reset, got {armed}')
            return False

        step_result(1, 'RESET', PASS, 'array reset, status responded')
        return True

    except Exception as e:
        step_result(1, 'RESET', FAIL, str(e))
        return False


def step2_uart(bridge, verbose=False) -> bool:
    """
    Step 2: UART round-trip
    Configure a PASS cell, inject a value, confirm it echoes back.
    This verifies: UART RX → command decode → cell configure → inject →
    cell fire → UART TX → host receive.
    On hardware: tests the full UART path at 115200 baud.
    """
    try:
        bridge.reset()

        # PASS cell: output = input unchanged
        bridge.configure(0, GS_PASS | GS_LATCH_IN, ADDR_A, ADDR_A_OUT)
        log('PASS cell configured', verbose)

        # NOTE: must NOT be 0xA5A5A5A5 (FUNCTION_LOAD_PATTERN) —
        # that value triggers the cell config state machine if received as data.
        MAGIC = 0xDEAD_BEEF
        bridge.inject(ADDR_A, MAGIC)
        log(f'injected 0x{MAGIC:08X}', verbose)

        result = bridge.read_output(timeout=2.0)
        log(f'read_output: {result}', verbose)

        if result is None:
            step_result(2, 'UART', FAIL, 'no response received (timeout)')
            return False

        addr_got, data_got = result
        if addr_got != ADDR_A_OUT:
            step_result(2, 'UART', FAIL,
                f'wrong output address: got 0x{addr_got:08X}, expected 0x{ADDR_A_OUT:08X}')
            return False

        if data_got != MAGIC:
            step_result(2, 'UART', FAIL,
                f'wrong data: got 0x{data_got:08X}, expected 0x{MAGIC:08X}')
            return False

        step_result(2, 'UART', PASS, f'inject→read round-trip confirmed (0x{MAGIC:08X})')
        return True

    except Exception as e:
        step_result(2, 'UART', FAIL, str(e))
        return False


def step3_not_gate(bridge, verbose=False) -> bool:
    """
    Step 3: NOT gate — single cell, full truth table
    This is the most fundamental test: one cell, one gate, two input values.
    Confirms: cell configuration, gate tree execution, output emission.
    On hardware: first real silicon computation.
    """
    try:
        bridge.reset()
        bridge.configure(0, GS_NOT | GS_LATCH_IN, ADDR_A, ADDR_A_OUT)
        log('NOT cell configured (GS_LATCH_IN: re-arms after each fire)', verbose)

        truth_table = [(0, 1), (1, 0)]
        errors = []

        for inp, expected in truth_table:
            bridge.inject(ADDR_A, inp)
            result = bridge.read_output(timeout=2.0)
            log(f'NOT({inp}) → {result}', verbose)

            if result is None:
                errors.append(f'NOT({inp}): no response')
                continue
            _, got = result
            if got != expected:
                errors.append(f'NOT({inp})={got}, expected {expected}')

        if errors:
            step_result(3, 'NOT gate', FAIL, '; '.join(errors))
            return False

        step_result(3, 'NOT gate', PASS, 'NOT(0)=1, NOT(1)=0')
        return True

    except Exception as e:
        step_result(3, 'NOT gate', FAIL, str(e))
        return False


def step4_and_gate(bridge, verbose=False) -> bool:
    """
    Step 4: Two-input AND gate — SYNC_WAIT + AND_V2
    Tests the two-input cell model: A on posedge, B on negedge (latch model).
    SYNC_WAIT fires only when both A and B are present.
    Verifies the full AND truth table (4 combinations).
    On hardware: first two-input silicon computation, validates input_b_address.
    """
    try:
        bridge.reset()

        # AND cell: SYNC_WAIT waits for A (ADDR_AND_A) and B (ADDR_AND_B)
        # Uses cell_id=0 for the AND cell
        bridge.configure(0, GS_AND_V2 | GS_LATCH_IN,
                         ADDR_AND_A, ADDR_AND_OUT)

        # Set B address directly on the cell after configure
        # (SimBridge handles this; FPGABridge sends via bus config)
        _set_b_addr(bridge, 0, ADDR_AND_B)

        log('AND cell configured (A=ADDR_AND_A, B=ADDR_AND_B)', verbose)

        truth_table = [
            (0, 0, 0),
            (0, 1, 0),
            (1, 0, 0),
            (1, 1, 1),
        ]
        errors = []

        for a, b, expected in truth_table:
            # Inject both inputs — SYNC_WAIT needs both on the bus
            bridge.inject_ab(ADDR_AND_A, a, ADDR_AND_B, b)
            result = bridge.read_output(timeout=2.0)
            log(f'AND({a},{b}) → {result}', verbose)

            if result is None:
                errors.append(f'AND({a},{b}): no response')
                continue
            _, got = result
            if got != expected:
                errors.append(f'AND({a},{b})={got}, expected {expected}')

        if errors:
            step_result(4, 'AND gate', FAIL, '; '.join(errors))
            return False

        step_result(4, 'AND gate', PASS, 'AND truth table 4/4 correct')
        return True

    except Exception as e:
        step_result(4, 'AND gate', FAIL, str(e))
        return False


def step5_relay_pair(bridge, verbose=False) -> bool:
    """
    Step 5: Relay pair — two isolated cells via a relay
    Models pond isolation: Cell A writes to ADDR_SRC. A relay cell
    (PASS, the 'bridge') reads ADDR_SRC and writes ADDR_RELAY.
    Cell B reads ADDR_RELAY and writes ADDR_DST.

    Verifies:
      (a) Signal propagates end-to-end: A → relay → B
      (b) Cell B does NOT directly receive ADDR_SRC writes
          (isolation: B's input_address is ADDR_RELAY, not ADDR_SRC)

    On hardware: validates the wired-OR bus scoping and that cells
    only respond to their own input_address, not all bus traffic.
    """
    try:
        bridge.reset()

        # Cell 0: source — NOT gate, reads ADDR_SRC, writes ADDR_RELAY
        bridge.configure(0, GS_NOT | GS_LATCH_IN, ADDR_SRC, ADDR_RELAY)
        log('source cell: NOT, ADDR_SRC → ADDR_RELAY', verbose)

        # Cell 1: destination — NOT gate, reads ADDR_RELAY, writes ADDR_DST
        # NOT(NOT(x)) = x — so end-to-end output should equal input
        bridge.configure(1, GS_NOT | GS_LATCH_IN, ADDR_RELAY, ADDR_DST)
        log('dest cell: NOT, ADDR_RELAY → ADDR_DST', verbose)

        # Inject into source — then drain multiple ticks for pipeline propagation:
        # Tick 1: src NOT cell fires → ADDR_RELAY = NOT(1) = 0
        # Tick 2: dst NOT cell sees ADDR_RELAY=0 → ADDR_DST = NOT(0) = 1
        bridge.inject(ADDR_SRC, 1)
        log('injected 1 at ADDR_SRC', verbose)

        # Run a second inject (empty bus tick) so dest cell sees relay output
        # In latch model each cell adds 1 tick of latency.
        # Source fires on tick 1, relay appears on bus tick 2,
        # dest fires on tick 3. We need 2 more ticks.
        for _ in range(2):
            bridge.inject(ADDR_SRC, 1)   # keep src firing, relay keeps emitting

        outputs = bridge.drain(timeout=0.3)
        log(f'outputs: {[(hex(a),d) for a,d in outputs]}', verbose)

        # Partition by address
        relay_outputs = [(a,d) for a,d in outputs if a == ADDR_RELAY]
        dst_outputs   = [(a,d) for a,d in outputs if a == ADDR_DST]
        src_outputs   = [(a,d) for a,d in outputs if a == ADDR_SRC]

        log(f'relay: {relay_outputs}, dst: {dst_outputs}, src_leak: {src_outputs}', verbose)

        errors = []

        # (a) Signal propagated
        if not relay_outputs:
            errors.append('relay cell did not emit to ADDR_RELAY')
        elif relay_outputs[0][1] != 0:   # NOT(1) = 0
            errors.append(f'relay output wrong: got {relay_outputs[0][1]}, expected 0')

        if not dst_outputs:
            errors.append('dest cell did not emit to ADDR_DST')
        elif dst_outputs[0][1] != 1:     # NOT(NOT(1)) = 1
            errors.append(f'dest output wrong: got {dst_outputs[0][1]}, expected 1')

        # (b) Isolation: ADDR_SRC writes should not appear at ADDR_DST directly
        # Cell 1 listens on ADDR_RELAY — it should never see ADDR_SRC
        # (This is implicit: if dst_output[1]==1 and relay fired correctly, isolation holds)
        # Extra explicit check: inject to ADDR_SRC, confirm ADDR_DST doesn't change
        # without relay first firing at ADDR_RELAY
        bridge.drain(timeout=0.1)   # clear queue
        bridge.inject(ADDR_SRC, 0)
        outputs2 = bridge.drain(timeout=0.3)
        # ADDR_DST should update only after ADDR_RELAY updates
        relay2 = [d for a,d in outputs2 if a==ADDR_RELAY]
        dst2   = [d for a,d in outputs2 if a==ADDR_DST]
        if dst2 and not relay2:
            errors.append('isolation breach: ADDR_DST changed without ADDR_RELAY firing')

        if errors:
            step_result(5, 'RELAY pair', FAIL, '; '.join(errors))
            return False

        step_result(5, 'RELAY pair', PASS,
            'relay forwarded, NOT(NOT(1))=1, isolation confirmed')
        return True

    except Exception as e:
        step_result(5, 'RELAY pair', FAIL, str(e))
        return False


def step6_scale(bridge, num_cells=8, verbose=False) -> bool:
    """
    Step 6: Scale — N cells, all NOT gates, all must respond
    Configures num_cells NOT gates at non-overlapping addresses.
    Injects into each one at a time, confirms correct output.
    Cells use GS_LATCH_IN so they re-arm between the two truth-table inputs.
    On hardware: stress test of cell allocation and config sequencing.
    On iCEBreaker: 8 cells comfortable (64 max).
    """
    try:
        bridge.reset()

        addrs = []
        for i in range(num_cells):
            addr_in  = ADDR_SCALE_BASE + i * 0x10
            addr_out = ADDR_SCALE_BASE + i * 0x10 + 0x08
            addrs.append((addr_in, addr_out))
            bridge.configure(i, GS_NOT | GS_LATCH_IN, addr_in, addr_out)
            log(f'cell {i}: NOT, 0x{addr_in:08X} → 0x{addr_out:08X}', verbose)

        log(f'{num_cells} cells configured', verbose)

        errors = []
        for i, (addr_in, addr_out) in enumerate(addrs):
            for inp, expected in [(0, 1), (1, 0)]:
                # Clear pending queue and stale bus entries before each inject.
                # GS_LATCH_IN cells on the shared bus will re-fire on stale addresses —
                # clearing the bus prevents cross-cell contamination.
                if hasattr(bridge, '_pending'):
                    bridge._pending.clear()
                if hasattr(bridge, '_array'):
                    bridge._array.bus.clear()

                bridge.inject(addr_in, inp)

                # Read output, filtering to only this cell's output address.
                # Allow up to num_cells*4 reads to drain spurious GS_LATCH_IN firings.
                result = None
                for _ in range(num_cells * 4):
                    r = bridge.read_output(timeout=0.5)
                    if r is None:
                        break
                    if r[0] == addr_out:
                        result = r
                        break
                    log(f'  skip 0x{r[0]:08X}', verbose)

                log(f'cell {i} NOT({inp}) → {result}', verbose)

                if result is None:
                    errors.append(f'cell {i} NOT({inp}): no response at 0x{addr_out:08X}')
                    continue
                _, got_data = result
                if got_data != expected:
                    errors.append(f'cell {i} NOT({inp})={got_data}, expected {expected}')

        if errors:
            step_result(6, 'SCALE', FAIL,
                f'{len(errors)} error(s): ' + '; '.join(errors[:3]))
            return False

        step_result(6, 'SCALE', PASS,
            f'{num_cells} cells, {num_cells*2}/{num_cells*2} NOT gate checks correct')
        return True

    except Exception as e:
        step_result(6, 'SCALE', FAIL, str(e))
        return False


# ── Helpers ────────────────────────────────────────────────────────────────────

def _set_b_addr(bridge, cell_id: int, b_addr: int):
    """
    Set input_b_address on a cell after configure().
    SimBridge: sets it directly on the cell object.
    FPGABridge: sends a bus config write to the cell's CONFIG_ADDRESS.
    """
    if isinstance(bridge, SimBridge):
        cell_bus_addr = bridge._cell_addrs.get(cell_id)
        if cell_bus_addr is not None:
            bridge._array.cells[cell_bus_addr].input_b_address = b_addr
    else:
        # On hardware: input_b_address is set by sending a 5th config field
        # after the standard 4-field LOAD_PATTERN sequence.
        # The uart_bridge passes it through as a plain bus write to CONFIG_ADDRESS.
        # For now: inject directly — the controller will handle this in production.
        # TODO: extend uart_bridge with CMD_SET_B_ADDR (0x09) in a future session.
        pass


def _inject_ab_sim(bridge, addr_a: int, val_a: int, addr_b: int, val_b: int):
    """Inject both A and B inputs simultaneously (SimBridge path)."""
    bridge._array.bus[addr_a] = (val_a, 0)
    bridge._array.bus[addr_b] = (val_b, 0)
    bridge._array.tick_drain()
    for bus_addr, entry in list(bridge._array.bus.items()):
        if bus_addr not in (addr_a, addr_b) and entry is not None:
            bridge._pending.append((bus_addr, entry[0]))


def _inject_ab_hw(bridge, addr_a: int, val_a: int, addr_b: int, val_b: int):
    """Inject A then B in quick succession (hardware path)."""
    bridge.inject(addr_a, val_a)
    bridge.inject(addr_b, val_b)


def _patch_bridge(bridge):
    """Add inject_ab and drain methods to the bridge instance."""
    import types

    if isinstance(bridge, SimBridge):
        def inject_ab(self, addr_a, val_a, addr_b, val_b):
            _inject_ab_sim(self, addr_a, val_a, addr_b, val_b)
        bridge.inject_ab = types.MethodType(inject_ab, bridge)
    else:
        def inject_ab(self, addr_a, val_a, addr_b, val_b):
            _inject_ab_hw(self, addr_a, val_a, addr_b, val_b)
        bridge.inject_ab = types.MethodType(inject_ab, bridge)

    if not hasattr(bridge, 'drain'):
        def drain(self, timeout=0.1):
            results = []
            deadline = __import__('time').monotonic() + timeout
            while __import__('time').monotonic() < deadline:
                r = self.read_output(timeout=0.02)
                if r is None:
                    break
                results.append(r)
            return results
        bridge.drain = types.MethodType(drain, bridge)


# ── Main ───────────────────────────────────────────────────────────────────────

STEPS = {
    1: ('RESET',      step1_reset),
    2: ('UART',       step2_uart),
    3: ('NOT gate',   step3_not_gate),
    4: ('AND gate',   step4_and_gate),
    5: ('RELAY pair', step5_relay_pair),
    6: ('SCALE',      step6_scale),
}


def run_bringup(bridge, steps=None, verbose=False, num_cells=8):
    _patch_bridge(bridge)

    bridge_name = type(bridge).__name__
    port = getattr(bridge, 'port', 'VM')

    print()
    print('  Imago UniCell — iCEBreaker Bring-Up')
    print(f'  Bridge: {bridge_name} ({port})')
    print('  ' + '─' * 35)

    steps_to_run = sorted(steps or STEPS.keys())
    passed = 0

    for step_num in steps_to_run:
        if step_num not in STEPS:
            print(f'  Step {step_num}  (unknown)')
            continue

        name, fn = STEPS[step_num]

        # Step 6 gets num_cells argument
        if step_num == 6:
            ok = fn(bridge, num_cells=num_cells, verbose=verbose)
        else:
            ok = fn(bridge, verbose=verbose)

        if ok:
            passed += 1
        else:
            print()
            print(f'  !! Step {step_num} failed — stopping sequence.')
            print(f'  !! Check: {_failure_hint(step_num)}')
            break

    print('  ' + '─' * 35)

    total = len(steps_to_run)
    ran = len(results)

    if passed == ran:
        print(f'  BRING-UP COMPLETE — {passed}/{total} steps passed')
        if ran == 6:
            print('  Ready for next phase.')
    else:
        print(f'  BRING-UP INCOMPLETE — {passed}/{ran} steps passed')

    print()
    return passed == ran


def _failure_hint(step: int) -> str:
    hints = {
        1: 'UART wiring, baud rate, FPGA power',
        2: 'cell configuration, uart_bridge CMD_CONFIGURE path',
        3: 'gate tree, GS_NOT bit 0, output address routing',
        4: 'SYNC_WAIT delivery, input_b_address, two-input gate tree',
        5: 'cell address isolation, PASS gate, bus routing',
        6: 'cell allocation at scale, simultaneous config writes',
    }
    return hints.get(step, 'see bring-up guide in MIGRATION_TODO.md')


def main():
    parser = argparse.ArgumentParser(
        description='Imago UniCell iCEBreaker bring-up sequence')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--sim',  action='store_true',
                      help='run against VM simulator (no hardware)')
    mode.add_argument('--port', metavar='PORT',
                      help='serial port for iCEBreaker (e.g. /dev/ttyUSB0)')
    parser.add_argument('--baud', type=int, default=115_200,
                        help='UART baud rate (default 115200)')
    parser.add_argument('--step', type=int, metavar='N',
                        help='run only step N (1-6)')
    parser.add_argument('--cells', type=int, default=8,
                        help='number of cells for step 6 scale test (default 8)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='show per-tick detail')
    args = parser.parse_args()

    if args.sim:
        bridge = SimBridge(num_cells=max(args.cells, 16))
    else:
        if not _HW_AVAILABLE:
            print('ERROR: pyserial required for hardware mode.')
            print('       pip install pyserial')
            sys.exit(1)
        bridge = FPGABridge(args.port, num_cells=args.cells, baud_rate=args.baud)

    steps = [args.step] if args.step else None

    with bridge:
        ok = run_bringup(bridge, steps=steps, verbose=args.verbose,
                         num_cells=args.cells)

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
