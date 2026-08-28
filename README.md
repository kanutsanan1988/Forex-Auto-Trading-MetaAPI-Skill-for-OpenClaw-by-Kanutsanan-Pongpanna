# Kanatsanan MetaAPI Trading Skill

Skill สำหรับ OpenClaw ที่เชื่อมต่อระบบวิเคราะห์และเทรดของ Kanatsanan เข้ากับบัญชี MetaTrader 4/5 ผ่านบริการ MetaAPI โดยใช้ MetaAPI Account ID และ API Token ของผู้ใช้งานเอง

Skill นี้ออกแบบให้ติดตั้งและปรับปรุงต่อได้อย่างอิสระภายในระบบ OpenClaw ของผู้ใช้งาน แต่คำสั่งส่งออเดอร์จริงจะถูกแยกจากคำสั่งอ่านข้อมูลอย่างชัดเจน และต้องได้รับการยืนยันจากผู้ใช้ก่อนทุกครั้งที่เปิดใช้โหมด Live

## ความสามารถ

- เชื่อมต่อบัญชี MT4/MT5 ผ่าน MetaAPI RPC
- ตรวจสอบสถานะการเชื่อมต่อและข้อมูลบัญชี
- อ่านราคา Bid/Ask และรายละเอียดสัญลักษณ์
- อ่านแท่งเทียนย้อนหลังของ M1, M5, M15 และ H1
- อ่าน Positions และ Pending Orders
- อ่านประวัติ Orders และ Deals ตามช่วงเวลา
- วิเคราะห์ตลาดด้วยกลยุทธ์ Kanatsanan แบบหลาย Timeframe
- คำนวณแนวโน้ม EMA, RSI, ATR, ADX, Bollinger, Choppiness และสัญญาณของกลยุทธ์ต่าง ๆ
- รองรับ Trend, Range, Mean Reversion, Breakout, Counter-trend และ Breakout Reversal
- สร้างแผนเข้าเทรดพร้อม Entry, Stop Loss, Take Profit และ Reward/Risk
- ทดลองระบบแบบ Dry-run โดยไม่ส่งคำสั่งจริง
- เทรดแบบ One-shot หรือทำงานเป็นรอบด้วย Loop
- ป้องกันการเปิดสถานะซ้ำใน Symbol เดียวกัน
- ปฏิเสธการเทรดเมื่อ Spread สูงเกินค่าที่กำหนด
- เก็บ Strategy Engine ไว้ภายใน Skill เพื่อให้ผู้ใช้แก้ไขและพัฒนาต่อได้เอง

## โครงสร้างไฟล์

```text
kanatsanan-metaapi-trading/
├── SKILL.md                    # คำสั่งหลักที่ OpenClaw โหลด
├── README.md                   # คู่มือภาษาไทยฉบับนี้
├── requirements.txt            # Python dependency
├── config.example.json          # ตัวอย่างค่าตั้งต้นที่ไม่มีข้อมูลลับ
├── .clawhubignore              # รายการไฟล์ที่ไม่ควรเผยแพร่
└── scripts/
    ├── metaapi_trading.py       # ตัวเชื่อมต่อ MetaAPI และ CLI
    └── strategy_engine.py       # เครื่องมือวิเคราะห์ของ Kanatsanan
```

## สิ่งที่ต้องเตรียม

1. บัญชี MetaAPI ที่ใช้งานได้
2. MetaAPI Account ID ของบัญชี MT4/MT5
3. MetaAPI API Token
4. Python 3 และอินเทอร์เน็ตสำหรับติดตั้ง SDK
5. บัญชีเทรดที่ตั้งค่า Login/Password/Server ใน MetaAPI แล้ว

หน้าตั้งค่าข้อมูลบัญชีของ MetaAPI ใช้รูปแบบ URL ต่อไปนี้:

```text
https://app.metaapi.cloud/configure-trading-account-credentials/<ACCOUNT_ID>
```

`<ACCOUNT_ID>` เป็นเพียงตัวแทน ต้องแทนด้วย Account ID ของผู้ใช้ในเครื่องของผู้ใช้เองเท่านั้น

## การตั้งค่า Credential

กำหนดตัวแปรสภาพแวดล้อมสองตัวนี้ในเครื่องที่รัน OpenClaw:

```bash
export METAAPI_TOKEN="ใส่-API-Token-ของคุณในเครื่องเท่านั้น"
export METAAPI_ACCOUNT_ID="ใส่-Account-ID-ของคุณในเครื่องเท่านั้น"
```

บน Windows PowerShell:

```powershell
$env:METAAPI_TOKEN = "ใส่-API-Token-ของคุณในเครื่องเท่านั้น"
$env:METAAPI_ACCOUNT_ID = "ใส่-Account-ID-ของคุณในเครื่องเท่านั้น"
```

ห้ามใส่ค่าเหล่านี้ลงใน `README.md`, `SKILL.md`, `config.example.json`, source code, Git repository หรือข้อความแชต ควรใช้ Secret Manager ของเครื่องหรือการตั้งค่า environment ของ OpenClaw แทน

## การติดตั้ง

ติดตั้ง dependency ด้วยคำสั่งใดคำสั่งหนึ่ง:

```bash
python3 -m pip install -r requirements.txt
```

หรือใช้ `uv`:

```bash
uv pip install -r requirements.txt
```

ตรวจสอบว่า Skill ถูกค้นพบโดย OpenClaw:

```bash
openclaw skills list
openclaw skills check
```

หากติดตั้ง Skill ไว้ในโฟลเดอร์ท้องถิ่น ให้ติดตั้งจากโฟลเดอร์ที่มี `SKILL.md` อยู่ที่ root ของ Skill:

```bash
openclaw skills install ./kanatsanan-metaapi-trading
```

## การทดสอบการเชื่อมต่อ

เริ่มจากตรวจสอบสถานะบัญชี:

```bash
python3 scripts/metaapi_trading.py status
```

ผลลัพธ์จะเป็น JSON และควรแสดงสถานะบัญชีที่ MetaAPI deploy และ synchronize สำเร็จแล้ว หากยังไม่ได้ตั้งค่า Credential หรือบัญชีเชื่อมต่อ Broker ไม่ได้ โปรแกรมจะแสดง error และจะไม่ส่งคำสั่งเทรด

ตรวจสอบราคาและรายละเอียด Symbol:

```bash
python3 scripts/metaapi_trading.py snapshot --symbol XAUUSD
```

ชื่อ Gold ของแต่ละ Broker อาจแตกต่างกัน เช่น `XAUUSDm`, `XAUUSD.sml` หรือ `GOLD` ให้ใช้ชื่อที่ MetaAPI แสดงจริง

## คำสั่งอ่านข้อมูล

อ่านแท่งเทียน:

```bash
python3 scripts/metaapi_trading.py candles --symbol XAUUSD --timeframe M5 --limit 300
```

อ่านสถานะบัญชีและตลาด:

```bash
python3 scripts/metaapi_trading.py status
python3 scripts/metaapi_trading.py positions
python3 scripts/metaapi_trading.py orders
python3 scripts/metaapi_trading.py history --days 30
```

คำสั่งเหล่านี้เป็น Read-only และไม่ส่งคำสั่งซื้อขาย

## การวิเคราะห์กลยุทธ์

คำสั่ง `analyze` จะอ่านแท่งเทียนปิดแล้วจาก M1, M5, M15 และ H1 แล้วส่งผ่าน Strategy Engine ของ Kanatsanan:

```bash
python3 scripts/metaapi_trading.py analyze --symbol XAUUSD
```

ผลลัพธ์จะมีข้อมูลสำคัญ เช่น:

- แนวโน้มของแต่ละ Timeframe
- Regime ของตลาด
- Strategy ที่ระบบเลือก
- Buy/Sell score และความมั่นใจ
- ราคา Entry ที่อ้างอิงจาก Ask หรือ Bid
- ระยะ Stop Loss และ Take Profit
- Spread และผลตรวจสอบ Risk เบื้องต้น
- ข้อมูลประกอบการตัดสินใจของแต่ละ Timeframe

การวิเคราะห์เป็นข้อมูลประกอบการตัดสินใจ ไม่ใช่การรับประกันผลกำไร และไม่ใช่คำแนะนำการลงทุน

## Dry-run และการส่งคำสั่งจริง

ทดลองวางแผนโดยไม่ส่งคำสั่ง:

```bash
python3 scripts/metaapi_trading.py once --symbol XAUUSD --volume 0.01
```

คำสั่งจะวิเคราะห์ตลาด ตรวจ Spread และตรวจสถานะที่มีอยู่ แล้วแสดงแผนเป็น JSON โดยไม่ส่ง Order

การส่งคำสั่งจริงต้องมี flags สองตัวพร้อมกัน:

```bash
python3 scripts/metaapi_trading.py trade \
  --symbol XAUUSD \
  --volume 0.01 \
  --live \
  --confirm-live
```

ก่อนใช้คำสั่งนี้ ผู้ใช้ควรตรวจสอบ Symbol, Volume, Side, Entry, Stop Loss, Take Profit, Spread, Equity และ Risk Limit จากผลลัพธ์ Dry-run ก่อนเสมอ การมี flags ดังกล่าวถือเป็นการอนุญาตให้โปรแกรมส่ง Order จริงไปยังบัญชี MetaAPI

เงื่อนไขที่ระบบตรวจสอบก่อนส่งคำสั่ง ได้แก่:

- ต้องมีสัญญาณ Buy หรือ Sell ที่ผ่าน Strategy Engine
- Spread ต้องไม่เกิน `max_spread`
- ต้องไม่มี Position ของ Symbol เดียวกันอยู่แล้ว
- บัญชีต้องอนุญาตให้เทรด
- ต้องระบุ `--live --confirm-live` ครบทั้งสองตัว

## การทำงานอัตโนมัติแบบ Loop

ทำงานแบบ Dry-run ทุก 60 วินาที:

```bash
python3 scripts/metaapi_trading.py loop --symbol XAUUSD --interval 60
```

ทำงานแบบ Live ต้องระบุอย่างชัดเจน:

```bash
python3 scripts/metaapi_trading.py loop \
  --symbol XAUUSD \
  --volume 0.01 \
  --interval 60 \
  --live \
  --confirm-live
```

Loop จะเริ่มเชื่อมต่อและวิเคราะห์ใหม่ในแต่ละรอบ แต่ไม่ควรถือว่าเป็นระบบบริหารความเสี่ยงเต็มรูปแบบ ผู้ใช้ต้องกำหนด Volume, Spread, Stop Loss, Take Profit และขีดจำกัดความเสี่ยงให้เหมาะสมกับบัญชีของตนเอง และควรมีวิธีหยุด process ได้ทันที

## การปรับปรุง Skill

ผู้ใช้สามารถแก้ไข `scripts/strategy_engine.py` เพื่อพัฒนากลยุทธ์ เพิ่ม Indicator หรือเปลี่ยนกฎการคัดเลือกสัญญาณได้โดยตรง และแก้ไข `scripts/metaapi_trading.py` เพื่อเพิ่มคำสั่ง MetaAPI อื่น ๆ

หลักที่ควรรักษาไว้เมื่อแก้ไข:

- อย่าฝัง Credential จริงไว้ในไฟล์ใด ๆ
- ให้คำสั่งอ่านข้อมูลยังคงเป็น Read-only
- คงการใช้แท่งเทียนปิดแล้วในการวิเคราะห์
- คงการยืนยันแยกสำหรับ Live trading
- ตรวจ Symbol และ Position ก่อนเปิด Order
- คืนผลลัพธ์เป็น JSON เพื่อให้ OpenClaw อ่านและสรุปได้
- อย่าเปลี่ยน Dry-run ให้ส่งคำสั่งจริงโดยอัตโนมัติ

ทดสอบ syntax และ CLI:

```bash
python3 -m py_compile scripts/metaapi_trading.py scripts/strategy_engine.py
python3 scripts/metaapi_trading.py --help
```

## การเผยแพร่ขึ้น ClawHub

เข้าสู่ระบบ ClawHub ก่อน:

```bash
npm install -g clawhub
clawhub login
clawhub whoami
```

เผยแพร่จากโฟลเดอร์ parent ของ Skill:

```bash
clawhub skill publish ./kanatsanan-metaapi-trading \
  --slug kanatsanan-metaapi-trading \
  --version 1.0.0
```

หลังเผยแพร่ ควรตรวจผล Security Scan และทดสอบติดตั้งใน OpenClaw อีกครั้ง ห้ามเผยแพร่ไฟล์ `.env`, token, key, password, log ที่มีข้อมูลบัญชี หรือไฟล์ runtime ที่สร้างจากการใช้งานจริง

## ข้อจำกัดและความรับผิดชอบ

MetaAPI เป็นบริการเชื่อมต่อระหว่าง Skill กับบัญชี MT4/MT5 ของผู้ใช้ ค่าใช้บริการ, ค่า Spread, Slippage, Margin, กฎของ Broker และผลลัพธ์การเทรดขึ้นกับบัญชีและตลาดจริง ผู้ใช้เป็นผู้รับผิดชอบการตั้งค่าและการส่งคำสั่งทั้งหมด ระบบนี้ไม่รับประกันผลกำไรและไม่ใช่คำแนะนำทางการเงิน

เอกสารอ้างอิง:

- [MetaAPI Documentation](https://metaapi.cloud/docs/)
- [MetaAPI Python Examples](https://metaapi.cloud/docs/client/usingCodeExamples/)
- [OpenClaw Skill Format](https://docs.openclaw.ai/clawhub/skill-format)
- [ClawHub](https://clawhub.ai/)
