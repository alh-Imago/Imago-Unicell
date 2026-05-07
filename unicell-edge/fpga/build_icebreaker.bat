@echo off
:: build_icebreaker.bat -- Build and flash unicell-edge for iCEBreaker
:: Claudette v2.1 / unicell-edge variant
:: A on posedge, B on negedge -- full 12-function NOR tree
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

echo === Imago UniCell Edge -- iCEBreaker build ===
echo Clock: 24MHz SB_HFOSC (validated)
echo Cells: 8
echo.

echo --- Synthesising...
yosys -p "read_verilog %VDIR%/unicell.v; read_verilog %VDIR%/unicell_array.v; read_verilog %VDIR%/uart_bridge.v; read_verilog %VDIR%/top_icebreaker.v; synth_ice40 -top top -json %BUILD%/edge.json" 2>&1 | findstr /i "LUT DFF CARRY Warning Error cells ICESTORM"

echo.
echo --- Place and route...
nextpnr-ice40 --up5k --package sg48 --pcf %PCF% --json %BUILD%/edge.json --asc %BUILD%/edge.asc --freq 24 2>&1 | findstr /i "ICESTORM_LC frequency Warning Error"

echo.
echo --- Packing bitstream...
icepack %BUILD%\edge.asc %BUILD%\edge.bin

echo.
echo === Build complete: %BUILD%\edge.bin ===

if "%1"=="flash" (
    echo.
    echo --- Flashing edge variant to iCEBreaker...
    iceprog %BUILD%\edge.bin
    echo === Flashed ===
)
pause
