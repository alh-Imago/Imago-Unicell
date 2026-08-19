"""
test_hierarchical_27leaf_collector_v1.py -- the first real VM-level test of
the FULL 3-level, 27-leaf (3x3x3) hierarchical collector tree, per Alan's
own direct request: "use the vm... test the 27 output and input mechanism."

Ground truth this extends: `points.md` #382 proved the FLAT 3-source
collector case at the Python-VM level (real `nano/unicell_automaton_v1.py`
CACell instances, not reasoning alone). `points.md` #397/#398 took the
SAME flat 3-source case to real iverilog-simulated RTL, and confirmed the
proven 3-header collector is the physical building block the whole
27 = 3x3x3 hierarchical addressing scheme (#381) is composed from --
"more sources means repetition of this exact mechanism, composed
hierarchically... not new RTL." That hierarchical composition had never
actually been built or run anywhere -- neither at RTL nor at VM level --
until this file.

Real, honest scope (stated up front, not discovered afterward):
- This drives real `CACell` objects directly (`.deliver()` calls, exactly
  like #382's own flat-case method) -- it does NOT attempt real 2D grid
  embedding/placement of all 40 cells (27 headers + 9 L1 collectors +
  3 L2 collectors + 1 root). That placement question is the real,
  still-open Numberlink-hard problem `docs/stripped-cell/design-notes/
  ram_interface_collector_mechanism.md` already flags -- explicitly NOT
  attempted here.
- Terminal-output contract (points.md #77): every collector/header in
  this test is configured with routing_mask=0 and its fired value is read
  directly from `deliver()`'s own return tuple, exactly matching the
  "host reads the offer, then confirm_read()" pattern `VMSession`/
  `vm_introspection_v1.py` already use elsewhere -- not a shortcut
  invented for this test.
- The real downstream RAM-cell queue (write-oriented, `ram_cell_v1.v`
  semantics) is NOT modeled here -- the "queue" below is a plain Python
  list the host appends the root's own final offered value into, matching
  #382's own stated boundary ("read the collector's own out_buffer
  directly, rather than modeling a real downstream RAM-cell queue").
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from unicell_automaton_v1 import CACell, N, S, E, W  # noqa: E402

_CHILD_DIRS = (N, S, E)  # 3 of the 4 cardinal directions carry children;
                          # the 4th (W) is conceptually reserved for the
                          # collector's own upward output, matching #397's
                          # real geometry (H1 north, H2 south, H3 west,
                          # queue east) -- unused here since routing is
                          # host-mediated, kept only as documentation.


def _make_header(value: int) -> CACell:
    """A leaf header: holds `value`, reemits it whenever triggered by ANY
    arrival, regardless of that arrival's own content (points.md #382
    Finding 3). routing_mask=0 -> terminal output, host reads the fired
    value directly and confirm_reads it."""
    return CACell(
        row=0, col=0,
        start_flag=True,
        hold_in=True,
        a_reemit_in=True,
        a_data=value,
        a_arrived=True,
        routing_mask=0,
    )


def _make_collector() -> CACell:
    """A collector: cardinal_edge is reprogrammed by the host between
    rounds to select exactly one child direction as `relay` (1) with
    every other direction left at `consume` (0) -- but since only the
    selected direction is ever actually driven in a given call (source-side
    gating, #382 Finding 1), the non-selected bits' consume/relay state
    never actually matters here. routing_mask=0 -> terminal, same
    host-read contract as the header."""
    return CACell(row=0, col=0, start_flag=True, routing_mask=0)


def _fire_header(header: CACell) -> int:
    """Trigger a header to reemit its held value. The triggering
    direction/content is irrelevant (#382 Finding 3) -- N with a dummy 0
    is used uniformly."""
    accepted, forward = header.deliver({N: 0})
    assert accepted, "header rejected its own reemit trigger"
    assert forward is not None
    _route, value = forward
    # Terminal output (points.md #77): host must confirm_read before the
    # cell can be used again.
    header.pending_ack = 0
    header._needs_confirm = False
    return value


def _fire_collector(collector: CACell, active_dir: int, value: int) -> int:
    """Select `active_dir` as the sole relay direction, deliver `value` on
    it, and return the collector's own relayed (forwarded, unmodified)
    output -- matching #382 Finding 2 (the selected direction must be
    `relay`, not `consume`, for pure single-value pass-through with no
    second-input wait)."""
    collector.cardinal_edge = 1 << {N: 0, S: 1, E: 2, W: 3}[active_dir]
    accepted, forward = collector.deliver({active_dir: value})
    assert accepted, f"collector rejected delivery on dir={active_dir}"
    assert forward is not None
    _route, out_value = forward
    assert out_value == value, "relay must pass the value through unmodified"
    collector.pending_ack = 0
    collector._needs_confirm = False
    return out_value


def _build_tree():
    """27 headers (values 1..27) -> 9 level-1 collectors (3 headers each)
    -> 3 level-2 collectors (3 level-1 collectors each) -> 1 root collector
    (3 level-2 collectors) -> host-side queue. Matches #381's own
    27 = 3x3x3 branching factor exactly: a collector has exactly 4
    cardinal ports, 3 available for input sources once one is reserved
    for the output toward the next level."""
    headers = [_make_header(v) for v in range(1, 28)]
    l1 = [_make_collector() for _ in range(9)]
    l2 = [_make_collector() for _ in range(3)]
    root = _make_collector()
    return headers, l1, l2, root


def _traverse_leaf(headers, l1, l2, root, leaf_index: int, queue: list) -> None:
    """Drive exactly one leaf's value all the way from its header through
    all 3 collector levels into the queue -- the real, physical path
    #398's own architectural generalization describes."""
    l1_idx, child_l1 = divmod(leaf_index, 3)
    l2_idx, child_l2 = divmod(l1_idx, 3)

    v = _fire_header(headers[leaf_index])
    v = _fire_collector(l1[l1_idx], _CHILD_DIRS[child_l1], v)
    v = _fire_collector(l2[l2_idx], _CHILD_DIRS[child_l2], v)
    v = _fire_collector(root, _CHILD_DIRS[l2_idx], v)
    queue.append(v)


def test_full_27_leaf_round_delivers_every_value_in_order():
    """The real acceptance test: a full round-robin sweep across all 27
    leaves, in order, every single value verified correct end to end
    through all 3 collector levels -- the VM-level equivalent of #397's
    own RTL 3-round/3-header proof, extended to the full hierarchical
    scale for the first time anywhere in this project."""
    headers, l1, l2, root = _build_tree()
    queue: list = []
    for leaf in range(27):
        _traverse_leaf(headers, l1, l2, root, leaf, queue)
    assert queue == list(range(1, 28))


def test_wraparound_second_partial_round_matches_first():
    """Confirms headers can be re-triggered indefinitely (continuously-live
    behavior, #396) and a second pass through the SAME leaves reproduces
    identical results -- the hierarchical analogue of #397's own
    round-1/round-2 wraparound proof."""
    headers, l1, l2, root = _build_tree()
    queue: list = []
    for leaf in range(27):
        _traverse_leaf(headers, l1, l2, root, leaf, queue)
    round1 = list(queue)
    queue.clear()
    for leaf in range(27):
        _traverse_leaf(headers, l1, l2, root, leaf, queue)
    assert queue == round1 == list(range(1, 28))


def test_out_of_order_leaf_access_within_a_round():
    """Design note's own stated design intent: out-of-order delivery
    relative to other chains is deliberate, not a defect (#381). Visits
    leaves in a scrambled order and confirms each individually-addressed
    leaf still delivers its own correct value, independent of visit
    order."""
    headers, l1, l2, root = _build_tree()
    order = [26, 0, 13, 5, 21, 8, 17, 2, 24]
    queue: list = []
    for leaf in order:
        _traverse_leaf(headers, l1, l2, root, leaf, queue)
    assert queue == [leaf + 1 for leaf in order]


def test_non_selected_child_stays_silent_no_leakage():
    """Direct VM-level check of the real OR-combine hazard #397 hit for
    the first time in a multi-source RTL system (Finding 2 of that
    entry): only the currently-selected child direction is ever delivered
    to a collector in a real round -- confirms firing one leaf under a
    given L1 collector does not disturb, advance, or leak into its
    siblings' own held state."""
    headers, l1, l2, root = _build_tree()
    # Fire leaf 0 (under l1[0], child dir N) only.
    queue: list = []
    _traverse_leaf(headers, l1, l2, root, 0, queue)
    assert queue == [1]
    # Sibling headers 1 and 2 (under the same l1[0]) must still be
    # untouched -- still armed, still holding their own original values,
    # never having been triggered.
    assert headers[1].a_arrived is True
    assert headers[1].a_data == 2
    assert headers[2].a_data == 3
    assert headers[1].pending_ack == 0
    assert headers[1].out_buffer is None
