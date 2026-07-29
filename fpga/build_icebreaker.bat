@echo off
:: build_icebreaker.bat -- Build and flash unicell64_v3 for iCEBreaker
:: PORTED 2026-07-29 to the v3 cell (unicell64_v3.v) -- same module the
:: Arria 10 build uses. Old validated v2.3 result (NOT gate + NAND, 14 May
:: 2026) used the retired unicell.v/unicell_array.v; see git history for
:: that version if ever needed for comparison.
::
:: Usage:
::   build_icebreaker.bat        -- build only
::   build_icebreaker.bat flash  -- build and flash

setlocal
cd /d "%~dp0"

set VDIR=verilog
set PCF=constraints\icebreaker.pcf
set BUILD=build

if not exist %BUILD% mkdir %BUILD%

echo === Imago UniCell v3 -- iCEBreaker build ===
echo Clock: 12MHz SB_HFOSC (CLKHF_DIV=0b10, reduced from 24MHz for v3 timing margin)
echo Cells: 2 (confirmed empirically 2026-07-29 -- the v3 cell is bigger than
echo         the old cell this board was sized for; 4 does NOT fit, 2 does,
echo         80%% LC utilization with real margin)
echo.

echo --- Synthesising...
yosys -p "read_verilog %VDIR%/unicell64_v3.v; read_verilog %VDIR%/uart_bridge.v; read_verilog %VDIR%/top_icebreaker.v; synth_ice40 -top top -json %BUILD%/icebreaker.json" 2>&1 | findstr /i "LUT DFF CARRY Warning Error cells"

echo.
echo --- Place and route...
nextpnr-ice40 --up5k --package sg48 --pcf %PCF% --json %BUILD%/icebreaker.json --asc %BUILD%/icebreaker.asc --freq 12 2>&1 | findstr /i "ICESTORM_LC frequency Warning Error"

echo.
echo --- Packing bitstream...
icepack %BUILD%\icebreaker.asc %BUILD%\icebreaker.bin

echo.
echo === Build complete: %BUILD%\icebreaker.bin ===

if "%1"=="flash" (
    echo.
    echo --- Flashing v3 model to iCEBreaker...
    iceprog %BUILD%\icebreaker.bin
    echo === Flashed ===
)
pause
