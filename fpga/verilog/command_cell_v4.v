// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// command_cell_v4.v — the 9th unified-carrier core, the "9th-core
// question" `compare_cell_v4.v`'s own header already flagged as
// parked. Built directly from the resolved design in
// `docs/stripped-cell/design-notes/command_core_scope_v2.md`
// (`points.md` #628, #641, #642, #643) -- a real, live, multi-session
// design discussion, not a fresh guess. Nothing in that note is
// contradicted here; this is the first real RTL for it.
//
// ONE core, mode-selected (`mode`), deployed as TWO simultaneously-
// active instances in a real topology -- same real pattern
// `ram_cell_v4.v`'s own `fixed_mode` bit already uses:
//   mode=0 (TRIGGER):   watches a real buffer stream (any of the 4
//                        real cardinal directions, direction-agnostic,
//                        OR-combined -- the same idiom `freeze_in`
//                        already uses on the shells, `#639`) for a
//                        single, real, config-set 4-bit toggle
//                        pattern. It is the outermost gate in the
//                        whole pipeline, so it detects its OWN start:
//                        a genuine symmetric toggle -- first match
//                        unfreezes the buffer direction (real start-
//                        of-burst), second match refreezes it (real
//                        end-of-burst). `polarity` sets which state
//                        it rests in.
//   mode=1 (PROGRAMMER): downstream of trigger mode's own gating, so
//                        its own toggle side is genuinely OFF, not
//                        merely unused -- it starts on the first real
//                        arrival while idle (no pattern match needed
//                        to start), freezes its real target, asserts
//                        `program_out`, and relays each captured word
//                        onto the target's real programming channel
//                        (the mirror image of every other core's own
//                        RECEIVE-side prog_data_in_x/prog_arrived_in_x/
//                        prog_ack_out_x -- this is the DRIVE side, new
//                        to this core alone in the family), paced by
//                        the target's own real, freeze-safe
//                        `prog_ack_in` (never ordinary `ack_in` --
//                        ordinary ack is dead under freeze, confirmed
//                        against `nano_gate_v4.v`'s own
//                        `!effective_freeze` gating on every
//                        `consumed_now` path -- exactly why the
//                        programming channel has its own separate ack
//                        lines at all). The SAME comparator identifies
//                        which relayed word is the real terminating
//                        one (matched against `toggle_pattern`, fixed
//                        at config time to the target's own real
//                        `PROG_ID_COMPLETE` value) -- one-shot match,
//                        not a toggle. Only once THAT word is
//                        confirmed via `prog_ack_in` does it drop
//                        `program_out` and release the target's
//                        freeze.
//
// Real, deliberate design choice, stated plainly: `toggle_pattern`
// compares against bits [23:20] of the watched/relayed 32-bit word --
// the real `PROG_ID` field position for 4-bit-ID targets (nano/
// branch), a strict superset of the 3-bit-ID position [22:20] the
// other six cores use. For a narrow-ID target, configure
// `toggle_pattern` to the zero-extended 3-bit value (e.g. `4'b0111`
// for `PROG_ID_COMPLETE=3'd7`) -- this relies on bit[23] being 0 in a
// well-formed transaction for a narrow-ID target, matching this
// project's own convention of leaving unused high bits at 0, NOT a
// hardware-enforced guarantee. Worth real, later scrutiny if a
// narrow-ID target's own word format ever legitimately uses bit[23].
//
// Real, confirmed, sidesteps a genuine hazard: ONE shared toggle-
// pattern register, not separate activate/deactivate patterns -- an
// activate value equal to a deactivate value would race under a
// naive two-field design; with one shared toggle, "equal" isn't even
// a distinguishable case, it's just "flip on this value."
//
// Real, deliberate scope limit, stated explicitly: `toggle_pattern`
// is config-time-only in this build, set via the ordinary `cfg_data`/
// `PROG_ID` mechanism like any other field (explicitly NOT via this
// cell's own trigger/programmer mechanism, which would be circular).
// Live reconfiguration while actively watching is real, separate,
// deferred work, matching how the addon-chain question (also not
// included here -- this core never produces a dataflow value for it
// to act on) and `#628`'s own 256-address dynamic targeting were both
// set aside rather than solved speculatively.
//
// Real, confirmed free consequence, not a mechanism built here: in
// TRIGGER mode, freezing the buffer's head cell (this cell's own
// `freeze_out`) cascades a full stall through an entire real
// `ram_shell_v1` chain on its own, via ordinary ready/ack backpressure
// (`ready_out` on every downstream core is gated `!effective_freeze`)
// -- no per-cell freeze logic needed anywhere in that chain.
//
// cfg_data[63:0] field map (atomic boot-load path):
//   [0]     mode            — 0=trigger, 1=programmer
//   [1]     polarity        — 0=rest frozen (trigger mode only,
//                             meaningless in programmer mode), 1=rest
//                             open
//   [4:2]   drive_dir       — single fixed direction the ACTION lands
//                             on (freeze in trigger mode; freeze+
//                             program in programmer mode), 0=N 1=S
//                             2=E 3=W, 4-7 reserved for the real,
//                             later 6-way cardinal expansion — same
//                             real shape as `branch_cell_v4.v`'s own
//                             `upstream_dir`
//   [8:5]   toggle_pattern  — the single, shared, config-set 4-bit
//                             comparator value (see above)
//   [63:9]  reserved
`default_nettype none
`timescale 1ns / 1ps

module command_cell_v4 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,
    input  wire         active,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,

    // ── Watch side: the real buffer stream. This cell never offers
    // ordinary data downstream -- it only watches (both modes) and,
    // in programmer mode, relays via the separate programming-drive
    // channel below -- so there is no data_out/fire/ready_in/ack_in
    // on this side, only a real ack_out. ──
    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,
    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    output wire         ready_out,

    // ── Real, NEW: freeze-drive output -- no core in this family
    // currently drives freeze, only receives it. Only the configured
    // `drive_dir` direction ever asserts; the other three stay 0. ──
    output wire         freeze_out_n, freeze_out_s, freeze_out_e, freeze_out_w,

    // ── Real, NEW: programming-channel-DRIVE output (programmer mode
    // only) -- the mirror image of every other core's own RECEIVE-
    // side prog_data_in_x/prog_arrived_in_x/prog_ack_out_x. Only the
    // `drive_dir` direction ever asserts program_out/prog_data_out/
    // prog_arrived_out; only that same direction's prog_ack_in is
    // ever meaningfully read. ──
    output wire         program_out_n, program_out_s, program_out_e, program_out_w,
    output wire [31:0]  prog_data_out_n, prog_data_out_s, prog_data_out_e, prog_data_out_w,
    output wire         prog_arrived_out_n, prog_arrived_out_s, prog_arrived_out_e, prog_arrived_out_w,
    input  wire         prog_ack_in_n, prog_ack_in_s, prog_ack_in_e, prog_ack_in_w,

    // ── Standard RECEIVE-side programming channel -- this cell's OWN
    // config fields (mode/polarity/drive_dir/toggle_pattern) are set
    // via this, exactly like every other core in the family. Separate
    // and distinct from the DRIVE-side channel above. ──
    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    input  wire         freeze_in,

    output wire         status_active,
    output wire         status_freeze_state
);

    reg        mode           = 1'b0;
    reg        polarity       = 1'b0;
    reg [2:0]  drive_dir      = 3'h0;
    reg [3:0]  toggle_pattern = 4'h0;
    reg        armed          = 1'b0;

    reg        freeze_state   = 1'b0;   // trigger mode: the toggled freeze level
    reg        active_r       = 1'b0;   // programmer mode: currently relaying / target frozen
    reg [31:0] held_word      = 32'h0;  // programmer mode: captured word awaiting relay/confirm
    reg        word_pending   = 1'b0;   // programmer mode: held_word awaiting prog_ack confirm

    wire effective_freeze = freeze_in;
    wire effective_armed  = armed && active;

    // ── Real, direction-agnostic recognition -- any of the 4 real
    // directions, priority N>S>E>W on simultaneous arrival (matching
    // this project's own established programming-channel priority-
    // select convention), NOT a configured watch-direction. ──
    wire watch_sel_n = arrived_n;
    wire watch_sel_s = arrived_s && !arrived_n;
    wire watch_sel_e = arrived_e && !arrived_n && !arrived_s;
    wire watch_sel_w = arrived_w && !arrived_n && !arrived_s && !arrived_e;
    wire watch_any_arrived = watch_sel_n | watch_sel_s | watch_sel_e | watch_sel_w;
    wire [31:0] watch_val = watch_sel_n ? data_in_n :
                            watch_sel_s ? data_in_s :
                            watch_sel_e ? data_in_e :
                                          data_in_w;

    wire toggle_match = (watch_val[23:20] == toggle_pattern);

    // Trigger mode: every real arrival is acked immediately,
    // unconditionally -- this cell is a pure passive observer, never
    // holding or blocking the buffer's own real offer (both this cell
    // and the paired programmer-mode instance multicast-consume the
    // same buffer stream; both must ack for the buffer's own real
    // `next_pending_ack` to clear).
    // Programmer mode: acked only when ready to capture (ordinary
    // "consume when ready" semantics, matching `ram_cell_v4.v`'s own
    // `capture_now`).
    wire watch_capture_now = mode
        ? (watch_any_arrived && !word_pending && !effective_freeze && effective_armed && !program_in)
        : (watch_any_arrived && !effective_freeze && effective_armed && !program_in);

    assign ack_out_n = watch_capture_now && watch_sel_n;
    assign ack_out_s = watch_capture_now && watch_sel_s;
    assign ack_out_e = watch_capture_now && watch_sel_e;
    assign ack_out_w = watch_capture_now && watch_sel_w;

    assign ready_out = effective_armed && !effective_freeze && (mode ? !word_pending : 1'b1);

    // ── Real programming-channel-drive, programmer mode only. ──
    wire prog_offer_active = mode && active_r && word_pending;
    assign prog_data_out_n = (drive_dir == 3'd0) ? held_word : 32'h0;
    assign prog_data_out_s = (drive_dir == 3'd1) ? held_word : 32'h0;
    assign prog_data_out_e = (drive_dir == 3'd2) ? held_word : 32'h0;
    assign prog_data_out_w = (drive_dir == 3'd3) ? held_word : 32'h0;
    assign prog_arrived_out_n = prog_offer_active && (drive_dir == 3'd0);
    assign prog_arrived_out_s = prog_offer_active && (drive_dir == 3'd1);
    assign prog_arrived_out_e = prog_offer_active && (drive_dir == 3'd2);
    assign prog_arrived_out_w = prog_offer_active && (drive_dir == 3'd3);

    assign program_out_n = mode && active_r && (drive_dir == 3'd0);
    assign program_out_s = mode && active_r && (drive_dir == 3'd1);
    assign program_out_e = mode && active_r && (drive_dir == 3'd2);
    assign program_out_w = mode && active_r && (drive_dir == 3'd3);

    // ── Real, freeze-safe confirmation -- prog_ack_in only, never
    // ordinary ack (dead under freeze). ──
    wire prog_ack_selected = (drive_dir == 3'd0) ? prog_ack_in_n :
                             (drive_dir == 3'd1) ? prog_ack_in_s :
                             (drive_dir == 3'd2) ? prog_ack_in_e :
                                                   prog_ack_in_w;
    wire relay_confirmed    = mode && active_r && word_pending && prog_ack_selected;
    wire relay_word_matched = (held_word[23:20] == toggle_pattern);

    // ── Real, NEW freeze-drive output, shared by both modes -- only
    // `drive_dir` ever asserts. ──
    wire driven_freeze_bit = mode ? active_r : freeze_state;
    assign freeze_out_n = driven_freeze_bit && (drive_dir == 3'd0);
    assign freeze_out_s = driven_freeze_bit && (drive_dir == 3'd1);
    assign freeze_out_e = driven_freeze_bit && (drive_dir == 3'd2);
    assign freeze_out_w = driven_freeze_bit && (drive_dir == 3'd3);

    assign status_active       = active_r;
    assign status_freeze_state = freeze_state;

    // ── Standard RECEIVE-side programming channel -- same real
    // priority-select shape as every other core in the family. ──
    localparam [2:0] PROG_ID_MODE           = 3'd0;
    localparam [2:0] PROG_ID_POLARITY       = 3'd1;
    localparam [2:0] PROG_ID_DRIVE_DIR      = 3'd2;
    localparam [2:0] PROG_ID_TOGGLE_PATTERN = 3'd3;
    localparam [2:0] PROG_ID_COMPLETE       = 3'd7;

    wire prog_any_arrived = prog_arrived_in_n | prog_arrived_in_s | prog_arrived_in_e | prog_arrived_in_w;
    wire prog_sel_n = prog_arrived_in_n;
    wire prog_sel_s = prog_arrived_in_s && !prog_arrived_in_n;
    wire prog_sel_e = prog_arrived_in_e && !prog_arrived_in_n && !prog_arrived_in_s;
    wire prog_sel_w = prog_arrived_in_w && !prog_arrived_in_n && !prog_arrived_in_s && !prog_arrived_in_e;
    wire [31:0] prog_data_val = prog_sel_n ? prog_data_in_n :
                                prog_sel_s ? prog_data_in_s :
                                prog_sel_e ? prog_data_in_e :
                                             prog_data_in_w;
    wire [2:0]  prog_id   = prog_data_val[22:20];
    wire [19:0] prog_word = prog_data_val[19:0];

    wire programming_active = program_in && active && prog_any_arrived;
    assign program_done = program_done_r;
    reg   program_done_r = 1'b0;

    assign prog_ack_out_n = programming_active && prog_sel_n;
    assign prog_ack_out_s = programming_active && prog_sel_s;
    assign prog_ack_out_e = programming_active && prog_sel_e;
    assign prog_ack_out_w = programming_active && prog_sel_w;

    always @(posedge clk) begin
        if (rst) begin
            mode            <= 1'b0;
            polarity        <= 1'b0;
            drive_dir       <= 3'h0;
            toggle_pattern  <= 4'h0;
            armed           <= 1'b0;
            freeze_state    <= 1'b0;
            active_r        <= 1'b0;
            held_word       <= 32'h0;
            word_pending    <= 1'b0;
            program_done_r  <= 1'b0;
        end else if (cfg_valid) begin
            mode            <= cfg_data[0];
            polarity        <= cfg_data[1];
            drive_dir       <= cfg_data[4:2];
            toggle_pattern  <= cfg_data[8:5];
            // Real, deliberate: the cell's own operating state
            // (freeze_state/active_r/word_pending) re-initializes on
            // a fresh full configuration, same real convention as
            // every other core's own data_valid/pending_ack reset on
            // cfg_valid. freeze_state starts at the configured rest
            // state (!polarity: polarity=0 -> rest frozen -> 1).
            freeze_state    <= !cfg_data[1];
            active_r        <= 1'b0;
            held_word       <= 32'h0;
            word_pending    <= 1'b0;
            armed           <= 1'b1;
        end else if (programming_active) begin
            case (prog_id)
                PROG_ID_MODE:           mode           <= prog_word[0];
                PROG_ID_POLARITY:       polarity       <= prog_word[0];
                PROG_ID_DRIVE_DIR:      drive_dir      <= prog_word[2:0];
                PROG_ID_TOGGLE_PATTERN: toggle_pattern <= prog_word[3:0];
                PROG_ID_COMPLETE: begin
                    program_done_r <= 1'b1;
                    armed          <= prog_word[0];
                end
                default: ;
            endcase
        end else begin
            if (!mode) begin
                // ── TRIGGER mode: genuine symmetric toggle. Flip only
                // on a real, matching, consumed arrival -- every
                // arrival is acked (above), but only a MATCH flips
                // the state. ──
                if (watch_capture_now && toggle_match) begin
                    freeze_state <= !freeze_state;
                end
            end else begin
                // ── PROGRAMMER mode: no toggle. Start on plain first
                // arrival while idle; stop on a confirmed match. ──
                if (watch_capture_now) begin
                    held_word    <= watch_val;
                    word_pending <= 1'b1;
                    active_r     <= 1'b1;
                end

                if (relay_confirmed) begin
                    word_pending <= 1'b0;
                    if (relay_word_matched) begin
                        active_r <= 1'b0;
                    end
                end
            end

            if (!program_in) program_done_r <= 1'b0;
        end
    end

endmodule
