# Kanatsanan MT5 Trading Suite

ระบบวิเคราะห์และเทรดทองคำบน MetaTrader 5 สำหรับ Windows พัฒนาโดย **คณัสนันท์ พงษ์พันนา**

แพ็กเกจนี้ออกแบบให้ผู้ใช้แต่ละคนเชื่อมต่อกับ MT5 ของตนเองบนเครื่องของตนเอง โดยไม่ส่งต่อรหัสผ่าน เลขบัญชี API key หรือข้อมูลการเทรดของผู้พัฒนา

> คำเตือน: การเทรดมีความเสี่ยงต่อการสูญเสียเงินจริง ระบบนี้ไม่รับประกันกำไร ผลวิเคราะห์และผล Backtest ไม่ใช่คำแนะนำการลงทุน

## 1. ภาพรวมระบบ

ระบบแบ่งเป็น 4 ชั้น:

1. **Trading Core** — คำนวณอินดิเคเตอร์ Regime กลยุทธ์ และแผน Entry/SL/TP
2. **Risk & Execution Guard** — ตรวจ Spread, Volume, ความเสี่ยง, Daily Loss, จำนวน Position, `order_check` และสิทธิ์การเทรด
3. **Auto Trader & Supervisor** — ตรวจแท่งใหม่เป็นรอบ ๆ จัดการ Position และทำงานต่อเมื่อการเชื่อมต่อหลุด
4. **AI Client Integration** — MCP tools, Codex Plugin และ Cowork Skill สำหรับให้ Codex/Cowork เรียกใช้ระบบบนเครื่องของผู้ใช้

ระบบใช้แท่งที่ปิดแล้วในการวิเคราะห์ ไม่ใช้แท่งที่ยังสร้างไม่เสร็จเป็นสัญญาณหลัก

## 2. ความสามารถของกลยุทธ์

### Timeframe และข้อมูลตลาด

- M1 ใช้เป็น Trigger หลัก
- M5, M15 และ H1 ใช้กำหนด Regime และยืนยันแนวโน้ม
- วิเคราะห์ Tick ล่าสุด, Spread, Volume และข้อมูล OHLC ที่ปิดแล้ว

### Strategy Router

Router คำนวณคะแนน Buy/Sell ของ Agent แต่ละตัว แล้วจัดลำดับตามคะแนนและความน่าจะเป็น:

- Trend
- Range
- Mean Reversion
- Breakout
- Counter Trend
- Breakout Reversal

Agent ที่ผ่านเกณฑ์จะเสนอทิศทาง, Confidence, ระยะ Stop และ Reward/Risk ให้ Risk Gate ตรวจต่อ ระบบไม่ได้ส่งคำสั่งเพียงเพราะมีสัญญาณ แต่ต้องผ่านการตรวจสอบทุกชั้น

### Adaptive และ Shadow Evaluation

- เก็บผลลัพธ์ของกลยุทธ์แยกตาม Agent
- ใช้ Rolling Outcomes และ Hysteresis ปรับการเปิดใช้กลยุทธ์อย่างระมัดระวัง
- มี Shadow Cycle สำหรับประเมินสัญญาณโดยไม่ส่งคำสั่งจริง
- ผูก State กับบัญชีและ Server ที่ตรวจพบ เพื่อป้องกันการนำ State ข้ามบัญชีโดยไม่ตั้งใจ

### Risk Control

- จำกัดความเสี่ยงต่อออเดอร์
- จำกัดขาดทุนรายวัน
- จำกัดจำนวนแพ้ติดต่อกัน
- จำกัด Spread สูงสุด
- ตรวจ Volume ขั้นต่ำ/ขั้นสูง/Step ของโบรกเกอร์
- ไม่เปิด Position ซ้อนใน Symbol เดียวกัน
- ใช้ Broker-side Stop Loss และ Take Profit
- ตรวจ `order_check` ก่อน `order_send`
- มี Kill Switch และ Singleton Lock
- บันทึก Audit เฉพาะเครื่องผู้ใช้

## 3. MCP Tools ที่มีให้ Codex/Cowork

เมื่อ Local MCP server เชื่อมต่อสำเร็จ จะมีเครื่องมือดังนี้:

| Tool | หน้าที่ | ส่งคำสั่งซื้อขายหรือไม่ |
|---|---|---|
| `mt5_setup_status` | ตรวจไฟล์ติดตั้งและ Dependency | ไม่ส่ง |
| `mt5_probe` | อ่าน Terminal, Account แบบ Mask, Symbol, Tick และแท่งล่าสุด | ไม่ส่ง |
| `mt5_analyze` | วิเคราะห์ตลาดด้วย Strategy Router | ไม่ส่ง |
| `mt5_dry_run` | จำลองหนึ่งรอบของ Auto Trader | ไม่ส่ง |
| `mt5_backtest` | Backtest จากประวัติแท่งปิด | ไม่ส่ง |
| `mt5_trader_status` | ดู Live Mode, Kill Switch, Process และ Supervisor | ไม่ส่ง |
| `mt5_enable_live_mode` | เปิด Live Mode หลังยืนยันบัญชีและความเสี่ยง | ไม่เริ่ม Process |
| `mt5_disable_live_mode` | หยุด Process และปิด Live Mode | หยุดระบบ |
| `mt5_start_auto_trader` | เริ่ม Supervisor ของระบบ | อาจส่งคำสั่งจริง |
| `mt5_stop_auto_trader` | สร้าง Kill Switch และหยุดระบบ | หยุดระบบ |

## 4. สิ่งที่ต้องมีในเครื่องผู้ใช้

- Windows 10 หรือ Windows 11
- MetaTrader 5
- บัญชีของผู้ใช้เองที่ล็อกอินอยู่ใน MT5
- เปิด MT5 ค้างไว้ขณะทดสอบหรือใช้งาน
- Python 3.11 ขึ้นไปสำหรับติดตั้งครั้งแรก
- Internet สำหรับดาวน์โหลด `MetaTrader5` Python package

ไม่ต้องกรอกหรือส่งรหัสผ่าน MT5 ให้ Codex, Cowork หรือในไฟล์แพ็กเกจ

## 5. วิธีติดตั้ง

แตกไฟล์ ZIP ไปยังโฟลเดอร์ที่ผู้ใช้มีสิทธิ์เขียนไฟล์ เช่น `C:\Trading\KanatsananMT5` จากนั้นเปิด PowerShell ในโฟลเดอร์นั้น

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\INSTALL-WINDOWS.ps1
```

ตัวติดตั้งจะ:

1. สร้าง Python virtual environment ใน `trading-system\.venv`
2. ติดตั้ง Dependency จาก `requirements.txt`
3. ค้นหา MT5 Terminal ที่กำลังทำงานหรืออยู่ในตำแหน่งมาตรฐาน
4. ค้นหา Symbol ที่มีคำว่า `XAU` หรือ `GOLD`
5. บันทึก Symbol ที่เลือกลงใน Configuration
6. บังคับให้ `live_enabled` เป็น `false`
7. ทดสอบข้อมูลบัญชีแบบ Mask และ Symbol

ถ้าระบบเลือก Symbol ไม่ถูกต้อง ให้ระบุเอง:

```powershell
.\INSTALL-WINDOWS.ps1 -Symbol XAUUSDm
```

ถ้าติดตั้ง MT5 ไว้ในตำแหน่งพิเศษ:

```powershell
.\INSTALL-WINDOWS.ps1 `
  -TerminalPath 'D:\Apps\MetaTrader 5\terminal64.exe' `
  -Symbol XAUUSDm
```

## 6. ทดสอบแบบ Read-only

ก่อนเปิดเงินจริงให้รัน:

```powershell
.\TEST-READ-ONLY.ps1
```

คำสั่งนี้จะอ่านข้อมูล MT5 และแสดงผลการวิเคราะห์โดยไม่มี `order_send`

ทดสอบ Logic ภายในระบบโดยไม่เชื่อม MT5:

```powershell
$python = '.\\trading-system\\.venv\\Scripts\\python.exe'
& $python -m unittest discover -s '.\\trading-system\\outputs\\mt5_python_bridge\\tests' -v
```

## 7. การเปิด Live Trading

ค่าเริ่มต้นของแพ็กเกจปิด Live Trading เสมอ การเปิดต้องเป็นการตัดสินใจของผู้ใช้เอง

### เปิดผ่าน PowerShell

```powershell
.\ENABLE-LIVE-TRADING.ps1 `
  -AccountLast3 123 `
  -MaxRiskPct 1.0 `
  -DailyLossLimitPct 3.0 `
  -Confirmation 'I UNDERSTAND LIVE TRADING CAN LOSE MONEY'
```

คำสั่งนี้จะตรวจว่าเลขท้ายบัญชีตรงกับ MT5 ที่เชื่อมอยู่ ตั้งค่า Live Mode และ **ยังไม่เริ่ม Auto Trader**

### เปิดผ่าน MCP

ใช้ `mt5_enable_live_mode` โดยต้องส่ง:

- เลขท้ายบัญชี 3 หลัก
- Maximum Risk ต่อออเดอร์
- Daily Loss Limit
- ข้อความ `I UNDERSTAND LIVE TRADING CAN LOSE MONEY` ตรงตัว

หลังเปิดแล้วให้เรียก `mt5_trader_status` เพื่อตรวจสอบก่อนเริ่มระบบ

## 8. เริ่ม หยุด และปิด Live Mode

เริ่ม Auto Trader จาก PowerShell:

```powershell
.\trading-system\outputs\mt5_python_bridge\start_auto_trader.ps1
```

ดูสถานะ:

```powershell
.\trading-system\outputs\mt5_python_bridge\status_auto_trader.ps1
```

หยุดระบบด้วย Kill Switch:

```powershell
.\trading-system\outputs\mt5_python_bridge\stop_auto_trader.ps1
```

หยุดและปิด Live Mode พร้อมกัน:

```powershell
.\DISABLE-LIVE-TRADING.ps1
```

หาก Kill Switch ยังอยู่ ระบบจะไม่เริ่มใหม่จนกว่าจะมีการตรวจสอบและล้างอย่างตั้งใจ

## 9. ใช้กับ Codex

ใช้ไฟล์ `kanatsanan-mt5-codex-plugin-v1.0.0.zip` หรือแตกไฟล์แล้วให้ Codex ช่วยติดตั้ง Plugin

ข้อความเริ่มต้นที่แนะนำ:

> ตรวจการเชื่อมต่อ MT5 และวิเคราะห์ทองคำแบบ read-only ห้ามเปิด live trading และห้ามส่งคำสั่งซื้อขาย

Codex จะเรียก MCP tools ผ่าน Local MCP server เมื่อ Plugin ถูกติดตั้งและ Dependency พร้อม

## 10. ใช้กับ Claude/Cowork

ใช้ไฟล์สองชิ้นร่วมกัน:

1. `mt5-gold-trading-cowork-skill-v1.0.0.zip` — อัปโหลดที่ Customize > Skills
2. `kanatsanan-mt5-bridge-v1.0.0.mcpb` — ติดตั้งเป็น Local MCP/Extension ใน Claude Desktop

Skill ให้ขั้นตอนและข้อจำกัดการใช้งาน ส่วน MCPB ให้เครื่องมือเชื่อมต่อ MT5 ในเครื่อง

## 11. ไฟล์ Runtime และข้อมูลส่วนตัว

ไฟล์ต่อไปนี้จะถูกสร้างเฉพาะเครื่องผู้ใช้ และไม่ควรนำไปแจกจ่าย:

- `trading-system\.venv` — Python environment
- `trading-system\work\auto_trader_state.json` — State ที่ผูกกับบัญชี
- `trading-system\work\auto_trader_audit.jsonl` — Audit log
- `trading-system\work\*.lock` และ `*.pid` — Process control files
- `trading-system\work\AUTO_TRADER_STOP` — Kill Switch

ห้ามนำ `.env`, API key, account state, audit log หรือไฟล์จากบัญชีหนึ่งไปใช้กับอีกบัญชีหนึ่ง

## 12. การแก้ปัญหาเบื้องต้น

### MT5 initialize ไม่สำเร็จ

- เปิด MT5 ค้างไว้
- ตรวจว่า MT5 ล็อกอินแล้ว
- ตรวจ `terminal64.exe` ด้วย `-TerminalPath`
- ปิด MT5 หลาย Instance ที่ไม่ใช่บัญชีเป้าหมาย

### ไม่พบ Symbol ทอง

ดูชื่อ Symbol ใน Market Watch แล้วติดตั้งใหม่ด้วย `-Symbol` เช่น `XAUUSDm`, `XAUUSD.sml` หรือ `GOLD`

### Volume ไม่ผ่าน

โบรกเกอร์บางรายกำหนด Volume ขั้นต่ำสูงกว่า `0.001` ระบบจะปฏิเสธออเดอร์เมื่อไม่ตรง Minimum หรือ Step เพื่อป้องกันคำสั่งผิดขนาด

### ระบบไม่เริ่มเพราะ Kill Switch

ตรวจสถานะและ Audit ก่อน จากนั้นล้าง Kill Switch ด้วย `clear_kill_switch.ps1` เฉพาะเมื่อแน่ใจว่าปลอดภัย

### บัญชีเปลี่ยนแล้วระบบปฏิเสธ State

เป็นกลไกป้องกันการนำ State ข้ามบัญชี ห้ามลบ State ทันที ให้สำรองและตรวจสอบบัญชี/Server ก่อน

## 13. ขอบเขตและความรับผิดชอบ

ผู้ใช้เป็นผู้รับผิดชอบการตรวจสอบ Broker, Symbol, Leverage, Contract Specification, Risk Limit, การเปิด Algo Trading และผลลัพธ์จากการเทรดทั้งหมด ซอฟต์แวร์นี้เป็นเครื่องมืออัตโนมัติ ไม่ใช่ผู้จัดการการลงทุนและไม่รับประกันผลตอบแทน
