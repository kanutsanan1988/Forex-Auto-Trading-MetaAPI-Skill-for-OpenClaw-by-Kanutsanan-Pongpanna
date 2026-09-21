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
"""Auto-Threshold Mode C v2 (ฉลาดจริง) — ปรับ 36 ค่า แยกอิสระต่อ strategy_side

หลักการ "ฉลาดจริง" (NET-PROFIT FIRST — winrate ≠ net profit):
  1. ปรับ ONLY ตัวที่ต้องปรับ: ตัวที่ current gate ยังอยู่ใน band ที่ข้อมูลแนะนำ → ข้าม (ไม่ขยับ)
  2. หลักฐานขั้นต่ำ: samples >= min_samples (default 30) ถึงจะคิด
  3. ขยับเฉพาะเมื่อ deviation >= deadband (0.02) — ไม่จิ้มจุ้มแกว่ง
  4. churn guard รายตัว: แต่ละ key มี last_update_ts ของตัวเอง (ไม่ใช้ค่าเดี่ยวทั้งระบบ)
  5. performance-aware ด้วย NET EXPECTANCY (USD/trade หลัง spread/commission) เป็นแกนหลัก:
     - net เฉลี่ย < 0 → ยก low ขึ้น (กรองสัญญาณที่ทำให้ขาดทุนจริง)
     - net เฉลี่ย > เป้า → ลด low ลง (เปิดรับสัญญาณที่ทำกำไรจริง)
     - winrate ใช้เป็น "ข้อมูลรายงาน" เท่านั้น — เพราะ winrate สูงแต่ R:R แย่ก็ขาดทุนได้
  6. FREQUENCY FLOOR: ห้ามกลไกปรับค่า "ปิดกั้นการเทรด" — ถ้าเงียบไม่มีออเดอร์นาน
     → ผ่อน band หนึ่งขั้น (freq_relax_hours); ถ้าออเดอร์รวมน้อย → ห้าม tighten
  7. ทุกการปรับ เขียน audit log + {key, from, to, reason} — โปร่งใส ตรวจย้อนได้
"""
import os, json, datetime

try:  # ตลาดเปิด/ปิด — ใช้ตัดสิน 'ความถี่ขั้นต่ำ' ไม่ให้นับช่วงตลาดปิด
    from market_clock import market_open as _market_open
except Exception:  # pragma: no cover - ถ้า import ไม่ได้ จะไม่ผ่อนประตู (ปลอดภัยกว่า)
    def _market_open(_t=None):
        return False

try:  # เขียนไฟล์แบบ atomic (temp + fsync + os.replace) — กัน config ถูกตัดครึ่ง
    from runtime_support import atomic_json as _atomic_json
except Exception:  # pragma: no cover
    _atomic_json = None


def _market_open_safe(ts):
    """ตรวจตลาดเปิดแบบปลอดภัย: ถ้า import ไม่ได้ ให้ถือว่า 'ปิด' (ไม่ผ่อนประตูจากข้อมูลไม่ครบ)"""
    try:
        return _market_open(ts)
    except Exception:
        return False


_RECENT_CACHE = {}


def _load_recent_audit(path, max_records=4000):
    """อ่านท้ายไฟล์ audit (สำหรับวัดอัตราความถี่ — ต้องกว้างกว่าหน้าต่าง band ปกติ)

    มีแคชตาม (path, mtime, size) เพราะตัวปรับถูกเรียกทุก 1-3 นาที
    และการอ่าน 4,000 บรรทัดซ้ำ ๆ ทุกครั้งไม่จำเป็น
    """
    try:
        st = os.stat(path)
        key = (str(path), st.st_mtime_ns, st.st_size, max_records)
    except Exception:
        key = None
    if key is not None and key in _RECENT_CACHE:
        return _RECENT_CACHE[key]
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()[-max_records:]
        for line in lines:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    if key is not None:
        _RECENT_CACHE.clear()
        _RECENT_CACHE[key] = out
    return out


def _active_open_hours(rows, end_ts, window_h, step_min=15):
    """ชั่วโมงที่ 'ระบบเทรดรันอยู่ + ตลาดเปิด' ในหน้าต่างย้อนหลัง window_h ชั่วโมง

    นับจากเหตุการณ์ started/stopped ใน audit — จำเป็นเพราะถ้านับเวลาปฏิทินเฉย ๆ
    ช่วงสุดสัปดาห์/ช่วงที่ระบบปิด จะถูกตีความว่า 'ประตูตัน' ทั้งที่ไม่ใช่
    """
    from datetime import datetime as _dt2, timedelta as _td
    try:
        end = _dt2.fromisoformat(str(end_ts))
    except Exception:
        return 0.0
    start = end - _td(hours=window_h)
    life = []
    for d in rows:
        ev = d.get("event")
        if ev in ("started", "stopped"):
            try:
                life.append((_dt2.fromisoformat(str(d.get("time", ""))), ev == "started"))
            except Exception:
                continue
    if not life:
        return 0.0
    life.sort(key=lambda x: x[0])
    hours = 0.0
    step = _td(minutes=step_min)
    t = start
    while t < end:
        # ค่าเริ่มต้น = "รันอยู่" เพราะตัวปรับนี้ถูกเรียกจากตัวเทรดเอง
        # (ถ้าไม่มีเหตุการณ์ started ก่อนหน้าต่าง แปลว่ามันรันมาต่อเนื่อง ไม่ใช่ปิดอยู่)
        running = True
        for ts, on in life:
            if ts <= t:
                running = on
            else:
                break
        if running and _market_open_safe(t):
            hours += step_min / 60.0
        t += step
    return hours


def _orders_in_window(rows, end_ts, window_h):
    """จำนวนออเดอร์ที่ส่งสำเร็จในช่วง window_h ชั่วโมงล่าสุด"""
    from datetime import datetime as _dt2, timedelta as _td
    try:
        end = _dt2.fromisoformat(str(end_ts))
    except Exception:
        return 0
    start = end - _td(hours=window_h)
    n = 0
    for d in rows:
        if d.get("event") != "order_result" or not d.get("ok"):
            continue
        try:
            if start <= _dt2.fromisoformat(str(d.get("time", ""))) <= end:
                n += 1
        except Exception:
            continue
    return n


def find_project_dir():
    """หาโฟลเดอร์โปรเจกต์

    ★ 19 ก.ย. 2026: เดิม hardcode path โฟลเดอร์โปรเจกต์ไว้ในโค้ด
      ทำให้ย้ายเครื่อง/ย้ายโฟลเดอร์แล้วพัง · ตอนนี้ใช้ runtime_support.project_root()
      (คำนวณจากตำแหน่งไฟล์จริง) และค่อย fallback ไปที่ path เดิมถ้าหาไม่ได้
    """
    try:
        from runtime_support import project_root as _project_root
        _p = _project_root()
        if _p and os.path.isdir(os.path.join(str(_p), "outputs", "mt5_python_bridge")):
            return str(_p)
    except Exception:
        pass
    # Fallback แบบพกพา: ค้นจากโฟลเดอร์แม่ของไฟล์นี้ขึ้นไป (ไม่ผูกกับไดรฟ์/โฟลเดอร์ของผู้สร้าง)
    # เดิมโค้ดนี้ชี้ path ตายตัวของผู้สร้าง ทำให้ย้ายเครื่องแล้วหาโปรเจกต์ไม่เจอ
    here = os.path.dirname(os.path.abspath(__file__))
    node = here
    for _ in range(6):
        node = os.path.dirname(node)
        if not node or node == os.path.dirname(node):
            break
        for d in (node, os.path.dirname(node)):
            if d and os.path.exists(os.path.join(d, "outputs", "mt5_python_bridge")):
                return d
    return None

STRAT_SIDES = [
    ("trend","buy"), ("trend","sell"),
    ("range","buy"), ("range","sell"),
    ("mean_reversion","buy"), ("mean_reversion","sell"),
    ("counter_trend","buy"), ("counter_trend","sell"),
    ("breakout","buy"), ("breakout","sell"),
    ("breakout_reversal","buy"), ("breakout_reversal","sell"),
]
ALL_KEYS = [f"{s}_{sd}" for s, sd in STRAT_SIDES]

def now_ts():
    return datetime.datetime.now(datetime.timezone.utc).timestamp()

L_DIR = None


def set_project_dir(path):
    global L_DIR
    L_DIR = path


def apply_auto_threshold_side(config, state=None, audit_path=None, audit_fn=None, net_by_key=None,
                              persist=True):
    """Returns updated config with per-side threshold tuning (only where evidence says so).

    net_by_key: optional {strategy_side: net expectancy USD/trade} — ให้รอบวิจัย (10 นาที)
    ป้อน net จริงต่อ strategy-side ได้ เพราะ audit ของ position_closed ไม่มี strategy/side
    (กลายเป็น 'unknown') ทำให้ blend แบบ net-first ในเครื่องยนต์ไม่เคยมีข้อมูล
    """
    at = (config.get("strategy_router") or {}).get("auto_threshold") or {}
    if not at.get("enabled", False):
        return config
    window = int(at.get("window_records", 1000))
    min_samples = int(at.get("min_samples_per_strategy", 30))
    deadband = float(at.get("min_change_to_apply", 0.02))
    churn_guard = float(at.get("churn_guard_seconds", 3600))
    min_close_for_perf = int(at.get("min_closed_for_performance", 8))
    # หมายเหตุ: คีย์ low_winrate_floor/high_winrate_floor เลิกใช้แล้ว (ใช้ net expectancy เป็นแกนตัดสิน)
    low_netexp_floor = float(at.get("low_netexp_floor", 0.0))    # net exp/trade < 0 → กรองเข้ม
    high_netexp_floor = float(at.get("high_netexp_floor", 0.02)) # net exp/trade > $0.02 → ผ่อนรับ

    proj = find_project_dir()
    global L_DIR
    L_DIR = os.path.join(proj, "outputs", "mt5_python_bridge")
    audit = audit_path or os.path.join(proj, "work", "auto_trader_audit.jsonl")
    # ★ อ่านเฉพาะท้ายไฟล์ (แก้ 19 ก.ย. 2026): เดิมอ่านทั้งไฟล์ (86.9 MB) ใช้เวลา ~8 วินาที
    #   ต่อการเรียก 1 ครั้ง และตัวปรับถูกเรียกทุก 1-3 นาที → เปลืองทั้ง CPU และเวลารอบเทรด
    #   ใช้ _load_recent_audit ที่อ่านท้ายไฟล์ + มีแคชตาม mtime/size → เร็วขึ้นมาก
    need = max(200, window)
    _raw = _load_recent_audit(audit, max(4000, need * 4))
    # ★ หน้าต่างเรียนรู้ (แก้ 19 ก.ย. 2026): เดิมนับ "180 records" ดิบ ๆ ซึ่งช่วงที่ audit
    #   มีแต่เหตุการณ์ noise (recommendation_retest_skipped / market_closed) หน้าต่างจะสั้นมาก
    #   จนตัวปรับแทบไม่มีตัวอย่าง → ตอนนี้เลือกเฉพาะ records ที่มีข้อมูลที่ตัวปรับใช้จริง
    #   (มี analysis · position_closed · order_result) แล้วจึงค่อยตัดเหลือ `need` รายการ
    _useful = [d for d in _raw
               if (d.get("analysis") or d.get("event") in ("position_closed", "order_result"))]
    rows = (_useful if len(_useful) >= need else _raw)[-need:]

    # --- aggregate per strategy_side ---
    raw_s = {k: [] for k in ALL_KEYS}
    win_s = {k: [] for k in ALL_KEYS}   # legacy (r_multiple/net) — ใช้เฉพาะรายงาน
    net_s = {k: [] for k in ALL_KEYS}   # ★ แกนหลัก: net USD ต่อ trade (หลัง spread/commission)
    prob_s = {k: [] for k in ALL_KEYS}  # ★ ความน่าจะเป็นจริงต่อคีย์ (สำหรับตั้งประตูตามตลาด)
    for d in rows:
        a = d.get("analysis") or {}
        rd = a.get("router_decision") or {}
        rs = rd.get("regime_scores") or {}
        for k in ALL_KEYS:
            v = rs.get(k)
            if isinstance(v, (int, float)) and v > 0:
                raw_s[k].append(float(v))
        for _g in (rd.get("bounded_live_diagnostics") or []):
            _kk = f"{_g.get('strategy')}_{_g.get('side')}"
            _pv = _g.get("probability")
            if _kk in prob_s and isinstance(_pv, (int, float)) and _pv > 0:
                prob_s[_kk].append(float(_pv))
        if d.get("event") == "position_closed":
            k = f"{d.get('strategy')}_{d.get('side')}"
            r = d.get("r_multiple")
            net = d.get("net")
            if k in win_s and (r is not None or net is not None):
                win_s[k].append(float(r if r is not None else net))
            if k in net_s and net is not None:
                net_s[k].append(float(net))

    # ── net จากรอบวิจัย (10 นาที): {strategy_side: {"mean": x, "n": k}} ──
    # ใช้เมื่อ audit position_closed ไม่มี strategy/side (กลายเป็น 'unknown') ทำให้ blend ไม่มีข้อมูล
    if net_by_key:
        for k, v in net_by_key.items():
            if k not in net_s:
                continue
            if isinstance(v, dict) and isinstance(v.get("mean"), (int, float)):
                n = int(v.get("n") or 0)
                if n > 0:
                    net_s[k] = [float(v["mean"])] * n
            elif isinstance(v, (int, float)):
                net_s[k] = [float(v)] * max(min_close_for_perf, 1)

    cfg = json.loads(json.dumps(config))
    gov = cfg["strategy_router"]["bounded_live"]["governance"]
    touches = at.setdefault("_touches", {})  # per-key last update ts (เก็บใน auto_threshold — ห้ามเก็บใน governance ไม่งั้น validator crash)
    changed = []

    # pass-rate ต่อ key (สัดส่วนสัญญาณที่ผ่าน band ปัจจุบัน) — ใช้ใน band health monitor
    pass_s = {k: [] for k in ALL_KEYS}
    for k in ALL_KEYS:
        strat, side = k.rsplit("_", 1)
        g = gov.get(strat, {})
        lo_k = float(g.get(f"raw_{side}", g.get("raw", 0.0)) or 0.0)
        hi_k = float(g.get(f"raw_max_{side}", g.get("raw_max", 1.0)) or 1.0)
        for v in raw_s[k]:
            pass_s[k].append(1.0 if (lo_k <= v <= hi_k) else 0.0)

    for k in ALL_KEYS:
        strat, side = k.rsplit("_", 1)
        g = gov.get(strat, {})
        vals = raw_s[k]
        if len(vals) < min_samples:
            continue  # ข้อมูลไม่พอ → ไม่ยุ่ง (ฉลาด: อย่าเดาจากเสี้ยวข้อมูล)
        v = sorted(vals)
        pl = lambda q: v[min(len(v)-1, int(q*(len(v)-1)))]
        suggested_low = pl(0.60)
        suggested_high = pl(0.90)
        # performance blend (5) — ★ NET-PROFIT FIRST (winrate ≠ net profit)
        # ใช้ net expectancy ต่อ trade ตัดสิน: net<0 → กรองเข้ม; net>เป้า → ผ่อนรับ
        # (winrate เก็บไว้รายงานเท่านั้น — สูงแต่ R:R แย่ก็ขาดทุนได้)
        nets = net_s[k]
        net_exp = None
        wr_note = ""
        if len(nets) >= min_close_for_perf:
            net_exp = sum(nets) / len(nets)
            wr = sum(1 for x in nets if x > 0) / len(nets)
            wr_note = f" | netexp=${net_exp:.3f}/trade wr={wr:.2f} n={len(nets)}"
            if net_exp < low_netexp_floor:
                suggested_low = min(1.0, suggested_low + 0.05)   # ขาดทุนเฉลี่ย → กรองเข้ม
            elif net_exp > high_netexp_floor:
                suggested_low = max(0.05, suggested_low - 0.03)  # กำไรเฉลี่ยดี → ผ่อนรับ
        # High-zone (reversal) check — ใช้ net เป็นแกน: ถ้าโซนนี้ขาดทุนเฉลี่ย
        # สัญญาณแรงสุดมีโอกาสกลับด้าน → ลด high (กันเข้าซื้อ/ขายยอดคลื่น)
        if net_exp is not None and net_exp < low_netexp_floor and suggested_high > 0.5:
            suggested_high = max(suggested_low + 0.02, suggested_high - 0.04)
        suggested_high = max(suggested_low + 0.02, min(1.0, suggested_high))

        # ── probability band (ส่วนหนึ่งของ 36 ค่า): net-first ก้าวเล็ก ±0.01 ──
        prob_cur = float(g.get(f"probability_{side}", g.get("probability", 0.55)))
        # ★ ประตูความน่าจะเป็น "ตามค่าจริงของตลาด" (เจ้าของระบบ 15 ก.ย. 2026)
        #   เดิมก้าว ±0.01 จาก net → ช้ามาก และค้างสูงกว่าค่าจริงจนประตูปิด (ไม่มีเทรด)
        #   ใหม่: ใช้ p25 ของค่าจริงล่าสุด → ประมาณ 75% ของสัญญาณผ่านประตูนี้
        prob_new = prob_cur
        _pv = sorted(prob_s.get(k) or [])
        if len(_pv) >= 20:
            prob_new = round(min(0.90, max(0.50, _pv[int(0.25 * (len(_pv) - 1))])), 3)
            _step = float(at.get("max_step", 0.06) or 0.06)
            prob_new = round(max(prob_cur - _step, min(prob_cur + _step, prob_new)), 3)
        prob_moved = abs(prob_new - prob_cur) >= 0.005

        # current per-side gates (fall back to strategy-level)
        cur_low = float(g.get(f"raw_{side}", g.get("raw", 1.0)))
        cur_high = float(g.get(f"raw_max_{side}", g.get("raw_max", 1.0)))
        # ปรับได้เมื่อมี band ต่อฝั่งครบ "หรือ" มี band กลาง (raw/raw_max) ให้ fallback
        # (เดิมบังคับ per-side เท่านั้น → counter_trend/breakout_reversal ปรับไม่ได้เลย)
        both_set = (f"raw_{side}" in g and f"raw_max_{side}" in g) or ("raw" in g and "raw_max" in g)

        # ★ STEP CAP: ปรับได้ไม่เกิน max_step ต่อรอบ/ฝั่ง — ค่อย ๆ ปรับเข้าหาเป้า
        #   กันค่ากระชาก (เช่น low 0.52 → 0.24 ในรอบเดียว) ซึ่งเสี่ยงต่อการเทรดจริง
        max_step = float(at.get("max_step", 0.06) or 0.06)
        suggested_low = max(cur_low - max_step, min(cur_low + max_step, suggested_low))
        suggested_high = max(float(cur_high) - max_step, min(float(cur_high) + max_step, suggested_high))
        suggested_high = max(suggested_low + 0.02, min(1.0, suggested_high))

        # churn guard (per key, shared for both bands of this side)
        last = float(touches.get(k, 0.0) or 0.0)
        if now_ts() - last < churn_guard:
            continue

        reason = f"percentile p60/p90 n={len(vals)}"
        reason += wr_note  # net expectancy + winrate (ข้อมูลรายงาน)

        # ---- INDEPENDENT band tuning ----
        # It is fine (and intended) for ONLY ONE band to move: low reflects
        # signal-quality percentile + win-rate floor; high reflects
        # reversal/extreme risk (p90 zone outcomes).  They are decoupled.
        low_moved = both_set and abs(suggested_low - cur_low) >= deadband
        high_moved = both_set and abs(suggested_high - float(cur_high)) >= deadband
        if not low_moved and not high_moved and not prob_moved:
            continue  # ไม่มีอะไรต้องขยับ

        entry = {"key": k, "reason": reason}
        if low_moved:
            g[f"raw_{side}"] = round(suggested_low, 3)
            g[f"weighted_{side}"] = round(suggested_low, 3)
            entry["from_low"] = cur_low
            entry["to_low"] = round(suggested_low, 3)
        if high_moved:
            g[f"raw_max_{side}"] = round(suggested_high, 3)
            g[f"weighted_max_{side}"] = round(suggested_high, 3)
            entry["from_high"] = float(cur_high)
            entry["to_high"] = round(suggested_high, 3)
        # HARD INVARIANT (user rule): band must always satisfy low <= high.
        # If only one band moved and it would cross the other, pull it back to
        # keep a minimum 0.02 spread instead of letting low exceed high.
        lo = float(g.get(f"raw_{side}", 0.0))
        hi = float(g.get(f"raw_max_{side}", 1.0))
        if lo > hi - 0.02:
            if low_moved and not high_moved:
                lo = hi - 0.02
            else:
                hi = lo + 0.02
            g[f"raw_{side}"] = round(lo, 3)
            g[f"raw_max_{side}"] = round(hi, 3)
            entry["band_clamped"] = True
        if prob_moved:
            g[f"probability_{side}"] = prob_new
            entry["from_probability"] = prob_cur
            entry["to_probability"] = prob_new
        g["weighted_" + side] = g[f"raw_{side}"]
        g[f"weighted_max_{side}"] = g[f"raw_max_{side}"]
        gov[strat] = g
        touches[k] = now_ts()
        changed.append(entry)

    # ============ BAND HEALTH MONITOR (กัน lockout / แน่น-หลวมเกินไป) ============
    # 1) LOCKOUT: ออเดอร์ 0 ใน lockout_hours (ตลาดเปิด) + มี analysis → ผ่อน band ทุกตัว
    # 2) TOO TIGHT: band กว้าง < min_width → ขยายออก (ให้เทรดдได้)
    # 3) TOO TIGHT by pass%: pass น้อยมาก (< min_pass_rate) ทั้งที่ samples พอ → ลด low
    # 4) TOO LOOSE by winrate: เทรดเยอะแต่ win-rate ต่ำ → ยก low ขึ้น / ลด high (กรองสัญญาณแย่)
    health = at.get("band_health", {})
    lockout_hours = float(health.get("lockout_hours", 24.0))
    min_width = float(health.get("min_band_width", 0.04))
    min_pass_rate = float(health.get("min_pass_rate", 0.01))
    relax_step = float(health.get("relax_step", 0.02))
    tighten_step = float(health.get("tighten_step", 0.03))
    min_closed_for_loose = int(health.get("min_closed_for_loose", 8))
    # ★ ความถี่ขั้นต่ำ (บังคับใช้จริงตั้งแต่ 19 ก.ย. 2026 — เจ้าของระบบอนุมัติ)
    #   วัดอัตราไม้/วันจากช่วง "ระบบรัน + ตลาดเปิด" เท่านั้น (ไม่นับสุดสัปดาห์/ช่วงระบบปิด)
    #   ต่ำกว่าขั้นต่ำ → ผ่อน band หนึ่งขั้น แต่มีเพดานกันผ่อนเกิน (freq_floor_*)
    min_orders_per_day = float(health.get("min_orders_per_day", 2.0))    # อัตราขั้นต่ำ (ไม้/วัน)
    loose_min_orders = float(health.get("loose_min_orders", 5.0))        # เทรดน้อย → ห้าม tighten
    floor_window_h = float(health.get("freq_floor_window_hours", 24.0))  # หน้าต่างวัดอัตรา
    floor_min_active_h = float(health.get("freq_floor_min_active_hours", 6.0))  # เวลาจริงขั้นต่ำ
    floor_cooldown_s = float(health.get("freq_floor_cooldown_seconds", 10800.0))  # ผ่อนซ้ำต่อคีย์
    floor_max_width = float(health.get("freq_floor_max_width", 0.45))    # ★ เพดานความกว้าง band
    floor_min_low = float(health.get("freq_floor_min_low", 0.10))        # ★ พื้นต่ำสุดของเกณฑ์

    orders_ok = sum(1 for d in rows if d.get("event") == "order_result" and d.get("ok"))
    first_ts = min((d.get("time","") for d in rows), default="")
    last_ts = max((d.get("time","") for d in rows), default="")
    span_h = 0.0
    if first_ts and last_ts:
        try:
            from datetime import datetime as _dt
            span_h = (_dt.fromisoformat(last_ts) - _dt.fromisoformat(first_ts)).total_seconds()/3600.0
        except Exception:
            span_h = 0.0
    healthy_keys = [k for k in ALL_KEYS if len(raw_s[k]) >= min_samples]

    # baseline: เก็บค่าแรกสุดไว้ใช้ revert — เก็บใน auto_threshold dict (ไม่ใช่
    # governance ซึ่ง validator จำกัดให้มีแค่ 6 strategy keys)
    if "baseline" not in at and healthy_keys:
        at["baseline"] = {k: {"low": float(gov.get(k.rsplit("_",1)[0], {}).get(f"raw_{k.rsplit('_',1)[1]}",
                          gov.get(k.rsplit("_",1)[0], {}).get("raw", 0.5))),
                          "high": float(gov.get(k.rsplit("_",1)[0], {}).get(f"raw_max_{k.rsplit('_',1)[1]}",
                          gov.get(k.rsplit("_",1)[0], {}).get("raw_max", 0.9)))}
                          for k in healthy_keys}

    health_actions = []
    lockout = orders_ok == 0 and span_h >= lockout_hours and len(healthy_keys) > 0
    if lockout:
        bl = at.get("baseline", {})
        for k in healthy_keys:
            strat, side = k.rsplit("_", 1)
            g = gov.get(strat, {})
            b = bl.get(k, {})
            base_low = float(b.get("low", 0.20)) if b else 0.20
            base_high = float(b.get("high", 0.85)) if b else 0.85
            g[f"raw_{side}"] = round(max(0.05, base_low - relax_step), 3)
            g[f"raw_max_{side}"] = round(min(1.0, base_high + relax_step), 3)
            g[f"weighted_{side}"] = g[f"raw_{side}"]
            g[f"weighted_max_{side}"] = g[f"raw_max_{side}"]
            gov[strat] = g
            touches[k] = now_ts()
        health_actions.append({"type": "LOCKOUT_RELAX", "hours": round(span_h,1),
                               "keys": len(healthy_keys), "to_baseline": True})

    # ★ FREQUENCY FLOOR (บังคับใช้จริง): อัตราไม้/วันต้องไม่ต่ำกว่าขั้นต่ำ
    #   เงื่อนไข: ระบบรันอยู่ + ตลาดเปิด รวมกัน >= floor_min_active_h ชั่วโมง ในหน้าต่าง
    #   แล้วอัตรา (ไม้/วัน) ต่ำกว่า min_orders_per_day → ผ่อน band หนึ่งขั้น
    #   เพดานกันผ่อนเกิน: ความกว้าง band ต้องไม่เกิน floor_max_width และเกณฑ์ต่ำสุดต้องไม่ต่ำกว่า floor_min_low
    #   ผ่อนซ้ำต่อคีย์ได้ไม่ถี่กว่า floor_cooldown_s
    freq_relax = False
    # cooldown แยกของกติกาความถี่ — ห้ามใช้ _touches ร่วมกับ band churn guard
    # เพราะการปรับ band อื่นในรอบเดียวกันจะตั้ง _touches ทำให้กติกานี้ถูกบล็อกทุกครั้ง
    freq_touches = at.setdefault("_freq_touches", {})
    if not lockout and len(healthy_keys) > 0:
        recent = _load_recent_audit(audit, 4000)
        active_h = _active_open_hours(recent, last_ts, floor_window_h)
        if active_h >= floor_min_active_h:
            orders_recent = _orders_in_window(recent, last_ts, floor_window_h)
            rate_per_day = orders_recent / (active_h / 24.0)
            if rate_per_day < min_orders_per_day:
                relaxed_keys = 0
                skipped_cap = 0
                for k in healthy_keys:
                    if now_ts() - float(freq_touches.get(k, 0)) < floor_cooldown_s:
                        skipped_cap += 1
                        continue
                    strat, side = k.rsplit("_", 1)
                    g = gov.get(strat, {})
                    lo_f = float(g.get(f"raw_{side}", 0.5))
                    hi_f = float(g.get(f"raw_max_{side}", 0.9))
                    new_lo = max(floor_min_low, lo_f - relax_step)
                    new_hi = min(1.0, hi_f + relax_step)
                    if (new_hi - new_lo) > floor_max_width:
                        skipped_cap += 1
                        continue
                    g[f"raw_{side}"] = round(new_lo, 3)
                    g[f"raw_max_{side}"] = round(new_hi, 3)
                    g["weighted_" + side] = g[f"raw_{side}"]
                    g[f"weighted_max_{side}"] = g[f"raw_max_{side}"]
                    freq_touches[k] = now_ts()
                    relaxed_keys += 1
                if relaxed_keys:
                    freq_relax = True
                    health_actions.append({"type": "FREQ_FLOOR_RELAX",
                                           "rate_per_day": round(rate_per_day, 3),
                                           "floor": min_orders_per_day,
                                           "orders": orders_recent,
                                           "active_hours": round(active_h, 1),
                                           "keys": relaxed_keys,
                                           "capped": skipped_cap,
                                           "step": relax_step})

    if not lockout and not freq_relax:
        for k in healthy_keys:
            strat, side = k.rsplit("_", 1)
            g = gov.get(strat, {})
            lo = float(g.get(f"raw_{side}", g.get("raw", 0.5)))
            hi = float(g.get(f"raw_max_{side}", g.get("raw_max", 0.9)))
            width = hi - lo
            # TOO TIGHT by width -> widen
            if width < min_width:
                g[f"raw_{side}"] = round(max(0.05, lo - relax_step), 3)
                g[f"raw_max_{side}"] = round(min(1.0, hi + relax_step), 3)
                g["weighted_" + side] = g[f"raw_{side}"]
                g[f"weighted_max_{side}"] = g[f"raw_max_{side}"]
                touches[k] = now_ts()
                health_actions.append({"type": "TIGHT_WIDEN", "key": k, "width": round(width,3)})
            # TOO TIGHT by pass rate
            pass_frac = (sum(pass_s[k]) / len(pass_s[k])) if pass_s[k] else 0.0
            if len(raw_s[k]) >= min_samples and 0.0 < pass_frac < min_pass_rate:
                g[f"raw_{side}"] = round(max(0.05, lo - relax_step), 3)
                g[f"raw_max_{side}"] = round(min(1.0, hi + relax_step), 3)
                g["weighted_" + side] = g[f"raw_{side}"]
                g[f"weighted_max_{side}"] = g[f"raw_max_{side}"]
                touches[k] = now_ts()
                health_actions.append({"type": "TIGHT_PASSRATE", "key": k, "pass": round(pass_frac,4)})
            # TOO LOOSE by NET (★ winrate ≠ net profit): เทรดเยอะแต่ net เฉลี่ยติดลบ → กรองเข้ม
            # กันปิดกั้นการเทรด: ถ้าจำนวนออเดอร์รวมยังน้อย → ข้าม (อย่า tighten ตอนเทรดน้อย)
            nets_k = net_s[k]
            if len(nets_k) >= min_closed_for_loose:
                net_exp_k = sum(nets_k) / len(nets_k)
                if net_exp_k < low_netexp_floor:
                    if orders_ok < loose_min_orders:
                        health_actions.append({"type": "LOOSE_SKIP_LOW_FREQ", "key": k,
                                               "netexp": round(net_exp_k, 4), "orders": orders_ok})
                    else:
                        g[f"raw_{side}"] = round(min(0.95, lo + tighten_step), 3)
                        g[f"raw_max_{side}"] = round(max(lo + 0.02, hi - tighten_step), 3)
                        g["weighted_" + side] = g[f"raw_{side}"]
                        g[f"weighted_max_{side}"] = g[f"raw_max_{side}"]
                        touches[k] = now_ts()
                        health_actions.append({"type": "LOOSE_TIGHTEN", "key": k,
                                               "netexp": round(net_exp_k, 4), "n": len(nets_k)})

    if health_actions and audit_fn:
        try:
            audit_fn("band_health_actions", actions=health_actions,
                     orders_ok=orders_ok, min_orders_per_day=min_orders_per_day)
        except Exception:
            pass

    # ── ★ weighted band = คำนวณจาก "คะแนน weighted จริง" (ไม่ mirror raw อีกต่อไป) ──
    # เหตุผล (ผู้ใช้ชี้ถูก): weighted = min(1, raw × น้ำหนักกลยุทธ์ × น้ำหนักทิศทาง)
    #   → คนละสเกลกับ raw (วัดจาก audit จริง: อัตราส่วน 0.850–1.150 · เท่ากับ raw เพียง 22.9%)
    #   การตั้ง band ของ weighted = raw จึงเทียบ "คนละหน่วย" → ประตู weighted ตัดสินผิด
    # วิธีที่ถูก: หาเปอร์เซ็นไทล์จาก weighted_score ที่เครื่องยนต์บันทึกไว้จริงใน audit
    #   (router_decision.bounded_live_diagnostics[].weighted_score)
    w_s = {k: [] for k in ALL_KEYS}
    for d in rows:
        rd_w = ((d.get("analysis") or {}).get("router_decision") or {})
        for gt in (rd_w.get("bounded_live_diagnostics") or []):
            k_w = f"{gt.get('strategy')}_{gt.get('side')}"
            v_w = gt.get("weighted_score")
            if k_w in w_s and isinstance(v_w, (int, float)) and v_w > 0:
                w_s[k_w].append(float(v_w))
    for k in ALL_KEYS:
        strat_w, side_w = k.rsplit("_", 1)
        g_w = gov.get(strat_w)
        vals_w = w_s.get(k) or []
        if not isinstance(g_w, dict) or len(vals_w) < min_samples:
            continue                      # หลักฐานไม่พอ → คงค่าเดิม (fallback = ค่า raw เดิม)
        vw = sorted(vals_w)
        plw = lambda q: vw[min(len(vw) - 1, int(q * (len(vw) - 1)))]
        w_lo = max(0.0, min(1.0, plw(0.60)))
        w_hi = max(w_lo + 0.02, min(1.0, plw(0.90)))
        nets_w = net_s.get(k) or []
        if len(nets_w) >= min_close_for_perf:
            net_exp_w = sum(nets_w) / len(nets_w)
            if net_exp_w < low_netexp_floor:
                w_lo = min(1.0, w_lo + 0.05)          # ขาดทุนเฉลี่ย → กรองเข้ม
            elif net_exp_w > high_netexp_floor:
                w_lo = max(0.05, w_lo - 0.03)         # กำไรเฉลี่ยดี → ผ่อนรับ
        # ★ ความกว้างขั้นต่ำ: กัน band แคบจนไม่มีสัญญาณผ่านเลย (บทเรียน 14 ก.ย.: band แคบ 0.02 → ระบบหยุดเทรด)
        _min_w = float(at.get("min_weighted_band_width", 0.06) or 0.06)
        w_hi = max(w_lo + 0.02, w_hi, w_lo + _min_w)
        # ★ เคารพ churn guard + เกณฑ์การเปลี่ยนขั้นต่ำ
        #   (เดิมบล็อกนี้เขียนใหม่ทุก cycle → band ไล่แคบลงเรื่อย ๆ จนระบบตัน)
        _guard = float(at.get("churn_guard_seconds", 0) or 0)
        _min_change = float(at.get("min_change_to_apply", 0.02) or 0.02)
        _old_lo = float(g_w.get(f"weighted_{side_w}") or 0.0)
        _old_hi = float(g_w.get(f"weighted_max_{side_w}") or 0.0)
        if _guard > 0 and (now_ts() - float(touches.get(k) or 0)) < _guard:
            continue
        if abs(_old_lo - w_lo) < _min_change and abs(_old_hi - w_hi) < _min_change:
            continue
        if (_old_lo != round(w_lo, 3)) or (_old_hi != round(w_hi, 3)):
            g_w[f"weighted_{side_w}"] = round(w_lo, 3)
            g_w[f"weighted_max_{side_w}"] = round(w_hi, 3)
            touches[k] = now_ts()
            changed.append({"key": k, "field": "weighted",
                            "low": round(w_lo, 3), "high": round(w_hi, 3),
                            "n_weighted": len(vw), "n_net": len(nets_w)})

    # ─ ★ ความกว้างขั้นต่ำมาตรฐาน (ข้อกำหนดเจ้าของระบบ 14 ก.ย.: band ทุกจุดต้องไม่แคบกว่านี้) ──
    #    ตัวปรับเส้นทางอื่น ๆ เคยเขียน band แคบลง (เช่น mirror raw) ทำให้ระบบไม่มีสัญญาณผ่านเลย
    #    ด่านนี้คุม "ทั้ง 36 ค่า" หลังจากการปรับทั้งหมด → ขยายให้กว้างขั้นต่ำเสมอ
    _mins = at.get("band_min_widths") or {}
    _min_map = (
        ("raw", float(_mins.get("raw", 0.10) or 0.10)),
        ("probability", float(_mins.get("probability", 0.10) or 0.10)),
        ("weighted", float(_mins.get("weighted", 0.10) or 0.10)),
    )
    for k in ALL_KEYS:
        st_m, side_m = k.rsplit("_", 1)
        g_m = gov.get(st_m)
        if not isinstance(g_m, dict):
            continue
        for fld_m, minw_m in _min_map:
            lo_key = f"{fld_m}_{side_m}"
            hi_key = f"{fld_m}_max_{side_m}"
            lo_m, hi_m = g_m.get(lo_key), g_m.get(hi_key)
            if not isinstance(lo_m, (int, float)) or not isinstance(hi_m, (int, float)):
                continue
            if (float(hi_m) - float(lo_m)) < minw_m - 1e-9:
                new_hi = round(min(1.0, float(lo_m) + minw_m), 3)
                g_m[hi_key] = new_hi
                changed.append({"key": k, "field": fld_m + "_min_width",
                                "low": round(float(lo_m), 3), "high": new_hi, "min_width": minw_m})
                touches[k] = now_ts()

    at["_touches"] = touches
    # เขียน _touches ลง "สำเนา" ที่จะ persist ด้วย (เดิมเขียนแต่ตัวต้นฉบับ → รีสตาร์ทแล้ว churn guard หลุด)
    _cfg_at = cfg.setdefault("strategy_router", {}).setdefault("auto_threshold", {})
    if isinstance(_cfg_at, dict):
        _cfg_at["_touches"] = touches
    if changed and audit_fn:
        try:
            audit_fn("auto_threshold_update", updates=changed)
        except Exception:
            pass
        # ★ แก้ 19 ก.ย. 2026: เทสต์ต้องไม่แตะข้อมูลจริง — persist=False ปิดการเขียนไฟล์
        if not persist:
            return cfg
        # Persist tuned 36 per-side values immediately so they survive
        # process kill / shutdown without any restart ceremony.
        try:
            cfg_path = os.path.join(L_DIR, "auto_config.json")
            # ★ เขียนแบบ "merge": เก็บคีย์ที่ผู้ใช้นอกขอบเขตตัวปรับไว้ (เช่น stage3 · side_net_gate)
            #   เดิมเขียนทับทั้งไฟล์จากสำเนาในหน่วยความจำ → คีย์ที่เพิ่มภายหลังหายทุกครั้งที่รอบปรับทำงาน
            _disk = {}
            try:
                with open(cfg_path, encoding="utf-8") as _fh:
                    _disk = json.load(_fh)
            except Exception:
                _disk = {}
            if isinstance(_disk, dict) and isinstance(_disk.get("strategy_router"), dict):
                merged = dict(_disk)
                merged["strategy_router"] = cfg.get("strategy_router") or _disk["strategy_router"]
                _at_out = merged["strategy_router"].setdefault("auto_threshold", {})
                if isinstance(_at_out, dict):
                    _at_out["_touches"] = cfg.get("strategy_router", {}).get("auto_threshold", {}).get("_touches", {})
                # ★ เขียนแบบ atomic (แก้ 19 ก.ย. 2026): เดิม open(...,"w") ตรง ๆ
                #   ถ้าโปรเซสตายกลางคัน config จะถูกตัดครึ่ง → รอบถัดไปต้องใช้ค่าเดิม
                #   ใช้ runtime_support.atomic_json (temp + fsync + os.replace) ถ้ามี
                if _atomic_json is not None:
                    _atomic_json(cfg_path, merged)
                else:
                    with open(cfg_path, "w", encoding="utf-8") as fh:
                        json.dump(merged, fh, ensure_ascii=False, indent=2)
            else:
                if _atomic_json is not None:
                    _atomic_json(cfg_path, cfg)
                else:
                    with open(cfg_path, "w", encoding="utf-8") as fh:
                        json.dump(cfg, fh, ensure_ascii=False, indent=2)
            audit_fn("auto_threshold_persisted", count=len(changed))
        except Exception as pe:
            try:
                audit_fn("auto_threshold_persist_error", error=str(pe))
            except Exception:
                pass
    return cfg


if __name__ == "__main__":
    proj = find_project_dir()
    L = os.path.join(proj, "outputs", "mt5_python_bridge")
    set_project_dir(L)
    cfg = json.load(open(os.path.join(L, "auto_config.json"), encoding="utf-8"))
    if "auto_threshold" not in cfg.get("strategy_router", {}):
        cfg["strategy_router"]["auto_threshold"] = {
            "enabled": True, "mode": "hybrid", "window_records": 1000,
            "min_samples_per_strategy": 30, "min_change_to_apply": 0.02,
            "churn_guard_seconds": 0, "min_closed_for_performance": 8,
            "low_winrate_floor": 0.40, "high_winrate_floor": 0.55,
            "low_netexp_floor": 0.0, "high_netexp_floor": 0.02,
        }
    out = apply_auto_threshold_side(cfg)
    ch = sum(1 for s,g in out["strategy_router"]["bounded_live"]["governance"].items()
             if any(k.endswith("_buy") or k.endswith("_sell") for k in g))
    print("updated keys:", ch)
    for k in ALL_KEYS:
        strat, side = k.rsplit("_",1)
        g = out["strategy_router"]["bounded_live"]["governance"][strat]
        if f"raw_{side}" in g:
            print(f"  {k}: [{g[f'raw_{side}']},{g[f'raw_max_{side}']}]")
    json.dump(out, open(os.path.join(L, "auto_config.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("saved")