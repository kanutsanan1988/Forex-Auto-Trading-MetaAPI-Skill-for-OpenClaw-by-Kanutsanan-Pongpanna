# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""เทสต์การบังคับใช้ 'ความถี่ขั้นต่ำ' (min_orders_per_day) — 19 ก.ย. 2026

ตรวจ 4 เรื่อง:
  1) นับชั่วโมง 'ระบบรัน + ตลาดเปิด' ถูกต้อง (วันธรรมดา > 0 · สุดสัปดาห์ = 0)
  2) ยิงผ่อน band เมื่ออัตราต่ำกว่าขั้นต่ำจริง (ใช้ audit จำลองที่มีตัวอย่างครบ)
  3) เพดานกันผ่อนเกินทำงาน (ความกว้าง band / เกณฑ์ต่ำสุด)
  4) ไม่ยิงเมื่ออัตราสูงกว่าขั้นต่ำ

ใช้เส้นทางจริงของโค้ด (ไม่ patch ตรรกะภายใน) — patch เฉพาะ 'ตลาดเปิด' ให้ทดสอบได้ตลอด
"""
import copy
import datetime
import io
import json
import os
import sys
import tempfile
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "outputs", "mt5_python_bridge"))

import auto_threshold as at  # noqa: E402

# ★ แก้ 19 ก.ย. 2026: เทสต์ต้องไม่แตะข้อมูลจริง
#   apply_auto_threshold_side() เขียน L_DIR/auto_config.json เพื่อ persist ค่า 36 ตัว
#   → เดิมเทสต์ไม่ได้แยก L_DIR ทำให้ _touches ของ config จริงถูกเขียนทับทุกครั้งที่รันเทสต์
_TMPDIR = tempfile.mkdtemp(prefix="freq_floor_test_")
at.set_project_dir(_TMPDIR)

CFG = os.path.join(ROOT, "outputs", "mt5_python_bridge", "auto_config.json")
REAL_AUDIT = os.path.join(ROOT, "work", "auto_trader_audit.jsonl")
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (" — " + detail if detail else ""))


def load_cfg():
    return json.load(io.open(CFG, encoding="utf-8"))


def gov_of(cfg):
    return cfg["strategy_router"]["bounded_live"].get("governance", {})


def make_fake_audit(path, hours_ago_started=25.0, n_samples=45, n_orders=1):
    """สร้าง audit จำลอง: started 25 ชม.ก่อน + ตัวอย่าง regime_scores ครบ + ออเดอร์ตามต้องการ"""
    now = datetime.datetime.now(datetime.timezone.utc)
    t0 = now - datetime.timedelta(hours=hours_ago_started)
    rows = [{"time": t0.isoformat(), "event": "started", "pid": 12345}]
    keys = [k for k in at.ALL_KEYS]
    for i in range(n_samples):
        t = t0 + datetime.timedelta(minutes=35 * i)
        scores = {k: 0.30 + 0.005 * i for k in keys}
        rows.append({"time": t.isoformat(), "event": "no_trade",
                     "analysis": {"router_decision": {"regime_scores": scores,
                                                      "bounded_live_diagnostics": []}}})
    for i in range(n_orders):
        t = t0 + datetime.timedelta(minutes=35 * i + 5)  # กระจายทั่วหน้าต่าง 26 ชม.
        rows.append({"time": t.isoformat(), "event": "order_result", "ok": True,
                     "strategy": "trend", "side": "buy"})
    with io.open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path


print("=== 1) การนับชั่วโมง 'ระบบรัน + ตลาดเปิด' (audit จริง) ===")
recent = at._load_recent_audit(REAL_AUDIT, 4000)
print("  อ่าน audit จริงได้ " + str(len(recent)) + " records")
# 16 ก.ย. 2026 12:00 UTC = วันพุธ ตลาดเปิด + ระบบรัน (มีข้อมูลเทรดจริงในวันนั้น)
first = datetime.datetime.fromisoformat(str(recent[0].get("time")))
mid = first + datetime.timedelta(hours=24)          # ต้นหน้าต่าง + 24 ชม. = อยู่ในช่วงข้อมูลแน่นอน
sun = datetime.datetime(2026, 9, 13, 12, 0, tzinfo=datetime.timezone.utc)
h_wed = at._active_open_hours(recent, mid.isoformat(), 24.0)
h_sun = at._active_open_hours(recent, sun.isoformat(), 24.0)
print("  ต้นหน้าต่าง+24 ชม. (" + mid.isoformat()[:16] + "): " + str(round(h_wed, 1)) + " ชม. | อาทิตย์: " + str(round(h_sun, 1)) + " ชม.")
check("ช่วงที่ระบบรัน+ตลาดเปิด นับได้ > 0", h_wed > 0, str(round(h_wed, 1)) + " ชม.")
check("สุดสัปดาห์ตลาดปิด นับได้ 0", h_sun == 0.0, str(round(h_sun, 1)) + " ชม.")

print("")
print("=== 2) ยิงผ่อน band เมื่ออัตราต่ำกว่าขั้นต่ำ (audit จำลอง) ===")
tmp = os.path.join(tempfile.gettempdir(), "_freq_floor_test_audit.jsonl")
make_fake_audit(tmp, n_samples=45, n_orders=1)      # 1 ไม้ / ~24 ชม. ตลาดเปิด → 1.0 ไม้/วัน < 2
at._market_open = lambda t=None: True               # ให้ตลาดเปิดตลอดเพื่อทดสอบกติกา
at._RECENT_CACHE.clear()
cfg = load_cfg()
# ★ เคลียร์ cooldown ต่อคีย์ เพื่อให้กติกามีโอกาสยิงในการทดสอบ
cfg["strategy_router"]["auto_threshold"]["_touches"] = {}
cfg["strategy_router"]["auto_threshold"]["_freq_touches"] = {}
gov_before = copy.deepcopy(gov_of(cfg))
actions = []
cfg2 = at.apply_auto_threshold_side(copy.deepcopy(cfg), state=None, audit_path=tmp, persist=False,
                                    audit_fn=lambda ev, **kw: actions.append((ev, kw)))
gov_after = gov_of(cfg2)
types = [a.get("type") for ev, kw in actions if ev == "band_health_actions"
         for a in kw.get("actions", [])]
check("มีเหตุการณ์ FREQ_FLOOR_RELAX", "FREQ_FLOOR_RELAX" in types, str(sorted(set(types))))

relaxed = [f"{s}.{k}" for s in gov_after for k, v in gov_after[s].items()
           if isinstance(v, float) and abs(v - gov_before.get(s, {}).get(k, v)) > 1e-9]
check("ค่าประตูถูกผ่อนจริง", len(relaxed) > 0, str(len(relaxed)) + " ค่า เช่น " + ", ".join(relaxed[:4]))
detail = [kw for ev, kw in actions if ev == "band_health_actions"]
if detail:
    acts = [a for a in detail[0].get("actions", []) if a.get("type") == "FREQ_FLOOR_RELAX"]
    if acts:
        a0 = acts[0]
        print("      อัตราที่วัดได้: " + str(a0.get("rate_per_day")) + " ไม้/วัน (ขั้นต่ำ "
              + str(a0.get("floor")) + ") | เวลาจริง " + str(a0.get("active_hours")) + " ชม. | ผ่อน "
              + str(a0.get("keys")) + " คีย์")

print("")
print("=== 3) เพดานกันผ่อนเกิน ===")
health = cfg["strategy_router"]["auto_threshold"].get("band_health", {})
max_w = float(health.get("freq_floor_max_width", 0.45))
min_lo = float(health.get("freq_floor_min_low", 0.10))
cur = cfg
for i in range(12):
    cur = at.apply_auto_threshold_side(copy.deepcopy(cur), state=None, audit_path=tmp, persist=False,
                                       audit_fn=lambda ev, **kw: None)
    cur["strategy_router"]["auto_threshold"]["_touches"] = {}
    cur["strategy_router"]["auto_threshold"]["_freq_touches"] = {}     # เคลียร์ cooldown เพื่อทดสอบเพดาน
g = gov_of(cur)
worst_w, lowest = 0.0, 1.0
for _strat, gg in g.items():
    for side in ("buy", "sell"):
        lo = gg.get("raw_" + side)
        hi = gg.get("raw_max_" + side)
        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
            worst_w = max(worst_w, hi - lo)
            lowest = min(lowest, lo)
print("  หลังผ่อน 12 รอบ: ความกว้างมากสุด " + str(round(worst_w, 3)) + " | เกณฑ์ต่ำสุด " + str(round(lowest, 3)))
check("ความกว้าง band ไม่เกินเพดาน " + str(max_w), worst_w <= max_w + 1e-6, str(round(worst_w, 3)))
check("เกณฑ์ต่ำสุดไม่ต่ำกว่า " + str(min_lo), lowest >= min_lo - 1e-6, str(round(lowest, 3)))

print("")
print("=== 4) ไม่ยิงเมื่ออัตราสูงกว่าขั้นต่ำ ===")
tmp2 = os.path.join(tempfile.gettempdir(), "_freq_floor_test_audit2.jsonl")
make_fake_audit(tmp2, n_samples=45, n_orders=80)    # 80 ไม้ / ~24 ชม. → 80 ไม้/วัน >> 2
at._RECENT_CACHE.clear()
actions2 = []
cfg["strategy_router"]["auto_threshold"]["_touches"] = {}
cfg["strategy_router"]["auto_threshold"]["_freq_touches"] = {}
at.apply_auto_threshold_side(copy.deepcopy(cfg), state=None, audit_path=tmp2, persist=False,
                             audit_fn=lambda ev, **kw: actions2.append((ev, kw)))
types2 = [a.get("type") for ev, kw in actions2 if ev == "band_health_actions"
          for a in kw.get("actions", [])]
check("ไม่มี FREQ_FLOOR_RELAX เมื่อเทรดถี่พอ", "FREQ_FLOOR_RELAX" not in types2, str(sorted(set(types2))))

for f in (tmp, tmp2):
    try:
        os.remove(f)
    except Exception:
        pass

print("")
print("ผ่าน " + str(len(PASS)) + " · ไม่ผ่าน " + str(len(FAIL)))
if FAIL:
    print("รายการที่ไม่ผ่าน: " + ", ".join(FAIL))
    sys.exit(1)
print("🎉 ผ่านทั้งหมด")

# ★ คืนค่า L_DIR + ลบ temp (ไม่ให้เหลือขยะ)
try:
    at.set_project_dir(os.path.join(ROOT, "outputs", "mt5_python_bridge"))
    shutil.rmtree(_TMPDIR, ignore_errors=True)
except Exception:
    pass

