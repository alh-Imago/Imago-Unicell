@echo off
:: build_split.bat -- Build and flash unicell_latch_split for iCEBreaker
:: 16-bit NOR tree, 2x internal clock (48MHz), external 24MHz unchanged
::
:: Usage:
::   build_split.bat        -- build only
::   build_split.bat flash  -- build and flash

setlocal
cd /d "%~dp0"

set VDIR=verilog
set PCF=constraints\icebreaker.pcf
set BUILD=build

if not exist %BUILD% mkdir %BUILD%

echo === Imago UniCell Latch-Split -- iCEBreaker build ===
echo Clock: 24MHz external / 48MHz internal tree
echo Cells: 8
echo.

echo --- Synthesising...
yosys -p "read_verilog %VDIR%/unicell_latch_split.v; read_verilog %VDIR%/unicell_array_split.v; read_verilog %VDIR%/uart_bridge.v; read_verilog %VDIR%/top_icebreaker_split.v; synth_ice40 -top top -json %BUILD%/split.json" 2>&1 | findstr /i "LUT DFF CARRY Warning Error cells ICESTORM"

echo.
echo --- Place and route...
nextpnr-ice40 --up5k --package sg48 --pcf %PCF% --json %BUILD%/split.json --asc %BUILD%/split.asc --freq 24 2>&1 | findstr /i "ICESTORM_LC frequency Warning Error"

echo.
echo --- Packing bitstream...
icepack %BUILD%\split.asc %BUILD%\split.bin

echo.
echo === Build complete: %BUILD%\split.bin ===

if "%1"=="flash" (
    echo.
    echo --- Flashing split variant to iCEBreaker...
    iceprog %BUILD%\split.bin
    echo === Flashed ===
)
pause
