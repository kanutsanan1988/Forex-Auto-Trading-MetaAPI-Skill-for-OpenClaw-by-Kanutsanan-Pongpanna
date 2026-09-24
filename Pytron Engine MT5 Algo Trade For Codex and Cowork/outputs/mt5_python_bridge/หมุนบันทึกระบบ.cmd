REM Python Qaunt Trading + AI(LLM) Live Research
REM ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
REM หมุน/บีบอัด audit log (เก็บของเก่าเป็น .gz ไม่ลบ) — ต้องปิดระบบก่อน
@echo off
setlocal
set PYTHONUTF8=1
"%~dp0..\..\.venv\Scripts\python.exe" "%~dp0tools\rotate_audit.py" %*
echo.
pause
