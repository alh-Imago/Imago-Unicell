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
echo  Claudette v1.2 - FPGA Verilog Update
echo ================================================
echo.
echo Changes:
echo   unicell.v       - CONFIG_ADDRESS parameter (fixed config address,
echo                     separate from runtime input_address)
echo                   - GS_FALL_EDGE (bit 24) implemented on negedge clk
echo                   - freeze line connected and active
echo                   - clk_n input for falling edge path
echo   unicell_array.v - Passes CONFIG_ADDRESS=c to each cell
echo                   - Passes clk_n, freeze to each cell
echo                   - Default NUM_CELLS reduced to 32 (safe bring-up)
echo   top_icebreaker.v - freeze tied low for bring-up (safe default)
echo                    - Version bumped to v1.2
echo.

:: Safety check
if not exist fpga\verilog\unicell.v (
    echo ERROR: Cannot find fpga\verilog\unicell.v
    echo        Run this script from inside your Imago-Unicell repo directory
    echo        and make sure you copied the .v files into fpga\verilog\
    pause
    exit /b 1
)

:: Copy updated Verilog files into place
echo Copying Verilog files...
copy /Y unicell.v          fpga\verilog\unicell.v
copy /Y unicell_array.v    fpga\verilog\unicell_array.v
copy /Y top_icebreaker.v   fpga\verilog\top_icebreaker.v
echo   Done.
echo.

:: Stage and commit
echo Staging files for git...
git add fpga\verilog\unicell.v
git add fpga\verilog\unicell_array.v
git add fpga\verilog\top_icebreaker.v

echo Committing...
git commit -m "Claudette v1.2 - FPGA Verilog update

- unicell.v: CONFIG_ADDRESS synthesis parameter separates fixed config
  address from runtime input_address register. Prevents address-zero
  collisions on reset. No cell can accidentally intercept another's
  config sequence.
- unicell.v: GS_FALL_EDGE (bit 24) implemented on negedge clk path.
  Falling edge cells stage result at posedge, assert at negedge.
  Separates simultaneous bus writes without pad cells.
- unicell.v: freeze line active - cell fully decouples when asserted.
- unicell.v: clk_n input for falling edge path.
- unicell_array.v: passes CONFIG_ADDRESS=c, clk_n, freeze per cell.
  Default NUM_CELLS reduced to 32 for safe iCEBreaker bring-up.
- top_icebreaker.v: freeze tied low for bring-up, version v1.2."

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
