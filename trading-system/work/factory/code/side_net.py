# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""ประตู net ต่อฝ่าย (side-net gate) — **โมดูลกลางเพียงที่เดียว** (แก้ 19 ก.ย. 2026)

เดิมตรรกะนี้ถูกเขียนซ้ำ 2 ที่:
  • auto_trader.recent_side_nets_timed / side_net_gate   (ใช้ตอนตรวจ risk ก่อนส่งออเดอร์)
  • strategy_engine._side_net_ledger / side_net_deferred_keys (ใช้ตอนด่าน 1 เลือกฝั่ง)
ทั้งคู่ทำสิ่งเดียวกัน (อ่าน work/side_net_ledger.json · align keys/keys_time · กรองอายุ ·
เอา N ไม้ล่าสุด · เทียบผลรวมกับ threshold) แต่ default ต่างกันเล็กน้อย → เสี่ยงเพี้ยนกัน

ที่นี้รวมเป็นชุดเดียว: ทุกที่ที่ต้องใช้ประตูนี้ ต้องเรียกจากโมดูลนี้เท่านั้น
"""
import datetime
import json
import os
import time

DEFAULT_CFG = {
    "enabled": True,
    "lookback_trades": 3,
    "threshold": 0.0,
    "min_samples": 2,
    "max_age_hours": 12,   # ★ ค่าเดียวกับ auto_config.json (เดิมฝั่งหนึ่ง default 24 อีกฝั่งไม่มี)
}

_CACHE = {"t": 0.0, "data": None, "path": None}
CACHE_SECONDS = 20.0


def ledger_path(root: str | None = None) -> str:
    """ตำแหน่งสมุดบัญชี net — work/side_net_ledger.json"""
    if root is None:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "work", "side_net_ledger.json")


def load_ledger(path: str | None = None) -> dict:
    """อ่านสมุดบัญชี net (แคช 20 วินาที) — อ่านไม่ได้ = {} (ประตูไม่ชะลอใคร)"""
    path = path or ledger_path()
    cache = _CACHE
    now = time.time()
    if cache["data"] is not None and now - float(cache["t"] or 0.0) < CACHE_SECONDS and cache["path"] == path:
        return cache["data"]
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    cache.update({"t": now, "data": data, "path": path})
    return data


def _parse_ts(value):
    if not value:
        return None
    try:
        dt = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception:
        return None


def filtered_nets(ledger: dict, key: str, limit: int, max_age_hours: float,
                  now=None) -> list:
    """net ของคีย์ (strategy_side) เอา N ไม้ล่าสุด ที่ปิดภายใน max_age_hours

    max_age_hours = 0 → ไม่จำกัดอายุ (พฤติกรรมเดิม) · ไม้ที่ไม่มีเวลาบันทึก = ถือว่าเก่าเกินไป
    """
    try:
        arr = [float(x) for x in ((ledger.get("keys") or {}).get(key) or [])]
    except Exception:
        return []
    if not arr:
        return []
    ts = list((ledger.get("keys_time") or {}).get(key) or [])[-len(arr):]
    if len(ts) < len(arr):
        ts = [""] * (len(arr) - len(ts)) + ts
    if not max_age_hours or max_age_hours <= 0:
        return arr[-limit:]
    now = now or datetime.datetime.now(datetime.timezone.utc)
    out = []
    for net_v, t in zip(arr, ts):
        dt = _parse_ts(t)
        if dt is None:
            continue
        if (now - dt).total_seconds() <= max_age_hours * 3600.0:
            out.append(net_v)
    return out[-limit:]


def _cfg_of(config: dict) -> dict:
    cfg = (config or {}).get("side_net_gate")
    if not isinstance(cfg, dict):
        cfg = dict(DEFAULT_CFG)
    merged = dict(DEFAULT_CFG)
    merged.update(cfg)
    return merged


def deferred_keys(config: dict, ledger: dict | None = None, now=None) -> dict:
    """→ {key: เหตุผล} ของกลยุทธ์-ทิศทางที่ 'ด่าน 1' ชะลอ (net ล่าสุดติดลบ)

    • หลักฐานไม่ถึง min_samples → ปล่อยผ่าน (ไม่เดาจากเสี้ยวข้อมูล)
    • กลับเป็นบวกเมื่อไร → หลุดรายการทันที (rolling จากไม้ที่ปิดจริง)
    • ปิดประตูทั้งด่าน: config["side_net_gate"]["enabled"] = false
    """
    cfg = _cfg_of(config)
    if not cfg.get("enabled", True):
        return {}
    look = int(cfg.get("lookback_trades", 3) or 3)
    mins = int(cfg.get("min_samples", 2) or 2)
    thr = float(cfg.get("threshold", 0.0) or 0.0)
    max_age_h = float(cfg.get("max_age_hours", DEFAULT_CFG["max_age_hours"]) or 0.0)
    led = ledger if ledger is not None else load_ledger()
    now = now or datetime.datetime.now(datetime.timezone.utc)
    out = {}
    for key in (led.get("keys") or {}):
        nets = filtered_nets(led, key, look, max_age_h, now=now)
        if len(nets) < mins:
            continue
        total = sum(nets)
        if total < thr:
            out[key] = (f"side-net defer: {key} net {total:+.2f} จาก {len(nets)} ไม้ล่าสุด "
                        f"(ภายใน {max_age_h:.0f} ชม.)")
    return out


def gate(config: dict, strategy: str, side: str, ledger: dict | None = None, now=None):
    """→ (ผ่านไหม, เหตุผล) สำหรับกลยุทธ์-ทิศทางเดียว

    ถ้า net ย้อนหลัง N ไม้ของกลยุทธ์-ทิศทางนี้ติดลบ → ยังไม่เข้า (ชะลอ)
    """
    cfg = _cfg_of(config)
    if not cfg.get("enabled", True):
        return True, "side-net gate disabled"
    if not strategy or not side:
        return True, "side-net: no strategy/side"
    look = int(cfg.get("lookback_trades", 3) or 3)
    thr = float(cfg.get("threshold", 0.0) or 0.0)
    mins = int(cfg.get("min_samples", 2) or 2)
    max_age_h = float(cfg.get("max_age_hours", DEFAULT_CFG["max_age_hours"]) or 0.0)
    led = ledger if ledger is not None else load_ledger()
    nets = filtered_nets(led, f"{strategy}_{side}", look, max_age_h, now=now)
    if len(nets) < mins:
        return True, f"side-net: หลักฐานไม่พอ (n={len(nets)})"
    total = sum(nets)
    if total < thr:
        return False, (f"side-net defer: {strategy}_{side} net {total:+.2f} จาก {len(nets)} ไม้ล่าสุด "
                       f"(ภายใน {max_age_h:.0f} ชม.) < {thr}")
    return True, f"side-net ok: {strategy}_{side} net {total:+.2f}"
