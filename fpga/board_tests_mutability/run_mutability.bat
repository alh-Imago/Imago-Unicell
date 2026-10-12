@echo off
:: run_mutability.bat -- ledger #1086 (Windows). Test 1 of the mutability proof on the Tang Nano 20K.
::   run_mutability.bat host COM7     load mutability1h.fs, then run mutability_host.py (needs: pip install pyserial)
::   run_mutability.bat self COM7     load mutability1.fs, which runs the seven phases by itself; read its line with any serial terminal at 115200
:: Needs openFPGALoader on this PC. The bitstream goes to SRAM only; the flash is not touched.
cd /d "%~dp0"
set MODE=%1
set PORT=%2
if "%MODE%"=="self" ( openFPGALoader -b tangnano20k mutability1.fs & echo Now open %PORT% at 115200 baud and read the line. & goto :eof )
openFPGALoader -b tangnano20k mutability1h.fs
timeout /t 4 /nobreak >nul
python mutability_host.py %PORT%
pause
