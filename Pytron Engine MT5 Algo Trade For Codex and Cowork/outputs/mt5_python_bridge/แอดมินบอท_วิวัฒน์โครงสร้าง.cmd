@echo off
REM Python Qaunt Trading + AI(LLM) Live Research — ผู้สร้างระบบ: Kanutsanan Pongpanna
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0..\.."
echo === รอบแอดมิน: วิวัฒน์ทั้งค่าและโครงสร้าง (ตรวจก่อน) ===
.venv\Scripts\python.exe outputs\mt5_python_bridge\tools\admin_bot_round.py --allow-structure
echo.
echo กด Enter เพื่อปรับจริง (หรือปิดหน้าต่างเพื่อยกเลิก)
pause >nul
.venv\Scripts\python.exe outputs\mt5_python_bridge\tools\admin_bot_round.py --apply --allow-structure
pause
