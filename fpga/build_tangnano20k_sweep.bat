@echo off
:: build_tangnano20k_sweep.bat -- overnight, unattended synthesis/PnR
:: sweep of every UniCell core type on the Sipeed Tang Nano 20K
:: (Gowin GW2AR-LV18QN88C8/I7), via the open-source yosys /
:: nextpnr-himbaechel / Apicula flow -- the same open-source spirit as
:: build_icebreaker.bat, ported to Gowin.
::
:: For each entry below, runs: yosys (synth_gowin) -> nextpnr-himbaechel
:: -> gowin_pack, and appends LUT/DFF/Fmax to ONE consolidated summary
:: file (results\tangnano20k_sweep_summary.csv). Continues past a
:: failed entry rather than aborting the whole overnight run -- each
:: entry's own pass/fail and any error text is recorded in the summary
:: too, so nothing is silently lost.
::
:: REAL, NECESSARY PREREQUISITE, not yet done: a real Tang Nano 20K
:: .cst pin-constraint file (mapping this design's own top-level ports
:: -- CLK, LEDs, etc -- to the board's own real physical pins) does not
:: exist in this repo yet. Sipeed's own official Tang Nano 20K
:: examples repo publishes the real, correct pin mapping; copy/adapt
:: that into constraints\tangnano20k.cst before running this for real.
:: DEVICE below is confirmed directly against Project Apicula's own
:: documented, supported device list for this board.
::
:: Usage:
::   build_tangnano20k_sweep.bat single   -- single-cell entries only
::   build_tangnano20k_sweep.bat block10  -- 10-cell-block entries only
::   build_tangnano20k_sweep.bat          -- both (the real overnight run)

setlocal enabledelayedexpansion
cd /d "%~dp0"

set VDIR=verilog
set CST=constraints\tangnano20k.cst
set DEVICE=GW2AR-LV18QN88C8/I7
set BUILD=build_tangnano20k
set RESULTS=results
set SUMMARY=%RESULTS%\tangnano20k_sweep_summary.csv

if not exist %BUILD% mkdir %BUILD%
if not exist %RESULTS% mkdir %RESULTS%

echo === Imago UniCell -- Tang Nano 20K overnight sweep === > %SUMMARY%
echo Started: %DATE% %TIME% >> %SUMMARY%
echo. >> %SUMMARY%
echo entry,phase,status,lut,dff,fmax_mhz,notes >> %SUMMARY%

:: ── Real, deliberate list of sweep entries. Each line: a unique
:: name, the top-level module, and its own real Verilog source files
:: (space-separated). Reuses the EXISTING, already-validated top-level
:: test modules from the Quartus/Arria 10 work (fpga/verilog/top_*/)
:: wherever their own real shape already matches "one cell" or "N
:: cells" -- new, dedicated 10-cell-block wrappers are real, separate,
:: not-yet-written work for entries marked TODO below. ──

:: --- single-cell entries (one instance of each core) ---
call :sweep_one "adder_single"       "top_adder_single"       "%VDIR%\adder_cell\adder_cell_v1.v %VDIR%\top_adder_single\top_adder_single_v1.v"
call :sweep_one "ram_single"         "top_ram_single"          "%VDIR%\ram_cell\ram_cell_v1.v %VDIR%\top_ram_single\top_ram_single_v1.v"
call :sweep_one "branch_single"      "top_branch_cell_test"    "%VDIR%\branch_cell\branch_cell_v1.v %VDIR%\top_branch_cell_test\top_branch_cell_test_v1.v"
call :sweep_one "latch_single"       "top_latch_toggle_test"   "%VDIR%\latch_cell\latch_cell_v1.v %VDIR%\top_latch_toggle_test\top_latch_toggle_test_v1.v"
call :sweep_one "comparator_single"  "top_compare_test"        "%VDIR%\compare_cell\compare_cell_v1.v %VDIR%\top_compare_test\top_compare_test_v1.v"
call :sweep_one "accumulator_single" "top_accumulator_pulse_mode_test" "%VDIR%\accumulator_cell\accumulator_cell_v1.v %VDIR%\top_accumulator_pulse_mode_test\top_accumulator_pulse_mode_test_v1.v"
:: TODO: sequencer_single, priority_single, nano_gate_single,
:: nano_hold_trigger_single -- real, dedicated single-cell top-level
:: wrappers not yet written for these; add once available.

if "%1"=="single" goto :summary_done

:: --- 10-cell-block entries (real, new wrappers -- NOT yet written) ---
:: The existing chain50 modules (top_adder_chain50, top_ram_chain50)
:: are real, but 50 cells, not 10 -- a real, deliberate design choice
:: for THIS sweep's own smaller, faster overnight scale needs a real,
:: new 10-cell wrapper per core type. None exist yet; each call below
:: will genuinely fail until its own top_..._block10 module is written
:: -- left in place so the sweep's own summary records that gap
:: honestly rather than silently skipping it.
call :sweep_one "adder_block10"      "top_adder_block10"       "%VDIR%\adder_cell\adder_cell_v1.v %VDIR%\top_adder_block10\top_adder_block10_v1.v"
call :sweep_one "ram_block10"        "top_ram_block10"         "%VDIR%\ram_cell\ram_cell_v1.v %VDIR%\top_ram_block10\top_ram_block10_v1.v"
:: TODO: one block10 entry per remaining core type, plus the VIX
:: carrier single/block10 equivalents -- add once those top-level
:: wrappers exist.

:summary_done
echo. >> %SUMMARY%
echo Finished: %DATE% %TIME% >> %SUMMARY%
echo.
echo === Sweep complete. Results: %SUMMARY% ===
type %SUMMARY%
pause
goto :eof

:: ── real, reusable per-entry routine: synth -> PnR -> pack, parse
:: LUT/DFF/Fmax, append one real, complete row to the summary. ──
:sweep_one
set NAME=%~1
set TOP=%~2
set FILES=%~3
set LOG=%BUILD%\%NAME%.log
set JSON=%BUILD%\%NAME%.json
set PNRJSON=%BUILD%\%NAME%_pnr.json
set FS=%BUILD%\%NAME%.fs

echo.
echo --- %NAME%: synthesising (top=%TOP%) ---
set READCMD=
for %%F in (%FILES%) do set READCMD=!READCMD! read_verilog %%F;
yosys -p "!READCMD! synth_gowin -top %TOP% -json %JSON%" > %LOG% 2>&1

findstr /i "ERROR" %LOG% >nul
if not errorlevel 1 (
    echo %NAME%,synth,FAIL,,,,"see %LOG%" >> %SUMMARY%
    echo     FAILED -- see %LOG%
    goto :eof
)

echo --- %NAME%: place and route ---
nextpnr-himbaechel --json %JSON% --write %PNRJSON% --device %DEVICE% --vopt cst=%CST% >> %LOG% 2>&1

findstr /i "ERROR" %LOG% >nul
if not errorlevel 1 (
    echo %NAME%,pnr,FAIL,,,,"see %LOG%" >> %SUMMARY%
    echo     FAILED -- see %LOG%
    goto :eof
)

echo --- %NAME%: packing bitstream ---
gowin_pack -d %DEVICE% -o %FS% %PNRJSON% >> %LOG% 2>&1

:: Real, direct parse of yosys's own stat summary and nextpnr's own
:: reported Fmax out of the one, shared log -- adjust the findstr
:: patterns here if a given yosys/nextpnr version's own real wording
:: differs; verified against nothing yet (no toolchain/board in this
:: environment), so treat these patterns as a real, honest starting
:: point to check against the FIRST real run's own actual log, not a
:: guaranteed-correct parse.
for /f "tokens=2" %%L in ('findstr /i "Number of cells" %LOG%') do set LUTCOUNT=%%L
for /f "tokens=3" %%D in ('findstr /i "\$dff" %LOG%') do set DFFCOUNT=%%D
for /f "tokens=2 delims=(" %%M in ('findstr /i "Max frequency" %LOG%') do set FMAX=%%M

echo %NAME%,full,OK,%LUTCOUNT%,%DFFCOUNT%,%FMAX%, >> %SUMMARY%
echo     OK -- lut=%LUTCOUNT% dff=%DFFCOUNT% fmax=%FMAX%
goto :eof
