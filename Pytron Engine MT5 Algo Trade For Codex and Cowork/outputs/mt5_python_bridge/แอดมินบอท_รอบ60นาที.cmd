@echo off
REM Python Qaunt Trading + AI(LLM) Live Research — ผู้สร้างระบบ: Kanutsanan Pongpanna
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0..\.."
.venv\Scripts\python.exe outputs\mt5_python_bridge\tools\admin_bot_round.py --interval 60
pause
