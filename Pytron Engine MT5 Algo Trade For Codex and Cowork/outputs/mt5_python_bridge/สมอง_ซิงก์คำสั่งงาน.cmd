REM Python Qaunt Trading + AI(LLM) Live Research
REM ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
REM ซิงก์คำสั่งงานบอทจาก cron ให้สมองตัวอื่นเห็นคำสั่งเดียวกัน
@echo off
setlocal
set PYTHONUTF8=1
"%~dp0..\..\.venv\Scripts\python.exe" "%~dp0..\..\agents\sync_briefs.py"
echo.
pause
