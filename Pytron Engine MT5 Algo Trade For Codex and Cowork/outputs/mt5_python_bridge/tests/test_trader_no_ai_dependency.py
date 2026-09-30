# -*- coding: utf-8 -*-
"""ยืนยันถาวร: "ตัวเทรด (LAYER 1) ไม่จำเป็นต้องมี AI" — หลักการเจ้าของระบบ (29 ก.ย. 2026)

ที่มา: เจ้าของระบบย้ำว่า "ตัวเทรดนั้นไม่ต้องมี AI" แต่พบว่าเข้าใจผิดซ้ำ ๆ เพราะในโค้ดตัวเทรดมีชั้น LLM ฝังอยู่
ไฟล์นี้คือด่านกันความเข้าใจผิดแบบถาวร — ถ้ามีใครทำให้ตัวเทรด "จำเป็น" ต้องมี AI เทสต์จะ FAIL ทันที

กติกา 4 ข้อ:
  L1 โมดูลตัดสินใจของตัวเทรด = Python ล้วน — จะอ้างถึงชั้น LLM ได้เฉพาะเมื่ออยู่ใน try/except (เป็นตัวเลือก)
  L2 ต้องพิสูจน์ได้ว่า import โมดูลคอร์สำเร็จ "แม้ไม่มี" โมดูล openrouter_agents (ด่านชี้ขาด)
  L3 เส้นทางส่งคำสั่งจริง (order path) ห้ามอ้างถึง LLM เด็ดขาด
  L4 ค่าโรงงานปิด AI; โหมด 1 ต้องกัน AI (ตาม contract ของโหมด)
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import unittest

BRIDGE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.dirname(os.path.dirname(BRIDGE))

# โมดูลที่ "ตัดสินใจ" ของตัวเทรด — ต้องเป็น Python ล้วน
CORE_MODULES = [
    "strategy_engine.py",
    "side_net.py",
    "auto_threshold.py",
    "live_executor.py",
    "market_analyzer.py",
    "market_clock.py",
    "adaptive_shadow.py",
    "bounded_adaptive_research.py",
]

# โมดูลที่ต้อง import ได้จริงเมื่อบล็อกชั้น LLM (ด่านชี้ขาด L2)
IMPORTABLE_WITHOUT_LLM = ["market_analyzer", "strategy_engine", "side_net", "auto_threshold"]

LLM_MARKERS = [
    r"openrouter_agents",
    r"run_dual_agents",
    r"chat/completions",
    r"api\.openai\.com",
    r"\banthropic\b",
    r"\bOPENROUTER_API_KEY\b",
]


def read(path: str) -> str:
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def code_only(src: str) -> str:
    """ตัดคอมเมนต์/ข้อความ docstring ออก เพื่อไม่ให้ชื่อในคำอธิบายทำให้เทสต์ตก"""
    out, in_doc = [], None
    for line in src.splitlines():
        s = line.strip()
        if in_doc:
            if in_doc in s:
                in_doc = None
            continue
        if s.startswith('"""') or s.startswith("'''"):
            q = s[:3]
            if s.count(q) >= 2 and len(s) > 3:
                continue
            in_doc = q
            continue
        out.append(line.split("#", 1)[0])
    return "\n".join(out)


def func_body(src: str, name: str) -> str:
    m = re.search(r"^def %s\(" % re.escape(name), src, re.M)
    if not m:
        return ""
    nxt = re.search(r"^(def |class )", src[m.end():], re.M)
    return src[m.start(): m.end() + (nxt.start() if nxt else len(src))]


class TestTraderHasNoAiDependency(unittest.TestCase):
    """L1: การอ้างถึงชั้น LLM ในโมดูลคอร์ต้องเป็นแบบ 'ตัวเลือก' (อยู่ใน try/except)"""

    def test_core_modules_llm_reference_is_guarded(self):
        """การอ้างถึงชั้น LLM ในโมดูลคอร์ต้องเป็นแบบ 'ตัวเลือก':
        - ถ้าเป็นบรรทัด import -> ต้องอยู่ใน try/except
        - ถ้าเรียกใช้ run_dual_agents -> ต้องมี fallback (def run_dual_agents) อยู่ในไฟล์
        """
        for name in CORE_MODULES:
            path = os.path.join(BRIDGE, name)
            if not os.path.exists(path):
                continue
            lines = read(path).splitlines()
            text = "\n".join(lines)
            for i, line in enumerate(lines):
                if line.strip().startswith("#"):
                    continue
                if not re.search(r"openrouter_agents|run_dual_agents", line):
                    continue
                is_import = re.match(r"\s*(from\s+\S+\s+import|import)\s", line) is not None
                if is_import:
                    window = "\n".join(lines[max(0, i - 6): i + 8])
                    self.assertIn(
                        "try:", window,
                        "%s บรรทัด %d import ชั้น LLM โดยไม่มี try/except — "
                        "ตัวเทรดต้องไม่ล้มเมื่อไม่มีชั้น LLM" % (name, i + 1),
                    )
                else:
                    self.assertIn(
                        "def run_dual_agents", text,
                        "%s เรียกใช้ run_dual_agents แต่ไม่มี fallback — "
                        "ถ้าไม่มีชั้น LLM จะพัง" % name,
                    )

    def test_core_modules_import_without_llm(self):
        """L2 (ด่านชี้ขาด): บล็อกโมดูล openrouter_agents แล้ว import โมดูลคอร์ ต้องสำเร็จ"""
        mods = ", ".join(IMPORTABLE_WITHOUT_LLM)
        blocker = (
            "import sys\n"
            "class _BlockLLM:\n"
            "    def find_spec(self, name, path=None, target=None):\n"
            "        if name == 'openrouter_agents' or name.startswith('openrouter_agents.'):\n"
            "            raise ImportError('blocked by test: LLM layer removed')\n"
            "        return None\n"
            "sys.meta_path.insert(0, _BlockLLM())\n"
            "import %s\n"
            "print('NO_AI_IMPORT_OK')\n" % mods
        )
        proc = subprocess.run([sys.executable, "-c", blocker], cwd=BRIDGE,
                              capture_output=True, timeout=180)
        out = (proc.stdout or b"").decode("utf-8", "replace") + \
              (proc.stderr or b"").decode("utf-8", "replace")
        self.assertIn("NO_AI_IMPORT_OK", out,
                      "โมดูลคอร์ import ไม่ได้เมื่อไม่มีชั้น LLM (ผิดหลักการ 'ตัวเทรดไม่ต้องมี AI'):\n" + out[-700:])

    def test_trader_llm_import_is_optional(self):
        """auto_trader.py เองก็ต้องมี try/except + fallback"""
        src = read(os.path.join(BRIDGE, "auto_trader.py"))
        lines = src.splitlines()
        hit = [i for i, ln in enumerate(lines) if "from openrouter_agents import" in ln]
        self.assertTrue(hit, "หา import openrouter_agents ไม่เจอ — โครงเปลี่ยน ต้องทบทวนเทสต์นี้")
        window = "\n".join(lines[max(0, hit[0] - 8): hit[0] + 12])
        self.assertIn("try:", window)
        self.assertIn("except", window)
        self.assertIn("def run_dual_agents", src)

    def test_order_path_has_no_llm(self):
        """L3: ฟังก์ชันที่ประกอบคำสั่งจริงต้องไม่รู้จัก LLM"""
        src = code_only(read(os.path.join(BRIDGE, "auto_trader.py")))
        checked = 0
        for fn in ("build_request",):
            body = func_body(src, fn)
            if not body:
                continue
            checked += 1
            for marker in LLM_MARKERS:
                self.assertIsNone(
                    re.search(marker, body),
                    "เส้นทางส่งคำสั่ง (%s) อ้างถึงชั้น LLM (%s) — ห้ามเด็ดขาด" % (fn, marker),
                )
        self.assertGreater(checked, 0)

    def test_factory_default_ai_off(self):
        """L4: ค่าโรงงานต้องปิด AI"""
        for root, _dirs, files in os.walk(os.path.join(PROJECT, "work", "factory")):
            for f in files:
                if not f.endswith(".json"):
                    continue
                try:
                    data = json.loads(read(os.path.join(root, f)))
                except Exception:
                    continue
                if isinstance(data, dict) and "openrouter" in data:
                    self.assertFalse(
                        bool((data.get("openrouter") or {}).get("enabled", False)),
                        "ค่าโรงงานเปิด AI ไว้ (%s) — ค่าตั้งต้นต้องปิด" % os.path.join(root, f),
                    )

    def test_mode_config_present(self):
        """มีไฟล์โหมดการเทรด (mode gate) อยู่ในระบบ"""
        found = any(os.path.exists(os.path.join(PROJECT, p))
                    for p in ("work/trading_mode.json", "outputs/mt5_python_bridge/choose_mode.py"))
        self.assertTrue(found, "ไม่พบกลไกโหมดการเทรด (mode gate)")


class TestChooseModeKeepsAiOut(unittest.TestCase):
    """choose_mode.py (ตัวสลับโหมด) ต้องไม่ผูกกับชั้น LLM"""

    def test_choose_mode_is_llm_free(self):
        path = os.path.join(BRIDGE, "choose_mode.py")
        if not os.path.exists(path):
            self.skipTest("ไม่พบ choose_mode.py")
        src = code_only(read(path))
        self.assertRegex(src, r"mode|MODE")
        for marker in LLM_MARKERS[:2]:
            self.assertIsNone(re.search(marker, src),
                              "choose_mode.py ต้องไม่ผูกกับชั้น LLM (%s)" % marker)


if __name__ == "__main__":
    unittest.main(verbosity=2)