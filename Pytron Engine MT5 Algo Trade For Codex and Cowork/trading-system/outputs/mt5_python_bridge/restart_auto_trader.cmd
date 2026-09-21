REM Python Qaunt Trading + AI(LLM) Live Research
REM อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
REM เทรดในไทยมีกฎหมายรองรับ 100%
REM Settrade e-Open Account · MTS Gold Futures + MT5
REM https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
REM ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
REM ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
REM ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
REM   Facebook: https://www.facebook.com/LoveMoneyTH
REM   YouTube:  https://youtube.com/@lovemoneythofficial
REM โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
@echo off
setlocal
pushd "%~dp0"
echo Stopping MT5 auto trader...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_auto_trader.ps1"
if errorlevel 1 goto :error
echo Clearing kill switch...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0clear_kill_switch.ps1"
if errorlevel 1 goto :error
echo Starting MT5 auto trader...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_auto_trader.ps1"
if errorlevel 1 goto :error
echo.
echo Auto trader restarted successfully.
pause
popd
exit /b 0
:error
echo.
echo Auto trader restart failed. Review the message above.
pause
popd
exit /b 1
