@echo off
:: run_all.bat -- ledger #1023: load each self-checking test bitstream onto the Tang Nano 20K, read its result line from the
:: board's USB serial port, and gather everything into ONE file: board_results.txt (also board_results.csv).
::
:: Needs: openFPGALoader and Python with pyserial (pip install pyserial) on this PC; the board plugged in by USB-C.
:: Usage:  run_all.bat            (auto-detects the serial port)
::         run_all.bat COM7      (name the serial port yourself: the board's second COM port is usually the FPGA UART)
:: Each bitstream goes to SRAM (lost at power-off, the flash is NOT touched).
setlocal enabledelayedexpansion
cd /d "%~dp0"
set PORT=%1
python board_run.py %PORT%
echo.
echo Finished. Results are in %~dp0board_results.txt
pause
