REM Python Qaunt Trading + AI(LLM) Live Research
REM ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
REM ดูสมอง (agentic AI) ที่ระบบรองรับ + ตัวที่ติดตั้งในเครื่องนี้
@echo off
setlocal
set PYTHONUTF8=1
"%~dp0..\..\.venv\Scripts\python.exe" "%~dp0..\..\agents\run_bot.py" --list %*
echo.
pause
