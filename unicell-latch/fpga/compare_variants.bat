@echo off
:: compare_variants.bat — Windows version of compare_variants.sh
:: Builds both latch variants and compares LUT usage
:: Requires: yosys, nextpnr-ice40, icepack, iceprog in PATH

setlocal
cd /d "%~dp0"

set VDIR=verilog
set PCF=constraints\icebreaker.pcf
set BUILD=build

if not exist %BUILD% mkdir %BUILD%

echo ================================================
echo  Imago UniCell -- Variant Comparison
echo  latch (32-bit) vs split (16-bit 2x clock)
echo ================================================
echo.

echo --- Building unicell_latch (standard 32-bit tree)...
yosys -p "read_verilog %VDIR%/unicell_latch.v; read_verilog %VDIR%/unicell_array_latch.v; read_verilog %VDIR%/uart_bridge.v; read_verilog %VDIR%/top_icebreaker.v; synth_ice40 -top top -json %BUILD%/latch.json" 2>&1 | findstr /i "LUT DFF CARRY cells"

echo.
nextpnr-ice40 --up5k --package sg48 --pcf %PCF% --json %BUILD%/latch.json --asc %BUILD%/latch.asc --freq 24 2>&1 | findstr /i "ICESTORM_LC frequency Warning"

icepack %BUILD%\latch.asc %BUILD%\latch.bin
echo latch.bin built.

echo.
echo --- Building unicell_latch_split (16-bit tree, 2x clock)...
yosys -p "read_verilog %VDIR%/unicell_latch_split.v; read_verilog %VDIR%/unicell_array_split.v; read_verilog %VDIR%/uart_bridge.v; read_verilog %VDIR%/top_icebreaker_split.v; synth_ice40 -top top -json %BUILD%/split.json" 2>&1 | findstr /i "LUT DFF CARRY cells"

echo.
nextpnr-ice40 --up5k --package sg48 --pcf %PCF% --json %BUILD%/split.json --asc %BUILD%/split.asc --freq 24 2>&1 | findstr /i "ICESTORM_LC frequency Warning"

icepack %BUILD%\split.asc %BUILD%\split.bin
echo split.bin built.

echo.
echo ================================================
echo  Results
echo ================================================
echo.
echo  Check ICESTORM_LC counts above.
echo  Lower count = fewer LUTs = more cells on iCEBreaker.
echo.
echo  Flash latch:  iceprog %BUILD%\latch.bin
echo  Flash split:  iceprog %BUILD%\split.bin
echo ================================================
pause
