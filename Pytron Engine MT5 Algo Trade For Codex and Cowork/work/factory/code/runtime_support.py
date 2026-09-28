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
"""Atomic JSON and advisory locks shared by research and trading."""
import contextlib
import hashlib
import json
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

DEFAULT_MODE = 'internal_llm_join'
MODE_TITLES = {
    'internal_only': 'เทรดด้วยสัญญาณภายใน',
    'internal_llm_join': 'เทรดร่วมสัญญาณ AI',
}

def configure_utf8_stdio(streams=None):
    """Keep project Python console I/O in UTF-8, including direct CLI runs."""
    if streams is None:
        streams = (sys.stdin, sys.stdout, sys.stderr)
    for stream in streams:
        reconfigure = getattr(stream, 'reconfigure', None)
        if callable(reconfigure):
            try:
                reconfigure(encoding='utf-8', errors='replace')
            except (OSError, ValueError):
                # Some redirected/test streams are already consumed or immutable.
                pass

configure_utf8_stdio()

def project_root():
    return Path(os.environ.get('TRADING_PROJECT_ROOT', Path(__file__).resolve().parents[2])).resolve()

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

@contextlib.contextmanager
def file_lock(path, timeout=10):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = open(path, 'a+b')
    stream.seek(0, 2)
    if not stream.tell():
        stream.write(b'0')
        stream.flush()
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                stream.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Another configuration/research operation is in progress')
                time.sleep(.1)
        yield
    finally:
        stream.close()

def write_recommendation(path, rec, source='unknown', defer_if_pending_llm=False):
    """เขียนคำแนะนำลง 'กล่องจดหมายไฟล์เดียว' อย่างปลอดภัย (19 ก.ย. 2026)

    กติกาเจ้าของระบบ: consumer อ่าน `latest_recommendation.json` **ไฟล์นี้ไฟล์เดียว**
    (ห้ามเปลี่ยนไปใช้ไฟล์อื่น ไม่งั้นระบบข้อมูลภายในจะแตกเป็นสองทาง)
    → ทุกฝ่าย (สคริปต์ภายใน · บอท/agent) ต้องเขียนผ่านฟังก์ชันนี้ เพื่อให้ได้ครบ 3 อย่าง:

      1) **สำรองก่อนทับ** — ถ้าไฟล์เดิมยังไม่ถูกประมวลผล (hash ≠ last_applied) จะคัดลอก
         ไปเก็บที่ `superseded/` ก่อน → ไม่มีคำแนะนำไหนหายเงียบ ๆ เมื่อสองฝ่ายเขียนชนกัน
      2) **ติดป้าย source** (internal / bot / ...) → ตรวจย้อนได้ว่าคำแนะนำมาจากฝ่ายไหน
      3) **เขียนแบบ atomic** (temp + fsync + os.replace) → อ่านไม่เจอไฟล์ครึ่ง ๆ กลาง ๆ
    """
    path = Path(path)
    if isinstance(rec, dict) and source:
        rec = dict(rec)
        rec.setdefault('source', source)
    # Serialize read/archive/replace, not merely the final write. A failed archive
    # must leave the previous recommendation intact, never silently discard it.
    with file_lock(str(path) + '.lock'):
        if path.exists():
            cur = json.loads(path.read_text(encoding='utf-8'))
            applied = path.parent / 'last_applied.json'
            applied_hash = None
            if applied.exists():
                try:
                    applied_hash = json.loads(applied.read_text(encoding='utf-8')).get('rec_hash')
                except Exception:
                    applied_hash = None
            # The internal signal bridge runs immediately before the consumer.
            # Do not erase a bot's unprocessed proposal before it can be tested.
            if (defer_if_pending_llm and isinstance(rec, dict) and isinstance(cur, dict)
                    and cur.get('uses_llm') is True
                    and cur.get('mode_epoch') == rec.get('mode_epoch')
                    and cur.get('mode') == rec.get('mode')):
                failed_hash = None
                failed = path.parent / 'last_failed.json'
                if failed.exists():
                    try:
                        failed_hash = json.loads(failed.read_text(encoding='utf-8')).get('rec_hash')
                    except (ValueError, OSError):
                        pass
                if digest(cur) not in (applied_hash, failed_hash):
                    return None  # Caller must not mark its signal as submitted.
            if applied_hash != digest(cur):          # ยังไม่ถูกประมวลผล → สำรองก่อนทับ
                superseded = path.parent / 'superseded'
                superseded.mkdir(parents=True, exist_ok=True)
                stamp = time.strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex
                atomic_json(superseded / ('superseded-' + stamp + '.json'), cur)
        atomic_json(path, rec)
    return rec


def update_json(path, mutate, expected_hash=None):
    path = Path(path)
    with file_lock(str(path) + '.lock'):
        current = json.loads(path.read_text(encoding='utf-8'))
        if expected_hash is not None and digest(current) != expected_hash:
            raise ValueError('Configuration changed during evaluation; retry the new baseline')
        result = mutate(current)
        atomic_json(path, result)
        return result

def current_mode(root=None):
    root = Path(root or project_root())
    data = json.loads((root / 'work/trading_mode.json').read_text(encoding='utf-8'))
    if data.get('mode') not in MODE_TITLES:
        raise ValueError('Choose a trading mode explicitly before starting research')
    return data


def require_ai_mode(root=None):
    """AI bot entry points may run only in mode 2 and while not stopped."""
    root = Path(root or project_root())
    mode = current_mode(root)
    if mode['mode'] != DEFAULT_MODE:
        raise ValueError('AI integrations are disabled in mode 1')
    if (root / 'work/AUTO_TRADER_STOP').exists():
        raise ValueError('Kill switch present; AI integrations remain stopped')
    return mode
