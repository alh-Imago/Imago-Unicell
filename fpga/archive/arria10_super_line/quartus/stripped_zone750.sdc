# stripped_zone750.sdc — points.md #150: 750-cell zone, Alan's actual
# per-zone target.
#
# points.md #237: clk_div retargeted from a mechanically-fixed 25MHz
# generated clock to a direct 200MHz override, per Alan's explicit
# request ("drop the clock to 200 and see what that does") -- the #229
# plan's real floor, not a chased maximum. NOTE: on real hardware,
# div_cnt[1] genuinely only toggles at CLK_100M/4 = 25MHz (no PLL in
# this design) -- this constraint is a Fitter/STA target for
# characterizing the routed design's real timing margin, same
# technique evidently used for every prior Fmax/slack figure in this
# investigation (the previously-committed generated-clock definition
# could not have produced the -2.852ns/259.61MHz figures already in
# points.md against a real 40ns budget -- flagged as a genuine, unresolved
# discrepancy, not silently corrected past). If a real 200MHz operating
# clock is ever wanted on actual silicon, this design needs a PLL --
# not yet added, separate follow-on work.

create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]

create_clock -name clk_div -period 5.000 [get_registers {div_cnt[1]}]

derive_clock_uncertainty

set_false_path -to [get_ports {LED0_N LED1_N}]
