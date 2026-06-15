# Kanutsanan Pongpanna AI Auto Trading v5.0

## XAUUSD (Gold) Automated Trading System with Self-Evolution

### Features
- **Dual Calculation System**: Mean-Reversion + Trend-Following
- **3 AI Agents** (parallel processing): Agent1(MR) + Agent2(TF) + Coordinator
- **Self-Evolution**: เรียนรู้จากประวัติเทรด ปรับตัวเองอัตโนมัติ
- **Swing/Trend Auto-Switch**: สลับ style ตามสภาพตลาด
- **AI-Calculated SL**: ATR-based, ไม่ fix ค่าตายตัว
- **TP max 5 pts**
- **Break-Even Logic**: ย้าย SL เมื่อกำไร >= 50% TP
- **No max_tokens**: ให้ AI คิดเต็มที่

### Files
- `auto_trade.py` - ระบบเทรดหลัก (auto + manual)
- `trade_check.py` - เช็คเทรด manual
- `trade_log.py` - ดูประวัติการเทรด
- `setup.sh` - ติดตั้ง systemd service/timer

### Quick Start
```bash
# ติดตั้ง
export OPENROUTER_API_KEY="your-key"
sudo bash setup.sh

# เช็คเทรด
python3 auto_trade.py check

# เทรดอัตโนมัติ
python3 auto_trade.py auto 5

# ดูผลงาน
python3 auto_trade.py performance
```

### AI Model
- Primary: google/gemini-3.5-flash (via OpenRouter)
- No max_tokens limit

### Self-Evolution
ระบบจะบันทึกทุกเทรดลง `trade_memory.json` และใช้ข้อมูลนี้ปรับปรุงการตัดสินใจอัตโนมัติ:
- วิเคราะห์ win rate ของแต่ละ market regime
- ปรับ preferred style (Trend/MR/Auto)
- เรียนรู้ patterns ที่ทำกำไร vs ขาดทุน
- สะสมประสบการณ์ไปเรื่อยๆ
