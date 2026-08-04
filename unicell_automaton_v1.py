"""
unicell_automaton_v1.py — pure cellular-automaton cell model.

REBUILT 2026-08-04 (Alan: "reuse the file... if it's mostly already built,
save you some work too") to catch this file up to fpga/verilog/
unicell_stripped_v1.v as it actually stands now, not as it stood on
2026-08-02 when this file was first written. Same relationship
unicell_v3.py had to the old unicell.py: a real foundation kept and
extended, not thrown away and restarted. PHASING below, mirroring
unicell_v3.py's own approach, so what's actually built vs. deferred is
never ambiguous.

Ground truth for everything in PHASE 1-4: fpga/verilog/unicell_stripped_v1.v,
cross-checked against docs/stripped-cell/CELL_INTERNALS.md (itself built by
reading that RTL file directly, 2026-08-04).

  PHASE 1 (2026-08-02, original): topology, start_flag (this file's own
    arm/ready-to-operate gate -- functionally what the real RTL's `armed`
    (#156) now also does, see Phase 4 note below), routing_mask,
    cardinal_edge (relay/consume, per-incoming), invert_out, latch_in,
    loop_back, one_shot, a basic ready/out_buffer backpressure concept.

  PHASE 2 (THIS REBUILD): two real bugs in Phase 1 fixed against the
    current RTL, not carried forward silently:
    - `ready` was a single bool that recovered on the FIRST successful
      delivery even when a fire's routing_mask targeted MULTIPLE
      neighbors -- the real RTL's `ready_bit` only recovers once EVERY
      targeted direction has genuinely acked (pending_ack all clear,
      points.md #89/#90). Replaced with a real 4-bit `pending_ack` mask.
    - relay_fire was modeled as bypassing ready entirely ("a pure
      conduit holds no state of its own"). Checked directly against the
      current RTL (unicell_stripped_v1.v line 542): relay_fire IS gated
      by `ready_bit && targets_all_ready`, exactly like can_fire -- a
      relay attempt writes the SAME shared out_buffer, so it must stall
      too if that buffer is still occupied. True when Phase 1 was
      written; the RTL was refined since (#91) and this file was never
      updated to match. Fixed.
    Also added: freeze_in (genuine external wire) + error_frozen (#154,
    internal protective latch) + relay/consume mismatch detection;
    same-cycle multi-direction OR-combine (#153, recreates the FULL
    cell's free wired-OR N-way reduction on these dedicated
    point-to-point wires); hold_in + a_reemit_in + a_update_in
    (#115/#119, the memory-cell write/reemit mechanisms -- both
    genuinely event-driven, gated on a real arrival, so they fit this
    file's tick model directly); pattern_low/pattern_equal/pattern_high
    + dynamic_route_en (#140, comparator-driven routing); is_command_cell
    (#143).

  PHASE 3 (THIS REBUILD): fb_internal_in / internal_fb_active (#118) +
    a_self_update_in (#120). In the real RTL, internal_fb_active
    recomputes EVERY CYCLE whenever hold_in && fb_internal_in are both
    held, with NO external arrival required at all -- fundamentally
    continuously-clocked, unlike everything else in this file, which is
    event-driven (a cell only gets processed when something is pending
    for it). Solved by giving Grid.tick() a SECOND, separate pass after
    the normal pending-delivery dispatch: any cell with hold_in &&
    fb_internal_in held gets internal_feedback_step() called every tick,
    unconditionally. Confirmed directly against the RTL (line 648
    onward, plus the fire_n/data_out_n assigns) that this write path
    does NOT touch pending_ack at all -- it's a private internal
    oscillation, invisible to neighbors except through the separate,
    deliberate a_reemit_in mechanism. run_to_quiescence() does NOT
    terminate an internal-feedback loop (correctly -- it's meant to run
    until explicitly stopped, same as the real RTL); call tick()
    explicitly for scenarios using this mode, matching how
    tb_stripped_v1_feedback.v exercises it on real hardware too.

  PHASE 4 (THIS REBUILD): the ID-tagged wire-level programming protocol
    (program_in/PROG_ID_*, points.md #123/#140) and the armed gate's own
    COMPLETE-with-LSB wire semantics (#156), now modeled at the actual
    protocol level -- program_word() applies one {3-bit ID, 16-bit data}
    field-write at a time, matching cell_wrapper_v2.v's own word format
    exactly. program_in (a live external wire, top priority) suspends
    ALL ordinary operation while held -- arrivals during programming are
    not consumed at all (no ack, matching the RTL's !program_in gating
    on every fire path), staying pending for retry once programming
    ends, same backpressure treatment as a frozen cell. start_flag
    (this file's arm/ready gate) is now genuinely settable via
    COMPLETE's data LSB, not just direct construction -- program_word()
    is additive, direct field mutation still works exactly as before
    for anyone who doesn't need the protocol-level fidelity.

THE ORIGINAL HYPOTHESIS THIS FILE EXISTS TO TEST (still true, unchanged):
if wiring only ever connects a cell to its immediate physical neighbor,
arbitrary addressing becomes meaningless -- there's no shared bus left to
address INTO. Every cell could, in principle, fire every single cycle,
independent of every other cell's activity -- this file measures that,
not assumes it.

Gate computation itself is UNCHANGED and always has been -- same
NOR-decomposition, same 12 topology codes, imported from
unicell_gate_core.py (points.md #164 -- extracted from unicell_v3.py as
the genuinely shared piece, per docs/shared/SYSTEM_MECHANICS.md's own
verified finding that this logic is byte-identical between both cells).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from unicell_gate_core import compute_gate, TOPO_PASS_A

_MASK32 = 0xFFFFFFFF
_MASK4 = 0xF
N, S, E, W = 0, 1, 2, 3
_DIRS = (N, S, E, W)
_DIR_BIT = {N: 0, S: 1, E: 2, W: 3}
_OPPOSITE = {N: S, S: N, E: W, W: E}

# ── Phase 4 (points.md #123/#140/#156): the ID-tagged incremental
# programming protocol, matching cell_wrapper_v2.v / unicell_stripped_v1.v
# exactly -- {3-bit ID, 16-bit data} per word, 7 real field targets + 1
# reserved COMPLETE marker (8 codes, exact fit for 3 bits).
PROG_ID_TOPOLOGY      = 0
PROG_ID_ROUTING_MASK  = 1
PROG_ID_CARDINAL_EDGE = 2
PROG_ID_PATTERN_LOW   = 3
PROG_ID_PATTERN_EQUAL = 4
PROG_ID_PATTERN_HIGH  = 5
PROG_ID_DYN_ROUTE_EN  = 6
PROG_ID_COMPLETE      = 7


@dataclass
class CACell:
    """One cell in the pure automaton model. No address fields exist at
    all -- position IS identity, fixed at construction, never
    reconfigured.

    READY / PENDING_ACK (points.md #77, #89/#90, rebuilt this phase to
    match the real RTL's multi-direction wait-for-all semantics): a fire
    that targets multiple neighbors via routing_mask must wait for EVERY
    targeted direction to ack before this cell is ready again -- not just
    the first one. `pending_ack` is a 4-bit mask (bit order matches
    routing_mask/cardinal_edge: N,S,E,W), one bit per direction still
    genuinely un-acked from the last fire. `ready` is a derived property,
    not stored state, matching the real RTL's
    `next_ready = hold_in || (next_pending_ack == 0)`.
    """
    row: int
    col: int
    topology: int = TOPO_PASS_A
    start_flag: bool = False     # this file's arm/ready-to-operate gate
                                  # (see Phase 4 note above re: `armed`)
    routing_mask: int = 0        # which neighbor direction(s) THIS cell's fire goes to
    cardinal_edge: int = 0       # per INCOMING direction: 1=relay (don't consume), 0=consume

    # ── LEGACY, from this file's OWN original 2026-08-02 exploration --
    # checked directly against the current RTL while rebuilding (2026-08-04)
    # and confirmed NONE of these four exist in unicell_stripped_v1.v at
    # all (grepped for each name, zero matches). Carried over from the
    # even-older v2/FULL-cell GS_* vocabulary this prototype started
    # from, not from anything the stripped cell actually implements
    # today. Kept ONLY for backward compatibility with this file's own
    # existing tests -- do NOT treat these as RTL-verified. The RTL's
    # actual closest equivalents are genuinely different mechanisms:
    # latch_in's "stay armed across fires" idea -> hold_in (#115);
    # loop_back's "feed output back to self" idea -> fb_internal_in
    # (#118, Phase 3, not yet built here). one_shot and invert_out have
    # no current stripped-cell equivalent at all.
    invert_out: bool = False
    latch_in: bool = False
    loop_back: bool = False
    one_shot: bool = False

    # ── Phase 2 additions (points.md #92/#115/#119/#140/#143/#154) ──
    freeze_in: bool = False              # live external wire
    error_frozen: bool = False           # internal, auto-set on relay/consume mismatch
    hold_in: bool = False
    a_reemit_in: bool = False
    a_update_in: bool = False
    fb_internal_in: bool = False         # Phase 3: internal feedback (#118)
    a_self_update_in: bool = False       # Phase 3: self-adjusting threshold (#120)
    is_command_cell: bool = False        # config-time permanent reemit-on-trigger
    pattern_low: int = 0                 # 4-bit, N/S/E/W wanted when cmp=LOW
    pattern_equal: int = 0               # ...EQUAL
    pattern_high: int = 0                # ...HIGH
    dynamic_route_en: bool = False

    # ── Phase 4 (points.md #123/#140/#156): wire-level programming ──
    program_in: bool = False             # live external wire, top priority
    program_done: bool = False           # broadcast status, mirrors ready_out's convention

    a_data: int = 0
    a_arrived: bool = False
    one_shot_fired: bool = False
    data_reg: int = 0

    out_buffer: Optional[int] = None     # the offered output -- separate from data_reg
    pending_ack: int = 0                 # 4-bit mask, bit order N,S,E,W (points.md #89/#90)

    @property
    def ready(self) -> bool:
        """Derived, not stored -- matches the RTL's next_ready formula exactly."""
        return self.hold_in or self.pending_ack == 0

    @property
    def effective_freeze(self) -> bool:
        return self.freeze_in or self.error_frozen or not self.start_flag

    @property
    def effective_hold(self) -> bool:
        return self.hold_in or self.is_command_cell

    @property
    def effective_reemit(self) -> bool:
        return self.a_reemit_in or self.is_command_cell

    def _effective_routing(self, second_val: int, input_val: int) -> int:
        """points.md #140: comparator-driven routing. dynamic_route_en=0
        (default) is purely additive-preserving: effective_routing ==
        routing_mask exactly, unchanged from every pre-#140 behavior."""
        if not self.dynamic_route_en:
            return self.routing_mask & _MASK4
        if second_val > input_val:
            selected = self.pattern_high
        elif second_val < input_val:
            selected = self.pattern_low
        else:
            selected = self.pattern_equal
        return selected & self.routing_mask & _MASK4

    def program_word(self, prog_id: int, data: int) -> None:
        """points.md #123/#140/#156: apply one incremental programming
        word, {3-bit ID, 16-bit data}, matching cell_wrapper_v2.v /
        unicell_stripped_v1.v's PROG_ID table exactly. No word-count
        state -- each word independently targets ONE field ("a scalpel,
        not a hammer"). Only takes effect while program_in is held; the
        caller is responsible for the same discipline the real wrapper
        enforces (hold program_in, send words, drop program_in when
        done) -- this method itself does not check program_in, matching
        how the RTL's case(prog_id) block is unconditional once
        programming_active is already true.
        """
        data &= 0xFFFF
        if prog_id == PROG_ID_TOPOLOGY:
            self.topology = data & 0x3FF
        elif prog_id == PROG_ID_ROUTING_MASK:
            self.routing_mask = data & _MASK4
        elif prog_id == PROG_ID_CARDINAL_EDGE:
            self.cardinal_edge = data & _MASK4
        elif prog_id == PROG_ID_PATTERN_LOW:
            self.pattern_low = data & _MASK4
        elif prog_id == PROG_ID_PATTERN_EQUAL:
            self.pattern_equal = data & _MASK4
        elif prog_id == PROG_ID_PATTERN_HIGH:
            self.pattern_high = data & _MASK4
        elif prog_id == PROG_ID_DYN_ROUTE_EN:
            self.dynamic_route_en = bool(data & 1)
        elif prog_id == PROG_ID_COMPLETE:
            # points.md #156: COMPLETE's own data LSB decides arm state
            # directly -- 1=commit+arm, 0=commit but stay/return cold.
            self.program_done = True
            self.error_frozen = False   # points.md #154: auto-clears on reprogram
            self.start_flag = bool(data & 1)
        # unrecognized ID: no-op, matches the RTL's `default: ;`

    def deliver(self, arrivals: Dict[int, int], injected: Optional[int] = None
                ) -> Tuple[bool, Optional[Tuple[int, int]]]:
        """Deliver every direction's value that arrived THIS SAME TICK
        (`arrivals`, {direction: value}), plus an optional direct external
        `injected` value (no cardinal direction -- a boundary-cell feed,
        always treated as consume since there's no wire to relay from).

        points.md #153's same-cycle OR-combine needs to see every
        simultaneous arrival together, not one at a time, to classify
        relay/consume correctly and detect a genuine mismatch.

        Returns (accepted, forward): accepted=False means this delivery
        was rejected (this cell's own output still unconsumed) and must
        be retried later, not dropped -- matching can_fire/relay_fire's
        real ready_bit gating. forward is (routing_mask, value) to
        deliver onward if this cell just fired/relayed, or None.
        """
        if not arrivals and injected is None:
            return (True, None)

        if self.program_in:
            # points.md #123: programming_active is genuinely TOP
            # priority -- suspends ordinary operation entirely, not
            # layered on top of it. No ack goes out (matches the RTL:
            # capture_now/can_fire/relay_fire all require !program_in in
            # their own definitions, so none of them fire here) -- an
            # arrival during programming is simply not consumed, exactly
            # like a frozen cell, and must be retried later.
            return (False, None)

        any_relay_dir = any((self.cardinal_edge >> _DIR_BIT[d]) & 1 for d in arrivals)
        any_consume_dir = (injected is not None) or any(
            not ((self.cardinal_edge >> _DIR_BIT[d]) & 1) for d in arrivals
        )

        # points.md #154: a well-formed model never has this by construction
        # (the compiler's job is ensuring relay/consume timing is
        # deliberate) -- if it happens anyway, genuine error, protective
        # freeze, not graceful handling (which would mask a real bug).
        if any_relay_dir and any_consume_dir:
            self.error_frozen = True
            # The offending event's OR-combine still completes THIS cycle
            # (can't be undone, matches the real RTL exactly) via the
            # consume path below -- the cell is frozen going forward
            # starting next delivery.

        arrived_val = 0
        for v in arrivals.values():
            arrived_val |= (v & _MASK32)
        if injected is not None:
            arrived_val |= (injected & _MASK32)

        is_relay = any_relay_dir and not any_consume_dir  # pure, legitimate combined-relay only

        if is_relay:
            if not self.ready:
                return (False, None)
            fired = self._emit(arrived_val)
            return (True, (self.routing_mask & _MASK4, fired))

        # ── consume path ──
        if self.effective_freeze:
            # points.md #91/#92: a frozen/disarmed cell must NOT ack --
            # ack_out requires !effective_freeze in the real RTL
            # (consumed_now = capture_now || can_fire || ..., and every
            # one of those already requires !effective_freeze). Silently
            # absorbing here (accepted=True) would clear the SENDER's
            # pending_ack immediately, defeating the entire freeze-
            # cascade backpressure mechanism (#152) this architecture is
            # built around. Must reject/retry, not drop.
            return (False, None)

        if self.effective_hold and self.effective_reemit and self.a_arrived:
            # points.md #119: pure pass-through of A, unprocessed. Needs
            # ready_bit/targets_all_ready gating too -- it writes the
            # SAME shared out_buffer as any other emit.
            if not self.ready:
                return (False, None)
            fired = self._emit(self.a_data)
            return (True, (self._effective_routing(0, 0), fired))

        if self.hold_in and self.a_update_in and self.a_arrived:
            # points.md #119: arriving value REPLACES A directly. Does
            # NOT write out_buffer -- no ready gating needed, updating
            # the held constant and offering it downstream are
            # deliberately independent steps.
            self.a_data = arrived_val
            return (True, None)

        if not self.a_arrived:
            self.a_data = arrived_val
            self.a_arrived = True
            return (True, None)

        if self.one_shot and self.one_shot_fired:
            return (True, None)

        if not self.ready:
            return (False, None)

        a = self.a_data
        b = arrived_val
        computed = compute_gate(self.topology, a, b)
        self.data_reg = computed

        if self.latch_in:
            self.a_arrived = True
            self.a_data = b
        else:
            self.a_arrived = False

        if self.loop_back:
            self.a_data = computed

        if self.one_shot:
            self.one_shot_fired = True
            self.start_flag = False

        route = self._effective_routing(b, a)
        fired = self._emit(computed, route_override=route)
        return (True, (route, fired))

    def internal_feedback_step(self) -> None:
        """points.md #118/#120, Phase 3: while hold_in && fb_internal_in
        are both held, recompute the gate against THIS cell's own
        out_buffer as the second operand, EVERY tick, independent of any
        external arrival. Genuinely different from every other mechanism
        in this file -- Grid.tick() must call this explicitly for any
        qualifying cell each tick; it will never be reached via the
        normal pending-delivery dispatch, since there may be nothing
        pending at all.

        Confirmed directly against the RTL (unicell_stripped_v1.v line
        648 onward, and the fire_n/data_out_n assigns at 712/717): this
        writes out_buffer/a_data directly and does NOT touch pending_ack
        at all -- neighbors do NOT see each oscillation tick as a new
        offering (fire_x stays driven by whatever pending_ack was last
        set by a real can_fire/relay_fire). data_out_n continuously
        exposes the current out_buffer value on the wire regardless, but
        that is a private internal loop, not a broadcast -- a_reemit_in
        remains the deliberate, separate mechanism for "now actually
        offer my current value to neighbors."

        a_self_update_in decides the destination: out_buffer (default,
        oscillates, a_data/A stays fixed) or a_data itself (#120 -- the
        threshold self-adjusts based on its own accumulated history).
        """
        if not (self.hold_in and self.fb_internal_in) or self.effective_freeze:
            return
        second_val = self.out_buffer if self.out_buffer is not None else 0
        computed = compute_gate(self.topology, self.a_data, second_val)
        if self.a_self_update_in:
            self.a_data = computed & _MASK32
        else:
            self.out_buffer = computed & _MASK32

    def _emit(self, value: int, route_override: Optional[int] = None) -> int:
        """Common tail: apply invert_out, load out_buffer, arm pending_ack
        for every targeted direction. invert_out is applied uniformly at
        this output/drain stage, not baked into which path produced the
        value -- matches the real RTL."""
        fired = (~value) & _MASK32 if self.invert_out else value & _MASK32
        self.out_buffer = fired
        route = self.routing_mask & _MASK4 if route_override is None else route_override
        self.pending_ack = route & _MASK4
        return fired


class CAGrid:
    """A grid of CACells wired ONLY to their fixed physical neighbors --
    no addressing, no shared bus, no bridges-to-elsewhere. Each cell's
    neighbor set is determined entirely by grid position, fixed at
    construction."""

    def __init__(self, rows: int, cols: int):
        self.rows, self.cols = rows, cols
        self.cells: Dict[Tuple[int, int], CACell] = {
            (r, c): CACell(row=r, col=c) for r in range(rows) for c in range(cols)
        }
        # Each pending entry: (origin_pos_or_None, direction_or_None, value).
        # origin_pos is who PRODUCED this event -- needed so a successful
        # delivery can clear the correct bit of THAT cell's pending_ack
        # (points.md #89/#90). None origin/direction = a direct external
        # injection, nothing to ack back.
        self._pending: Dict[Tuple[int, int], List[Tuple[Optional[Tuple[int, int]], Optional[int], int]]] = {}
        self.tick_count = 0

    def neighbor_pos(self, row: int, col: int, direction: int) -> Optional[Tuple[int, int]]:
        dr, dc = {N: (-1, 0), S: (1, 0), E: (0, 1), W: (0, -1)}[direction]
        pos = (row + dr, col + dc)
        return pos if pos in self.cells else None

    def inject(self, row: int, col: int, value: int) -> None:
        """External injection at a boundary cell -- the only way data
        enters the fabric at all, since there's no addressed host bus."""
        self._pending.setdefault((row, col), []).append((None, None, value))

    def confirm_read(self, row: int, col: int) -> None:
        """Explicit external confirmation that a cell's offered output has
        been consumed -- the chain-end case (points.md #77): an external
        reader acknowledges out_buffer, clearing this cell's pending_ack
        entirely so it (and, via the cascade, everything feeding it) can
        become ready for new data again."""
        self.cells[(row, col)].pending_ack = 0

    def tick(self) -> Dict[Tuple[int, int], bool]:
        """Advance every cell that has pending deliveries by one tick,
        combining SIMULTANEOUS same-cell arrivals into one call to
        deliver() (points.md #153's OR-combine) rather than processing
        them one at a time. Rejected deliveries (target not ready) are
        RE-QUEUED for the next tick, not dropped."""
        active: Dict[Tuple[int, int], bool] = {}
        outgoing: List[Tuple[Tuple[int, int], Tuple[int, int], int, int]] = []
        retry: Dict[Tuple[int, int], List[Tuple[Optional[Tuple[int, int]], Optional[int], int]]] = {}

        current = self._pending
        self._pending = {}

        for pos, events in current.items():
            cell = self.cells[pos]
            active[pos] = True

            # Split this tick's events into real-direction arrivals
            # (one wire, one value per tick each) and direct injections
            # (no direction). Both fold into ONE deliver() call so they
            # OR-combine together if both happen the same tick.
            by_dir: Dict[int, Tuple[Optional[Tuple[int, int]], int]] = {}
            injected_val = None
            injected_origin = None
            for origin, from_dir, value in events:
                if from_dir is None:
                    injected_val = (injected_val or 0) | (value & _MASK32)
                    injected_origin = origin
                else:
                    by_dir[from_dir] = (origin, value & _MASK32)

            real_dirs = {d: v for d, (_o, v) in by_dir.items()}
            accepted, result = cell.deliver(real_dirs, injected=injected_val)

            if not accepted:
                for d, (origin, value) in by_dir.items():
                    retry.setdefault(pos, []).append((origin, d, value))
                if injected_val is not None:
                    retry.setdefault(pos, []).append((injected_origin, None, injected_val))
                continue

            for d, (origin, _v) in by_dir.items():
                if origin is not None:
                    opp_bit = _DIR_BIT[_OPPOSITE[d]]
                    self.cells[origin].pending_ack &= ~(1 << opp_bit) & _MASK4
            # Injections have no origin cell to ack back to (None origin).

            if result is not None:
                mask, out_value = result
                for direction in _DIRS:
                    if (mask >> _DIR_BIT[direction]) & 1:
                        nb = self.neighbor_pos(pos[0], pos[1], direction)
                        if nb is not None:
                            outgoing.append((nb, pos, direction, out_value))

        for pos, events in retry.items():
            self._pending.setdefault(pos, []).extend(events)

        for nb, origin, out_dir, value in outgoing:
            arrive_from = _OPPOSITE[out_dir]
            self._pending.setdefault(nb, []).append((origin, arrive_from, value))

        # points.md #118, Phase 3: internal feedback runs EVERY tick for
        # any qualifying cell, independent of the pending-delivery
        # dispatch above -- genuinely continuous, not event-driven,
        # unlike everything else in this file.
        for pos, cell in self.cells.items():
            if cell.hold_in and cell.fb_internal_in and not cell.effective_freeze:
                cell.internal_feedback_step()
                active[pos] = True

        self.tick_count += 1
        return active

    def run_to_quiescence(self, max_ticks: int = 10000) -> int:
        """Run until nothing is pending anywhere. Returns ticks used."""
        ticks = 0
        while self._pending and ticks < max_ticks:
            self.tick()
            ticks += 1
        if self._pending:
            raise TimeoutError(f"did not quiesce within {max_ticks} ticks")
        return ticks
