# -*- coding: utf-8 -*-
"""human_behavior_research.py — งานวิจัยพฤติกรรมการเทรดของ "มนุษย์ที่เทรดร่วม" (30 ก.ย. 2026)

คำสั่งเจ้าของระบบ (ถ้อยคำจริง):
  "แล้วก็มีระบบงานวิจัยและงานเรียนรู้พฤติกรรมการเทรดที่มนุษย์เทรดร่วมด้วยนะครับ
   เพื่อที่จะคัดสรรสิ่งที่ดีๆไว้เรียนรู้ไว้ปรับไว้แก้ไขระบบเทรดให้สอดคล้องกับพฤติกรรมการเทรดของมนุษย์ด้วยครับ
   ทางนี้ก็เพื่อกำไรสูงสุดนะครับเป้าหมายสูงสุดคือกำไรครับ"

ทำอะไร:
  1) แยก "ไม้ของระบบ" กับ "ไม้ของมนุษย์" จากบันทึกจริง (ticket ที่ระบบไม่ได้เปิด = ของมนุษย์)
  2) วัดพฤติกรรม: ทิศทาง · ช่วงเวลาที่เทรด · มี/ไม่มี TP-SL · การถือไม้ · ผลลัพธ์จริง
  3) เทียบกับไม้ของระบบ → คัดสิ่งที่ดี (ช่วงเวลา/ทิศทาง/ขนาด) เก็บเป็นงานวิจัยให้ทุกชั้นอ่าน
  4) เขียนสรุปลง work/research_notes/human_cotrading_behavior.md (อัปเดตทุกครั้งที่รัน)

ไม่ใช้ AI · $0 · อ่านเท่านั้น (ไม่แตะไม้ของใคร)
"""
import io
import json
import os
import datetime as dt
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.dirname(os.path.dirname(ROOT))          # ...\เทรดทองคำ
AUD = os.path.join(PROJ, "work", "auto_trader_audit.jsonl")
NOTE = os.path.join(PROJ, "work", "research_notes", "human_cotrading_behavior.md")
TH = dt.timezone(dt.timedelta(hours=7))
HOURS = 168          # 7 วัน

SYS_EVENTS = ("order_result", "position_closed", "mgmt_verdict", "profit_exit_result",
              "profit_exit_hold", "same_direction_cut_loss_evaluation", "close_ticker",
              "position_close_confirmed", "position_protection")
EXT_HINT = ("orphan", "external", "manual", "unknown_position")


def collect():
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=HOURS)
    sys_tickets, ext_tickets, prot, hours, sides, closed = set(), {}, [], collections.Counter(), {}, {}
    for ln in io.open(AUD, encoding="utf-8", errors="replace"):
        if '"ticket"' not in ln and '"position_id"' not in ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:
            continue
        try:
            t = dt.datetime.fromisoformat(d["time"].replace("Z", "+00:00"))
        except Exception:
            continue
        ev = d.get("event", "")
        tk = d.get("ticket") or d.get("position_id")
        if isinstance(tk, (int, str)) and str(tk).isdigit():
            tk = int(tk)
            if ev in SYS_EVENTS:
                sys_tickets.add(tk)
            if any(h in ev for h in EXT_HINT):
                ext_tickets[tk] = ext_tickets.get(tk, {})
                ext_tickets[tk].update({"t": t, "side": d.get("side") or d.get("position_side")})
        if ev == "position_protection":
            prot.append(d)
            h = t.astimezone(TH).hour
            hours[h] += 1
            sides[str(d.get("side"))] = sides.get(str(d.get("side")), 0) + 1
        if ev == "position_closed" and t >= cutoff:
            closed[tk] = {"net": d.get("net"), "side": d.get("side"), "strategy": d.get("strategy")}
    human = {k: v for k, v in ext_tickets.items() if k not in sys_tickets}
    return sys_tickets, human, prot, hours, sides, closed


def main():
    sys_tk, human, prot, hours, sides, closed = collect()
    lines = []
    lines.append("# งานวิจัย: พฤติกรรมการเทรดของมนุษย์ที่เทรดร่วม (อัปเดตอัตโนมัติ)")
    lines.append("")
    lines.append("_ไฟล์นี้เขียนโดย `tools/human_behavior_research.py` · รันซ้ำได้ทุกเมื่อ · ไม่ใช้ AI_")
    lines.append("")
    lines.append("## 1) สรุปข้อมูลที่มีตอนนี้")
    lines.append("- ไม้ที่ระบบเปิดเอง: **%d ไม้**" % len(sys_tk))
    lines.append("- ไม้ที่มนุษย์เทรดร่วม (ticket ที่ระบบไม่ได้เปิด): **%d ไม้**" % len(human))
    lines.append("- ไม้ที่ระบบต้อง **ใส่ TP/SL ให้** (ตอนตรวจพบว่าไม่มี): **%d ครั้ง**" % len(prot))
    lines.append("")
    if prot:
        lines.append("## 2) ไม้ของมนุษย์ที่ไม่มี TP/SL → ระบบใส่ให้แล้ว")
        lines.append("| เวลา | ทิศ | ราคาเข้า | ราคาตอนใส่ | SL ที่ใส่ | TP ที่ใส่ | ATR |")
        lines.append("|---|---|---|---|---|---|---|")
        for d in prot[-25:]:
            tt = dt.datetime.fromisoformat(d["time"].replace("Z", "+00:00")).astimezone(TH)
            lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                tt.strftime("%d %H:%M"), d.get("side"), d.get("entry"), d.get("current"),
                d.get("sl"), d.get("tp"), d.get("atr")))
        lines.append("")
        lines.append("### ช่วงเวลาที่มนุษย์กดเทรดเอง (ชั่วโมงไทย)")
        for h, n in sorted(hours.items()):
            lines.append("- %02d:00 น. → %d ครั้ง" % (h, n))
        lines.append("")
        lines.append("### ทิศทางที่มนุษย์เลือก")
        for s, n in sides.items():
            lines.append("- %s → %d ครั้ง" % (s, n))
        lines.append("")
    else:
        lines.append("## 2) ยังไม่มีไม้ของมนุษย์ที่ตรวจพบ")
        lines.append("ระบบจะเริ่มบันทึกทันทีที่มีไม้จากภายนอก (มนุษย์กดเทรดร่วม) และไม้ที่ไม่มี TP/SL")
        lines.append("จะถูกใส่ TP/SL ให้อัตโนมัติ **ทุกครั้งที่เช็คเทรด** แล้วบันทึกไว้ที่นี่")
        lines.append("")
    lines.append("## 3) สิ่งที่ต้องเรียนรู้/ปรับ (เกณฑ์ที่ตั้งไว้)")
    lines.append("1. **ช่วงเวลาที่มนุษย์ได้เปรียบ** — ถ้ามนุษย์เทรดช่วงเวลาใดได้ผลดีกว่าระบบ → เพิ่มน้ำหนักช่วงนั้น")
    lines.append("2. **ทิศทางที่มนุษย์เลือก** — ถ้ามนุษย์เลือกฝั่งตรงข้ามกับระบบบ่อยและได้กำไร → ระบบต้องทบทวนการอ่านทิศทาง")
    lines.append("3. **วินัย TP/SL** — ไม้ของมนุษย์ที่ไม่มี TP/SL คือความเสี่ยงเปิด → ระบบใส่ให้แล้ว (กันขาดทุนไม่จำกัด)")
    lines.append("4. **คัดเฉพาะสิ่งที่ดี** — ต้องมีหลักฐาน ≥12 ไม้ก่อนปรับค่าระบบ (กติกาเดิมของระบบ)")
    lines.append("5. **เป้าหมายสูงสุด = กำไร** — ทุกการปรับต้องวัดด้วยตัวเลขจริงก่อน-หลัง ไม่ใช่ความรู้สึก")
    lines.append("")
    lines.append("---")
    lines.append("_เวลาที่สร้าง: %s_" % dt.datetime.now(TH).strftime("%Y-%m-%d %H:%M"))
    body = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(NOTE), exist_ok=True)
    io.open(NOTE, "w", encoding="utf-8").write(body)
    print("  ✓ เขียนงานวิจัย: %s (%.1f KB)" % (NOTE, os.path.getsize(NOTE) / 1024.0))
    print("    ไม้ระบบ %d · ไม้มนุษย์ %d · ไม้ที่ใส่ TP/SL ให้ %d" % (len(sys_tk), len(human), len(prot)))


if __name__ == "__main__":
    main()