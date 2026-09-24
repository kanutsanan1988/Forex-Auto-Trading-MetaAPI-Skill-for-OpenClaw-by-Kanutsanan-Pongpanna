# MetaAPI Python example ZIP — safety and compatibility review

ผู้สร้างระบบ: Kanutsanan Pongpanna — https://www.facebook.com/LoveMoneyTH  
วันที่ตรวจ: 24 กันยายน 2026 (เวลาไทย)

## ขอบเขต

ตรวจรายการไฟล์และอ่านข้อความใน ZIP ที่ผู้ใช้แนบเพื่อประเมินตัวอย่างการเชื่อมต่อ MetaAPI เท่านั้น ไม่รันตัวอย่าง, ไม่ deploy/undeploy บัญชี, ไม่อ่าน/เปลี่ยนคำสั่งซื้อขาย และไม่บันทึกค่าลับจากไฟล์แนบไว้ในรายงานนี้

## สิ่งที่พบ

- ZIP มี `example.py` และ `requirements.txt` โดยตัวอย่างใช้ `metaapi-cloud-sdk` และ `MetaApi` SDK
- ตัวอย่างมี JWT credential ฝังเป็นค่า fallback ในซอร์ส แทนที่จะบังคับอ่านจาก environment; token นี้ไม่ควรถูกแจกต่อหรือใช้หลังการแชร์
- ตัวอย่างเชื่อม RPC, รอ synchronization และอ่านข้อมูลบัญชี/positions/orders ได้ แต่ยังพิมพ์ข้อมูลบัญชีและประวัติออก stdout ซึ่งไม่เหมาะกับ log สาธารณะ
- ตัวอย่างเรียก `account.deploy()` เมื่อบัญชียังไม่ deployed และมีส่วนส่ง `create_limit_buy_order()` สำหรับ GBPUSD จึงไม่ใช่สคริปต์ตรวจ read-only และห้ามนำมารันตรง ๆ เพื่อทดสอบการเชื่อมต่อ
- ห้ามนำ token หรือ Account ID จากไฟล์ตัวอย่างไปใช้หรือคัดลอกเข้าสู่แพ็กเกจแจกจ่าย

## ผลทดสอบ read-only

### ก่อนเปลี่ยน credential

- ตัวแปร Windows User ถูกปฏิเสธที่ account lookup ด้วย `UnauthorizedException`
- ไฟล์ `.env` ก่อนการเปลี่ยน credential ตรงกับ token ที่ฝังใน ZIP จึงไม่ถูกนำไปใช้

### หลังผู้ใช้ยืนยันว่าเปลี่ยน credential และแก้ `.env`

- ทดสอบ MetaAPI SDK โดยตรงจาก credential ใน `release/metaapi-validation-local/.env`:
  `get_account()` สำเร็จ, state เป็น deployed, RPC synchronization สำเร็จ และอ่าน account information, positions, orders สำเร็จ
- ผลการทดสอบ: `readonly_connected`; ไม่เรียก `deploy`, `order_send`, `create_limit_buy_order` หรือคำสั่งปิด Position
- การทดสอบนี้ยืนยันการเชื่อมต่อ SDK แบบอ่านอย่างเดียวเท่านั้น ยังไม่ยืนยันว่า MT5 shim ทำงานร่วมกับระบบเทรดรุ่นล่าสุด

## ข้อสรุปและเงื่อนไขก่อนเดินหน้าชุด MetaAPI

ตัวอย่างนี้ช่วยอธิบายลำดับการใช้ SDK แต่ตัวอย่างเดิมไม่ปลอดภัยสำหรับการรันตรง ๆ ผู้ใช้ยืนยันว่าเปลี่ยน credential ในไฟล์ `.env` แล้ว และการเชื่อมต่อ SDK แบบอ่านอย่างเดียวผ่านครบ อย่างไรก็ดี token ที่แชร์ใน ZIP ควรถูกเพิกถอน/หมุนใหม่ตามคำแนะนำด้านความปลอดภัย ก่อนส่งมอบชุด MetaAPI ยังต้องทดสอบ adapter/shim กับ source รุ่นล่าสุดใน read-only mode และตรวจว่าไม่มีคำสั่งซื้อขายถูกเรียก

แนวทางตัวอย่างที่ปลอดภัยต้องไม่ deploy/undeploy เอง, ไม่ส่งคำสั่งซื้อขาย, ไม่พิมพ์ account payload หรือ credential และหยุดพร้อมรายงานเหตุผลเมื่อ authorization ล้มเหลว

## ตรวจไฟล์ตัวอย่างที่ส่งแยกภายหลัง

ผู้ใช้ส่ง `example.py` และ `requirements.txt` แยกอีกครั้งในวันที่ 24 ก.ย. 2026 ซึ่งเป็น snapshot ต่างจาก ZIP เดิม: ไฟล์ล่าสุดอ่าน `TOKEN` และ `ACCOUNT_ID` จาก environment และไม่พบ token ฝังใน source ที่ตรวจซ้ำนี้; ห้ามนำข้อสรุป token ฝังจาก ZIP เดิมไปเหมารวมกับไฟล์ใหม่ อย่างไรก็ตาม `example.py` ล่าสุดยังเรียก `account.deploy()`/`account.undeploy()` ได้ และมี `create_limit_buy_order()` อยู่ในเส้นทางที่เรียกจาก main จึงยังห้ามรันตรง ๆ ในการตรวจ read-only

`requirements.txt` ระบุ `metaapi-cloud-sdk>=28.0.0`; isolated validation environment ในเครื่องมี SDK รุ่น `29.1.1`. ก่อนเผยแพร่ SDK ที่คัดลอกมากับแพ็กเกจ ต้องคง LICENSE/เงื่อนไขเจ้าของ MetaApi ไว้ใน third-party notices แยกจาก MIT ของซอร์สโครงการ

## ผลทดสอบซ้ำหลังหมุน token รอบล่าสุด

- พบ `METAAPI_TOKEN` ใน process environment ซึ่งไม่ตรงกับค่าในไฟล์ `.env`; `METAAPI_ACCOUNT_ID` ใน process environment ตรงกับไฟล์
- คำขอแรกที่ปล่อยให้ environment ทับ `.env` ได้ `UnauthorizedException`; จากนั้นทดสอบใหม่โดยลบตัวแปร MetaAPI ออกจาก child process ชั่วคราว (ไม่ได้ลบค่าถาวรจากเครื่อง) เพื่อให้สคริปต์อ่าน `.env` โดยตรง
- SDK เชื่อม WebSocket ไปยัง MetaApi region ได้ แต่ `get_account()` ของ account ID ที่กำหนดตอบ `NotFoundException`; จึงยังไม่ได้อ่าน account info/positions/orders ในรอบล่าสุด
- ไม่เรียก deploy/undeploy, order_send, create_limit_buy_order หรือ close-position ใด ๆ
- ผลล่าสุดนี้ supersede ผลเชื่อมต่อผ่านจากการทดสอบก่อนหน้าที่เกิดก่อน credential retest รอบนี้; ณ จุดปัจจุบัน gate การเชื่อมบัญชีจริงยังไม่ผ่าน ต้องยืนยัน token/account-ID คู่ที่ถูกต้องก่อนเดินหน้าชุด MetaAPI
