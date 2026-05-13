---
name: forex-auto-trading
description: "AI-driven Forex Auto Trading System for XAUUSD using OpenRouter (Gemini 3.1 Flash Lite) and MetaAPI"
---

# Forex Auto Trading System

ระบบเทรดอัตโนมัติสำหรับคู่เงิน XAUUSD (Gold) ที่ขับเคลื่อนด้วย AI ผ่าน OpenRouter (ใช้โมเดล `google/gemini-3.1-flash-lite`) โดยทำงานร่วมกับ MetaAPI เพื่อดึงข้อมูลและส่งคำสั่งซื้อขาย ระบบนี้ออกแบบมาเพื่อการเทรดแบบ Scalping โดยเฉพาะ

## Architecture Overview

ระบบทำงานโดยใช้ Python script (`auto_trade.py`) เป็นแกนหลัก ซึ่งจะถูกเรียกใช้งานทุกๆ 5 นาทีผ่าน systemd timer หรือ cron job กระบวนการทำงานมีดังนี้:

1. **ตรวจสอบสถานะบัญชีและตลาด**: ตรวจสอบว่าตลาดเปิดหรือไม่ และดึงข้อมูล Balance, Equity, Free Margin
2. **ตรวจสอบ Position**: ระบบเปิดได้สูงสุด 5 positions พร้อมกัน หากเต็ม 5 แล้วจะข้ามการทำงาน แต่ยังตรวจสอบ Break-Even ทุก position ทุกรอบ
3. **ดึงข้อมูลราคาและกราฟ (Real-time)**: ระบบมี 3 แหล่งข้อมูล (Fallback mechanism):
   - **Source 1**: MetaAPI candles (M15 + H1) - ข้อมูลดิบจากโบรกเกอร์
   - **Source 2**: TradingView Scanner API
   - **Source 3**: TradingView Web
   *กฎเหล็ก: หากไม่สามารถดึงข้อมูลจากทั้ง 3 แหล่งได้ ระบบจะหยุดทำงานและไม่เทรดเด็ดขาด*
4. **AI Analysis**: ส่งข้อมูลทั้งหมดให้ OpenRouter AI วิเคราะห์เพื่อตัดสินใจ (BUY/SELL/SKIP) พร้อมกำหนดความมั่นใจ (Strength) และจุดตัดขาดทุน/ทำกำไร (SL/TP)
5. **Risk Management**: 
   - คำนวณ Lot size อัตโนมัติ (สูงสุด 50% ของ Free Margin, ขั้นต่ำ 0.001, สูงสุด 0.1)
   - บังคับ TP แบบขั้นบันได: TP>10pts→5, TP>5pts→2.5, TP>2.5pts→1
   - บังคับ TP ต้องไม่เกิน SL (Risk:Reward ขั้นต่ำ 1:1)
   - เทรดเมื่อ AI ให้คะแนนความมั่นใจ (Strength) $\ge$ 6/10 เท่านั้น
6. **Entry Decision Framework (ตรวจสอบตามลำดับ)**:
   - **A) Late Entry Check**: ถ้าราคาห่างจาก EMA20 เกิน 1.5x ATR → SKIP (ป้องกันไล่ราคา)
   - **B) RSI Extreme + Divergence**: RSI > 70 + bearish divergence → พิจารณา Reversal SELL, RSI < 30 + bullish divergence → พิจารณา Reversal BUY, ไม่มี divergence → SKIP
   - **C) Trend-Following (Pullback)**: H1 Filter ใช้ที่นี่, รอราคา pullback มาหา EMA20, RSI 35-65
   - **D) Reversal Entry**: ไม่ต้องผ่าน H1 Filter, ต้องมีอย่างน้อย 2/3 สัญญาณ (RSI divergence, reversal candle, key level rejection)
   - **Entry Priority**: Pullback (ดีสุด) > Reversal (ดี) > Breakout (พอได้) > ไล่ราคา (ห้ามทำ)
7. **Break-Even Logic**: เมื่อกำไร >= 50% ของระยะ TP จะย้าย SL มาที่จุดเข้า (break-even) เพื่อป้องกันไม่ให้ออเดอร์ที่เคยกำไรกลับมาขาดทุน
8. **Execution**: ส่งคำสั่งซื้อขายผ่าน MetaAPI

## Prerequisites & Installation

### สิ่งที่ต้องเตรียม
1. **METAAPI_TOKEN**: API Key จาก MetaAPI
2. **METAAPI_ACCOUNT_ID**: Account ID ของบัญชีเทรดใน MetaAPI
3. **OPENROUTER_API_KEY**: API Key จาก OpenRouter

### วิธีติดตั้งและใช้งาน

1. คัดลอกไฟล์ทั้งหมดในโฟลเดอร์ `scripts/` ไปยังเครื่องที่ต้องการรัน
2. รันสคริปต์ติดตั้ง:
   ```bash
   sudo ./setup.sh
   ```
3. แก้ไขไฟล์ `.env` เพื่อใส่ API Keys:
   ```bash
   nano .env
   ```
   ใส่ข้อมูลดังนี้:
   ```env
   METAAPI_TOKEN=YOUR_METAAPI_TOKEN_HERE
   METAAPI_ACCOUNT_ID=YOUR_METAAPI_ACCOUNT_ID_HERE
   OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY_HERE
   ```
4. ระบบจะเริ่มทำงานอัตโนมัติตาม Cron job ที่ตั้งไว้ (ทุก 10 นาทีตามค่าเริ่มต้นใน `setup.sh` แต่สามารถปรับเป็น 5 นาทีได้)

### คำแนะนำ Cloud Computer

เพื่อประหยัดเครดิต Manus ผู้ใช้สามารถซื้อ **Cloud Computer ของ Manus** แล้วให้ Manus AI Agent เขียนสคริปต์ระบบทั้งหมดเพื่อรันบน Cloud Computer โดยสามารถใช้ API Key จาก AI ตัวอื่นๆ ที่ประหยัดกว่า หรือจาก OpenRouter ก็ได้ วิธีนี้จะช่วยให้ระบบทำงานได้ตลอด 24 ชั่วโมงโดยไม่ต้องเปิดเครื่องคอมพิวเตอร์ส่วนตัวทิ้งไว้ และประหยัดค่าใช้จ่ายในระยะยาว

## Manual Trade Check (ดูผลวิเคราะห์โดยไม่เทรดจริง)

หากต้องการดูผลการวิเคราะห์ของ AI โดยที่ยังไม่ต้องการให้ระบบส่งคำสั่งซื้อขายจริง สามารถทำได้โดย:

1. รันสคริปต์ด้วยตนเอง:
   ```bash
   cd /path/to/scripts
   ./venv/bin/python auto_trade.py
   ```
2. ตรวจสอบผลการวิเคราะห์ใน Terminal หรือดูจากไฟล์ Log:
   ```bash
   python3 trade_log.py 50
   ```
   *(หมายเหตุ: หากต้องการให้เป็นโหมด "ดูอย่างเดียว" อย่างแท้จริง ควรคอมเมนต์ส่วน `requests.post` ในขั้นตอน "Step 8: Execute trade" ของไฟล์ `auto_trade.py` ออกก่อน)*

## Approval / Safety Conditions

ระบบมีเงื่อนไขความปลอดภัยที่เข้มงวดเพื่อป้องกันความเสียหาย:

1. **No Data = No Trade**: หากไม่สามารถดึงข้อมูลกราฟแบบ Real-time ได้จากทั้ง 3 แหล่ง ระบบจะปฏิเสธการเทรดทันที
2. **Market Closed**: ระบบจะไม่ทำงานในวันเสาร์-อาทิตย์
3. **Insufficient Margin**: หาก Free Margin ไม่เพียงพอสำหรับการเปิด Lot ขั้นต่ำ (0.001) ระบบจะข้ามการเทรด
4. **AI Confidence**: AI ต้องมีความมั่นใจระดับ 6/10 ขึ้นไปจึงจะเปิดออเดอร์
5. **H1 Directional Filter**: ใช้กับ Trend-Following เท่านั้น (H1 Bullish → BUY only, H1 Bearish → SELL only, H1 Neutral → ตาม M15) ไม่ใช้กับ Reversal trades
6. **Entry Decision Framework**: Late Entry Check → RSI/Divergence → Trend-Following (Pullback) → Reversal Entry ตรวจสอบตามลำดับ ไม่มีเงื่อนไขซ้ำซ้อน
7. **Break-Even**: ย้าย SL มาจุดเข้าเมื่อกำไร >= 50% ของ TP distance

## Position Management Rules

1. **Max Positions**: เปิดได้สูงสุด 5 positions พร้อมกัน ระบบจะตรวจสอบ Break-Even ทุก position ทุกรอบ
2. **Lot Sizing**: 
   - คำนวณอัตโนมัติจาก Free Margin (ใช้สูงสุด 50%)
   - Lot ขั้นต่ำ: 0.001
   - Lot สูงสุด: 0.1
3. **Take Profit (TP) & Stop Loss (SL)**:
   - SL ถูกกำหนดโดย AI (ประมาณ 20% ของ M15 ATR)
   - TP ถูกจำกัดแบบขั้นบันได: TP>10pts ปรับเป็น 5 pts, TP>5pts ปรับเป็น 2.5 pts, TP>2.5pts ปรับเป็น 1 pt
   - TP ต้องน้อยกว่าหรือเท่ากับ SL เสมอ (เพื่อรักษาสัดส่วน Risk:Reward)

## Files in this Skill

- `scripts/auto_trade.py`: สคริปต์หลักสำหรับรันระบบเทรด
- `scripts/trade_log.py`: สคริปต์สำหรับดูและสรุปผลการเทรดจาก Log
- `scripts/setup.sh`: สคริปต์สำหรับติดตั้ง Environment และ Cron job
- `.env.example`: ไฟล์ตัวอย่างสำหรับตั้งค่า Environment Variables
