# ledger #1115: the same design as mixed_flex_sub_flex_v1.icm-hier.json, written in the DSL.
# Three blocks in a row, each adds its own constant: A (flex, +1000) -> B (SUB, +234) -> C (flex, +5), so out = x + 1239.
# `family:` says which cell family a block is built from (flex is the default); where two families meet the assembler inserts the sub bridge by itself.
# (The DSL has no negative coordinates, so the main line is row 1 and the constants sit above it on row 0.)
# Compile:  python3 nano/dsl_cli_v1.py nano/examples/mixed_flex_sub_flex_v1.uc --target flex -o out.icm-hier.json
program mixed_fsf {
    place a_in  as ram_flowing  at (1, 0) { in: w
        out: e
        io_name: x_in
        family: flex }
    place a_k   as ram_constant at (0, 1) { out: s
        init_data: 1000
        family: flex }
    place a_add as adder        at (1, 1) { in_a: w
        in_b: n
        out: e
        family: flex }
    place a_out as ram_flowing  at (1, 2) { in: w
        out: e
        family: flex }

    place b_in  as ram_flowing  at (1, 3) { in: w
        out: e
        family: sub }
    place b_k   as ram_constant at (0, 4) { out: s
        init_data: 234
        family: sub }
    place b_add as adder        at (1, 4) { in_a: w
        in_b: n
        out: e
        family: sub }
    place b_out as ram_flowing  at (1, 5) { in: w
        out: e
        family: sub }

    place c_in  as ram_flowing  at (1, 6) { in: w
        out: e
        family: flex }
    place c_k   as ram_constant at (0, 7) { out: s
        init_data: 5
        family: flex }
    place c_add as adder        at (1, 7) { in_a: w
        in_b: n
        out: e
        family: flex }
    place c_out as ram_flowing  at (1, 8) { in: w
        out: e
        io_name: y_out
        family: flex }
}
