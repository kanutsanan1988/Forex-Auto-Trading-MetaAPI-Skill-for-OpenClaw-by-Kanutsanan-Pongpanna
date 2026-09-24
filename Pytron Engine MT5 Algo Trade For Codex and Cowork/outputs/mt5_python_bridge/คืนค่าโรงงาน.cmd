@echo off
REM Python Qaunt Trading + AI(LLM) Live Research — ผู้สร้างระบบ: Kanutsanan Pongpanna
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0..\.."
echo === คืนค่าโรงงาน (ตรวจก่อน) ===
.venv\Scripts\python.exe work\factory\restore_factory.py
echo.
echo กด Enter เพื่อคืนค่าจริง (หรือปิดหน้าต่างเพื่อยกเลิก)
pause >nul
.venv\Scripts\python.exe work\factory\restore_factory.py --apply
pause
