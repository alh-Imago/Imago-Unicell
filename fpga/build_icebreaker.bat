@echo off
:: build_icebreaker.bat -- Build and flash standard unicell for iCEBreaker
:: This is the VALIDATED standard model (NOT gate + NAND confirmed 14 May 2026)
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

echo === Imago UniCell Standard -- iCEBreaker build ===
echo Clock: 24MHz SB_HFOSC (validated 14 May 2026)
echo Cells: 8
echo.

echo --- Synthesising...
yosys -p "read_verilog %VDIR%/unicell.v; read_verilog %VDIR%/unicell_array.v; read_verilog %VDIR%/uart_bridge.v; read_verilog %VDIR%/top_icebreaker.v; synth_ice40 -top top -json %BUILD%/icebreaker.json" 2>&1 | findstr /i "LUT DFF CARRY Warning Error cells"

echo.
echo --- Place and route...
nextpnr-ice40 --up5k --package sg48 --pcf %PCF% --json %BUILD%/icebreaker.json --asc %BUILD%/icebreaker.asc --freq 24 2>&1 | findstr /i "ICESTORM_LC frequency Warning Error"

echo.
echo --- Packing bitstream...
icepack %BUILD%\icebreaker.asc %BUILD%\icebreaker.bin

echo.
echo === Build complete: %BUILD%\icebreaker.bin ===

if "%1"=="flash" (
    echo.
    echo --- Flashing standard model to iCEBreaker...
    iceprog %BUILD%\icebreaker.bin
    echo === Flashed ===
)
pause
