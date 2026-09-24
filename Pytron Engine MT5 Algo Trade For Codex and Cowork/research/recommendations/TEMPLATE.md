<!--
  ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
    Facebook: https://www.facebook.com/LoveMoneyTH
    YouTube:  https://youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->
{
  "schema": "hermes-trading-recommendation-v1",
  "llm_provider": "example: openrouter/anthropic/local-llama (ระบุ LLM ที่ใช้)",
  "summary": "สรุปคำแนะนำ 1 ประโยค",
  "auto_apply": true,
  "restart_after_apply": true,
  "research_reference": "research/2026-09-12-xxx.md",
  "changes": [
    {
      "action": "set_gate",
      "strategy": "trend",
      "side": "buy",
      "raw_low": 0.45,
      "raw_high": 0.80,
      "reason": "ช่วงคะแนนที่ควรเทรดตามงานวิจัย"
    },
    {
      "action": "toggle_strategy",
      "strategy": "mean_reversion",
      "enabled": false,
      "reason": "ขาดทุนต่อเนื่องตาม P/L attribution"
    },
    {
      "action": "set_weights",
      "strategy_weights": {"range": 1.2, "trend": 0.8},
      "reason": "range มีกำไรสุด เอียงน้ำหนัก"
    },
    {
      "action": "set_risk",
      "max_risk_pct": 8.0,
      "reason": "ปรับความเสี่ยง"
    }
  ]
}