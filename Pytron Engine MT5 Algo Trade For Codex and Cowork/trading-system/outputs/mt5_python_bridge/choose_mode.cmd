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
REM ============================================================
REM  choose_mode.cmd — เลือก "โหมดการเทรด" (ดับเบิลคลิกได้เลย)
REM   โหมด 1 = เทรดด้วยสัญญาณภายใน (ไม่ใช้สัญญาณ LLM ของรอบ 10 นาที)
REM   โหมด 2 = เทรดร่วมสัญญาณ AI (LLM) — ค่าเริ่มต้น
REM  แก้แค่: work/trading_mode.json + เปิด/ปิด cron 2 งาน (ไม่แตะเทรดเดอร์)
REM ============================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
REM Hermes: ใช้ค่าจาก environment ก่อน; ถ้าไม่มีให้ค้นจาก PATH และที่ติดตั้งทั่วไป
REM (เดิมโค้ดนี้ชี้ path ตายตัวของผู้สร้าง ทำให้เครื่องอื่นใช้ไม่ได้)
if not defined HERMES_EXE for /f "delims=" %%H in ('where hermes 2^>nul') do if not defined HERMES_EXE set HERMES_EXE=%%H
if not defined HERMES_EXE if exist "%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\hermes.exe" set HERMES_EXE=%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\hermes.exe
if not defined HERMES_EXE if exist "%USERPROFILE%\hermes-agent\venv\Scripts\hermes.exe" set HERMES_EXE=%USERPROFILE%\hermes-agent\venv\Scripts\hermes.exe
if not defined HERMES_EXE set HERMES_EXE=hermes

set PY=%~dp0..\..\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python

"%PY%" "%~dp0choose_mode.py" %*
echo.
pause
endlocal
