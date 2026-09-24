# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""โหราศาสตร์ไทยสำหรับเทรด (Thai Astrology for Trading)
ใช้ตำรา 2 เล่ม: 
  1) ตำราโหรทายหนู — ทายทักตามดาวประจำวัน (อาทิตย์..เสาร์)
  2) ตำราเลข 7 ตัว 9 ฐาน — ใช้ตัวเลขจากเวลาประมวลผล (ว/ด/ป/ชม/นาที/วิ) 
     ประกอบเป็น "เลข 7 ตัว" แล้วลดด้วย 9 ฐาน เกิดเลขทาย 1-9
ใช้ตัวเลขเวลาตอนประมวลผลเป็นเครื่องมือสร้างคำทำนาย — เป็นสัญญาณร่วม (secondary)
ประกอบกับข้อมูลตลาดจริง ไม่ใช่ตัวตัดสินหลัก  (ความแม่นยำเป็นไปตามตำรา ไม่รับประกัน)

directional bias: bullish / bearish / sideways พร้อม strength 0-1
"""
import datetime

# ---------- ตำราโหรทายหนู: ดาวประจำวัน ----------
# วันอาทิตย์=1 .. เสาร์=7 (เลขโหรประจำวันตามตำราไทย)
STAR_BY_WEEKDAY = {0:"จันทร์",1:"อังคาร",2:"พุธ",3:"พฤหัสบดี",4:"ศุกร์",5:"เสาร์",6:"อาทิตย์"}
STAR_NUM = {"อาทิตย์":1,"จันทร์":2,"อังคาร":3,"พุธ":4,"พฤหัสบดี":5,"ศุกร์":6,"เสาร์":7}
# ลักษณะดาว (ตามตำราโหรทายหนู: ธาตุ + ฤทธิ์)
STAR_TRAIT = {
 "อาทิตย์": {"element":"ไฟ","tone":"ร้อนแรง","bias":"bullish","power":0.55},
 "จันทร์": {"element":"น้ำ","tone":"ไหลขึ้นลง","bias":"sideways","power":0.35},
 "อังคาร": {"element":"ไฟ","tone":"ดุเดือด","bias":"bullish","power":0.60},
 "พุธ": {"element":"ดิน","tone":"แปรปรวน","bias":"sideways","power":0.40},
 "พฤหัสบดี": {"element":"ดิน","tone":"มั่นคง","bias":"bullish","power":0.50},
 "ศุกร์": {"element":"น้ำ","tone":"นุ่มนวล","bias":"sideways","power":0.35},
 "เสาร์": {"element":"ลม","tone":"หดหู่","bias":"bearish","power":0.55},
}

# ---------- ตำราเลข 7 ตัว 9 ฐาน ----------
# นำตัวเลขเวลาประมวลผลมาสร้าง "เลข 7 ตัว": วว ดด ปปปป ชม นน วิ (ใช้หลักหน่วย)
# แล้วรวมลดเหลือเลข 1-9 (ฐาน 9) + ประกอบ "เลขคู่เสียง" (ผลรวม 2 ตัวท้าย)
BASE9_MEANING = {
 1: {"bias":"bullish","desc":"เลข 1 — จุดเริ่มเดินหน้า แนวโน้มขึ้น"},
 2: {"bias":"sideways","desc":"เลข 2 — คู่สมดุล รอจังหวะ"},
 3: {"bias":"bullish","desc":"เลข 3 — กำไรเสริม เลื่อนขึ้น"},
 4: {"bias":"sideways","desc":"เลข 4 — เสถียร ทรงตัว"},
 5: {"bias":"bearish","desc":"เลข 5 — เปลี่ยนแปลง ผันผวนลงได้"},
 6: {"bias":"bullish","desc":"เลข 6 — เดินขึ้น เกื้อหนุน"},
 7: {"bias":"bearish","desc":"เลข 7 — เสี่ยง ดาวเสาร์กด"},
 8: {"bias":"bullish","desc":"เลข 8 — มั่งคั่ง เฟื่องฟู"},
 9: {"bias":"sideways","desc":"เลข 9 — ครบรอบ จบ-เริ่มใหม่"},
}

def _to_base9(n: int) -> int:
    if n <= 0: return 9
    r = n % 9
    return r if r != 0 else 9

def thai_astrology_now(now: datetime.datetime | None = None) -> dict:
    now = now or datetime.datetime.now()
    # ตัวเลขเวลา 7 ตัว
    dd, mm, yy = now.day, now.month, now.year % 100
    hh, nn, ss = now.hour, now.minute, now.second
    lucky7 = [dd % 10 or 10, mm % 10 or 10, yy % 10 or 10,
              hh % 10 or 10, nn % 10 or 10, ss % 10 or 10,
              1]  # ตัวที่ 7 = 1 (ตัวตั้งต้น/ตัวตน)
    total = sum(lucky7)
    base9 = _to_base9(total)
    # เลขคู่เสียง = หลักหน่วยของ (ผลรวมตัวที่ 1-3 + ตัวที่ 4-6)
    tone = _to_base9(sum(lucky7[0:3]) + sum(lucky7[3:6]))
    # ดาวประจำวัน
    star = STAR_BY_WEEKDAY[now.weekday()]
    trait = STAR_TRAIT[star]
    b9 = BASE9_MEANING[base9]

    # รวม bias: ถ้าสองฝั่งตรงกัน -> แรง; ขัดกัน -> sideways
    biases = [trait["bias"], b9["bias"]]
    if biases[0] == biases[1]:
        bias = biases[0]
        strength = 0.5 + 0.3 * trait["power"]
    elif "sideways" in biases:
        bias = biases[0] if biases[0] != "sideways" else biases[1]
        strength = 0.35
    else:
        bias = "sideways"
        strength = 0.25
    strength = round(min(0.9, strength), 3)

    return {
        "method": "thai-astrology (โหรทายหนู + เลข 7 ตัว 9 ฐาน)",
        "timestamp": now.isoformat(),
        "lucky7": lucky7,
        "total_digits": total,
        "base9": base9,
        "base9_desc": b9["desc"],
        "tone_digit": tone,
        "weekday_star": star,
        "star_trait": f'{trait["tone"]} ({trait["element"]})',
        "directional_bias": bias,
        "strength": strength,
        "advice": b9["desc"] + f" — วัน{star} ลักษณะ{trait['tone']}",
    }

if __name__ == "__main__":
    import json
    now = datetime.datetime.now()
    print("เวลาประมวลผล:", now.strftime("%Y-%m-%d %H:%M:%S %A"))
    print(json.dumps(thai_astrology_now(now), ensure_ascii=False, indent=2))