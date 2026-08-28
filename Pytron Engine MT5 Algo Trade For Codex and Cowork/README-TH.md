# Kanatsanan MT5 Trading Suite 1.0.0

แพ็กเกจระบบวิเคราะห์และเทรดทองคำบน MetaTrader 5 สำหรับ Windows พัฒนาโดย **คณัสนันท์ พงษ์พันนา**

ระบบเชื่อมกับ MT5 ที่ผู้ใช้เปิดและล็อกอินไว้ในเครื่องของตนเอง ไม่เก็บหรือแจกจ่ายรหัสผ่าน บัญชี API key ประวัติเทรด หรือข้อมูลจากเครื่องผู้พัฒนา

## ความสามารถ

- วิเคราะห์แท่งปิด M1 โดยใช้ M5/M15/H1 ประกอบ
- Strategy Router: Trend, Range, Mean Reversion, Breakout, Counter Trend และ Breakout Reversal
- Adaptive evaluation และ shadow outcomes
- Read-only probe, market analysis, dry run และ backtest
- Risk gate, daily loss gate, consecutive-loss gate, spread limit และ one-position rule
- Supervisor, singleton lock, audit log และ kill switch
- MCP tools สำหรับ Codex และ Claude/Cowork

ผลการวิเคราะห์และ Backtest ไม่รับประกันผลกำไร การเปิด Live Trading สามารถทำให้สูญเสียเงินจริงได้

## ติดตั้งบนเครื่องใหม่

1. ใช้ Windows 10/11 และติดตั้ง MetaTrader 5
2. เปิด MT5 และล็อกอินบัญชีของผู้ใช้เอง
3. แตก ZIP ไปยังโฟลเดอร์ที่ผู้ใช้มีสิทธิ์เขียนไฟล์
4. เปิด PowerShell ในโฟลเดอร์นี้แล้วรัน:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\INSTALL-WINDOWS.ps1
```

ถ้าระบบเลือกชื่อทองผิด ให้ระบุชื่อของโบรกเกอร์:

```powershell
.\INSTALL-WINDOWS.ps1 -Symbol XAUUSDm
```

5. ทดสอบแบบไม่ส่งคำสั่ง:

```powershell
.\TEST-READ-ONLY.ps1
```

Live Trading ปิดอยู่เสมอหลังติดตั้ง

## เปิดหรือปิดเงินจริง

เปิดเงินจริงต้องยืนยันเลขท้ายบัญชี 3 หลัก กำหนดเพดานความเสี่ยง และพิมพ์ข้อความยอมรับความเสี่ยงตรงตัว:

```powershell
.\ENABLE-LIVE-TRADING.ps1 `
  -AccountLast3 123 `
  -MaxRiskPct 1.0 `
  -DailyLossLimitPct 3.0 `
  -Confirmation 'I UNDERSTAND LIVE TRADING CAN LOSE MONEY'
```

คำสั่งนี้ยังไม่เริ่มเทรด จากนั้นให้ผู้ใช้ขอดูสถานะก่อนสั่งเริ่มผ่าน Codex/Cowork

หยุดและปิดเงินจริง:

```powershell
.\DISABLE-LIVE-TRADING.ps1
```

## ใช้กับ Codex

โฟลเดอร์นี้เป็น Codex Plugin ที่มี `.codex-plugin/plugin.json`, Skill และ local MCP server ครบ ผู้รับสามารถส่ง ZIP ให้ Codex ช่วยแตกไฟล์ ติดตั้ง dependency และเพิ่ม Plugin จากโฟลเดอร์ที่แตกแล้วได้ เมื่อเปิด task ใหม่ให้ขอว่า “ตรวจการเชื่อมต่อ MT5 โดยห้ามส่งคำสั่งซื้อขาย”

## ใช้กับ Claude/Cowork

ไฟล์ส่งมอบหลักมีไฟล์ย่อย `mt5-gold-trading-cowork-skill.zip` สำหรับอัปโหลดที่ Customize > Skills และ `kanatsanan-mt5-bridge.mcpb` สำหรับติดตั้ง local connector ใน Claude Desktop ต้องติดตั้งทั้ง Skill และ connector จึงจะได้คำแนะนำและเครื่องมือ MT5 ครบ

## ข้อมูลที่สร้างเฉพาะเครื่อง

หลังเริ่มใช้งาน ระบบจะสร้าง `.venv` และโฟลเดอร์ `trading-system/work` ในเครื่องผู้รับ ห้ามส่งสองโฟลเดอร์นี้ต่อ เพราะอาจมี account binding, state และ audit history ของผู้ใช้นั้น
