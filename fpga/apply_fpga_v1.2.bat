@echo off
setlocal enabledelayedexpansion

:: apply_fpga_v1.2.bat
:: Applies Claudette v1.2 Verilog updates to your Imago-Unicell repository
::
:: HOW TO USE:
::   1. Copy all files from this folder into your Imago-Unicell repo directory
::   2. Open a command prompt in that directory
::   3. Run:  apply_fpga_v1.2.bat

echo.
echo ================================================
echo  Claudette v1.2 - FPGA Verilog + Bridge Update
echo ================================================
echo.
echo Changes:
echo   unicell.v       - CONFIG_ADDRESS parameter (fixed config address)
echo                   - GS_FALL_EDGE (bit 24) on negedge clk
echo                   - freeze line active
echo   unicell_array.v - CONFIG_ADDRESS, clk_n, freeze per cell
echo                     NUM_CELLS default = 32 for safe bring-up
echo   uart_bridge.v   - Bus 1 passed with inject (scope + handshake)
echo                   - 0x06 freeze / 0x07 release commands
echo                   - 0x10 response includes handshake echo byte
echo   top_icebreaker.v - freeze wired from bridge to array
echo   fpga_bridge.py  - inject() sends bus1 word with handshake/scope
echo                   - freeze() / release() methods added
echo                   - build_bus1() helper matches command_interface.py
echo.

:: Safety check
if not exist fpga\verilog\unicell.v (
    echo ERROR: Cannot find fpga\verilog\unicell.v
    echo        Run this script from inside your Imago-Unicell repo directory
    echo        and make sure you copied the .v files into fpga\verilog\
    pause
    exit /b 1
)

:: Copy updated files into place
echo Copying files...
copy /Y unicell.v          fpga\verilog\unicell.v
copy /Y unicell_array.v    fpga\verilog\unicell_array.v
copy /Y uart_bridge.v      fpga\verilog\uart_bridge.v
copy /Y top_icebreaker.v   fpga\verilog\top_icebreaker.v
copy /Y fpga_bridge.py     fpga\fpga_bridge.py
echo   Done.
echo.

:: Stage and commit
echo Staging files for git...
git add fpga\verilog\unicell.v
git add fpga\verilog\unicell_array.v
git add fpga\verilog\uart_bridge.v
git add fpga\verilog\top_icebreaker.v
git add fpga\fpga_bridge.py

echo Committing...
git commit -m "Claudette v1.2 - FPGA Verilog and bridge update

- unicell.v: CONFIG_ADDRESS separates fixed config address from
  runtime input_address. GS_FALL_EDGE on negedge clk. freeze active.
- unicell_array.v: CONFIG_ADDRESS, clk_n, freeze per cell.
  NUM_CELLS default 32 for safe iCEBreaker bring-up.
- uart_bridge.v: Bus 1 word in inject command (scope+handshake+auth).
  freeze(0x06) and release(0x07) commands. RSP_FIRED includes
  handshake echo byte. array_freeze output wired to array.
- top_icebreaker.v: freeze wired from bridge to array.
- fpga_bridge.py: inject() sends bus1 with handshake/scope.
  freeze() and release() methods. build_bus1() helper."

echo.
echo Git commit done.
echo.

echo ================================================
echo  FPGA v1.2 applied.
echo.
echo  To synthesise for iCEBreaker:
echo    cd fpga\verilog
echo    yosys -p "synth_ice40 -top top -json top.json" top_icebreaker.v unicell_array.v unicell.v uart_bridge.v
echo    nextpnr-ice40 --up5k --package sg48 --json top.json --pcf icebreaker.pcf --asc top.asc
echo    icepack top.asc top.bin
echo    iceprog top.bin
echo ================================================
echo.
pause
