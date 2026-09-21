REM Python Qaunt Trading + AI(LLM) Live Research
REM อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
REM เทรดในไทยมีกฎหมายรองรับ 100%
REM Settrade e-Open Account · MTS Gold Futures + MT5
REM https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
REM ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
REM โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
REM เลือกสมอง (agentic AI) แล้วสั่งให้ทำงานรอบวิจัย/แอดมินบอท
@echo off
setlocal
set PYTHONUTF8=1
set PY=%~dp0..\..\.venv\Scripts\python.exe
set RB=%~dp0..\..\agents\run_bot.py
echo === เลือกรอบงาน ===
echo   1^) วิจัยโหมด 2   (บอทสมอง LLM)
echo   2^) แอดมินบอท     (วิวัฒน์ค่าต่างๆ + วิจัยข่าว + สั่งคำสั่ง)
set /p R="เลือก 1 หรือ 2: "
if "%R%"=="1" set ROLE=mode2
if "%R%"=="2" set ROLE=admin
if not defined ROLE (echo ไม่ได้เลือก - ยกเลิก & pause & exit /b 1)
echo.
"%PY%" "%RB%" --list
echo.
set /p BRAIN="พิมพ์ id ของสมอง (เว้นว่าง = ตัวเริ่มต้นที่ติดตั้ง): "
if "%BRAIN%"=="" (
  "%PY%" "%RB%" --role %ROLE%
) else (
  "%PY%" "%RB%" --role %ROLE% --brain %BRAIN%
)
echo.
pause
