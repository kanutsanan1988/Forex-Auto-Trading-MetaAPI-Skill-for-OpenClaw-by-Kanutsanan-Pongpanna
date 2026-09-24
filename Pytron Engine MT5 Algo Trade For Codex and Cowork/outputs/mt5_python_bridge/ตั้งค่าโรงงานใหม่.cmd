@echo off
REM Python Qaunt Trading + AI(LLM) Live Research — ผู้สร้างระบบ: Kanutsanan Pongpanna
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0..\.."
echo === ตั้งค่าโรงงานใหม่ = สถานะระบบปัจจุบัน (ค่าตั้ง + โค้ด + งาน cron) ===
.venv\Scripts\python.exe work\factory\set_factory.py
echo.
echo เสร็จแล้ว — ค่าโรงงานอัปเดตเป็นสถานะปัจจุบัน
pause
