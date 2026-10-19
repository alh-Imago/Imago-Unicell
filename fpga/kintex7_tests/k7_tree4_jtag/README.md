# k7_tree4_jtag_v1 -- read the design's own state out of the Kintex chip over JTAG (ledger #1239)

Same as k7_tree4_v1 (Tang std_tree4 design, unchanged, compared byte for byte, LEDs show PASS) plus a JTAG user register that a host can read:
96 bits: 0x554E4943 ("UNIC"), a clock counter, and the wrapper's own registers (seen / bad / timeout / idx). It is the first step towards
Alan's idea of freezing the design and reading the latch states.

Three steps, each only after the one before worked. Nothing here writes the card's flash or sends a configuration instruction.

**A. Can OpenOCD see the chip through this cable? (no bitstream needed)**
    nix shell nixpkgs#openocd          # adds OpenOCD to the openXC7 shell; a download the first time
    sh scan_chain.sh                   # expect: one TAP, xc7.tap, IDCODE 0x23751093.  (if permission denied: sudo env "PATH=$PATH" sh scan_chain.sh)

**B. Build and load (the open question: can nextpnr-xilinx place a BSCANE2? the build is the test)**
    copy this folder into demo-projects (next to blinky-ypcb003381p1), then:  make   and   make program JTAG_LINK="-c ft232"
    The LEDs must show the same PASS pattern as k7_tree4_v1 (green, yellow, green + yellow, off; red off).
    If `make` stops with an error mentioning BSCANE2 or an unknown cell, paste it: that is the answer to the question.

**C. Read the register**
    sh read_user1.sh                   # prints the three words and what they mean
    Expect word0 = 0x554E4943, a counter that differs on every read, and seen=1 bad=0 timeout=0.

The OpenOCD config uses the pin table openFPGALoader uses for its "ft232" cable (FT232H, 0403:6014, TCK/TDI/TDO/TMS on the low four pins). I read that
table in openFPGALoader v1.1.1 (the version you have); I have not run OpenOCD against your cable.
