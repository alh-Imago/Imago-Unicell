# Imago UniCell — Environment Quick Start

## WSL (Kintex-7 / openXC7 builds)

```bash
source ~/.nix-profile/etc/profile.d/nix.sh
nix develop ~/toolchain-nix
cd /mnt/c/Users/Alan/Imago-Unicell/fpga
git pull
```

### Kintex-7 builds
```bash
bash build_kintex7.sh 10     # baseline / quick check
bash build_kintex7.sh 100    # mid-scale
bash build_kintex7.sh 500    # stress / machine limit
```

---

## Windows — OSS-CAD Suite (iCEBreaker builds)

Open **OSS-CAD Suite** shell (start.bat), then:

```cmd
cd C:\Users\Alan\Imago-Unicell\fpga
git pull
```

### iCEBreaker build + flash
```cmd
yosys -p "read_verilog verilog/unicell.v verilog/unicell_array.v verilog/uart_bridge.v verilog/top_icebreaker.v; synth_ice40 -top top -json top_icebreaker.json"
nextpnr-ice40 --up5k --package sg48 --pcf constraints/icebreaker.pcf --json top_icebreaker.json --asc top_icebreaker.asc --freq 24
icepack top_icebreaker.asc top_icebreaker.bin
iceprog top_icebreaker.bin
```

### iCEBreaker tests
```cmd
python test_sync_wait.py COM4 0x2A5
python test_new_opcodes.py COM4 0x2A5
python test_all.py COM4 0x2A5
```

---

## LiteX / PCIe (WSL)

```bash
source ~/.nix-profile/etc/profile.d/nix.sh
cd ~
source litex-env/bin/activate
export PATH="/mnt/f/AMDDesignTools/2025.2/Vivado/bin:$PATH"
cd /mnt/c/Users/Alan/Imago-Unicell/pcie
python3 litepcie_unicell_top.py --build
```

---

## Git push (WSL or OSS-CAD)

```bash
git push https://alh-Imago:PASTE_PAT_HERE@github.com/alh-Imago/Imago-Unicell.git main
```

---

## Vivado Hardware Manager (program iCEBreaker or Kintex-7)

Open Vivado on Windows, then in TCL console:
```tcl
open_hw_manager
connect_hw_server
open_hw_target
program_hw_devices [get_hw_devices xc7k480t_0] -bitfile C:/Users/Alan/Imago-Unicell/fpga/build_kintex7/top_kintex7_100.bit
```
