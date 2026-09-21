@echo off
REM Python Qaunt Trading + AI(LLM) Live Research
REM อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
REM เทรดในไทยมีกฎหมายรองรับ 100%
REM Settrade e-Open Account · MTS Gold Futures + MT5
REM https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
REM ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
REM โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
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
