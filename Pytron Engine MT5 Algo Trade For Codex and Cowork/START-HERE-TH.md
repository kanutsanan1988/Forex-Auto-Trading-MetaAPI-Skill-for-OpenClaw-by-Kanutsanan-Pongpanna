# เริ่มต้นใช้งาน Kanatsanan MT5 Trading Suite

ชุดส่งมอบประกอบด้วย 3 ไฟล์:

1. `kanatsanan-mt5-codex-plugin-v1.0.0.zip` — ส่งให้ Codex หรือแตกเพื่อติดตั้งเป็น Codex Plugin
2. `mt5-gold-trading-cowork-skill-v1.0.0.zip` — อัปโหลดใน Claude/Cowork ที่ Customize > Skills
3. `kanatsanan-mt5-bridge-v1.0.0.mcpb` — ติดตั้ง Local Connector ใน Claude Desktop/Cowork

## Codex

อัปโหลดไฟล์ Codex Plugin ZIP แล้วขอให้ Codex:

> แตกและติดตั้ง Plugin นี้ในเครื่อง Windows ของฉัน เชื่อมกับ MT5 ที่ฉันล็อกอินไว้ แล้วทดสอบแบบ read-only เท่านั้น ห้ามเปิด live trading และห้ามส่งคำสั่งซื้อขาย

## Claude/Cowork

1. อัปโหลด Cowork Skill ZIP ที่ Customize > Skills
2. ติดตั้งไฟล์ `.mcpb` ที่ Claude Desktop > Customize/Extensions
3. ตั้งชื่อสัญลักษณ์ทองให้ตรงกับโบรกเกอร์
4. เริ่มด้วยคำขอทดสอบ read-only เช่นเดียวกับข้อความด้านบน

ต้องใช้ Windows และ MetaTrader 5 ที่ผู้ใช้เปิดและล็อกอินบัญชีของตนเอง ระบบไม่ต้องการรหัสผ่าน MT5

การเปิดเงินจริงต้องผ่านการยืนยันเลขท้ายบัญชี ความเสี่ยง และข้อความยอมรับความเสี่ยงแยกต่างหาก ผลการทดสอบย้อนหลังไม่รับประกันกำไร
