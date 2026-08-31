// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// debug_issp_probe_v1.v — points.md #528/#529: a minimal, reusable
// wrapper around the real `issp` IP core (In-System Sources and
// Probes), matching Alan's own real generated config exactly
// (issp.qsys: probe_width=2, source_width=1, create_source_clock=
// false -- confirmed directly from the uploaded .qsys, not assumed).
// Since create_source_clock is false, the generated `issp` module has
// only two ports (`source`, `probe`) -- no clock port to wire.
//
// PURPOSE: a real, unambiguous, JTAG-readable answer to "did this
// self-test's own error flag ever latch" that doesn't depend on
// whether a physical LED is actually wired to whatever pin Quartus's
// fitter happened to place LED0_N/LED1_N on (the real, still-open
// question from #528). `read_probe_data` (quartus_stp) gives an
// instant snapshot of the CURRENT value -- no waveform capture, no
// live clock-watching needed, matching Alan's own real question.
//
// probe[0] = err_sticky   -- the self-test's own real latched result
// probe[1] = heartbeat    -- proves the design is genuinely clocking
//                            (alive), not just stuck in reset --
//                            without this, a stuck-at-0 err_sticky
//                            could mean "passed" OR "frozen before
//                            ever reaching a real check"
//
// source is real but unused here (source_width=1, tied to 0) -- this
// wrapper is read-only by design; nothing needs to be injected back
// into the fabric for a pass/fail check.
`default_nettype none
`timescale 1ns / 1ps

module debug_issp_probe_v1 (
    input wire err_sticky,
    input wire heartbeat
);

    wire [0:0] source;   // unused, real per the generated IP's source_width=1
    wire [1:0] probe = {heartbeat, err_sticky};

    issp issp_inst (
        .source (source),
        .probe  (probe)
    );

endmodule
