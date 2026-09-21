# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""Bounded admin config transactions. This is not an OS sandbox for AI tools."""
import math
import uuid
from pathlib import Path
from runtime_support import atomic_json, require_ai_mode, update_json

PROTECTED = {'live_enabled', 'magic', 'volume', 'symbol'}


def get_path(value, key):
    for part in key.split('.'):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def apply_values(path, values, bounds, *, root, expected_hash=None, label='admincmd'):
    """Validate all changes before backup/commit, retaining unrelated current keys."""
    require_ai_mode(root)
    changes = []

    def mutate(current):
        require_ai_mode(root)
        converted = {}
        for key, value in values.items():
            if key not in bounds or PROTECTED.intersection(key.split('.')):
                raise ValueError('Admin key not permitted: ' + key)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError('Admin value must be finite numeric: ' + key)
            lo, hi = bounds[key]
            if not lo <= value <= hi:
                raise ValueError('Admin value out of bounds: ' + key)
            old = get_path(current, key)
            if old is None:
                raise ValueError('Admin key missing from current config: ' + key)
            if isinstance(old, bool):
                if value not in (0, 1):
                    raise ValueError('Boolean key accepts only 0 or 1: ' + key)
                value = bool(value)
            elif isinstance(old, int):
                if int(value) != value:
                    raise ValueError('Integer key needs a whole number: ' + key)
                value = int(value)
            elif not isinstance(old, float):
                raise ValueError('Admin key is not numeric: ' + key)
            converted[key] = value
        if any(get_path(current, k) != v for k, v in converted.items()):
            atomic_json(str(path) + '.bak_' + label + '_' + uuid.uuid4().hex, current)
        for key, value in converted.items():
            old = get_path(current, key)
            node = current
            parts = key.split('.')
            for part in parts[:-1]:
                node = node[part]
            node[parts[-1]] = value
            if old != value:
                changes.append({'key': key, 'from': old, 'to': value})
        return current

    result = update_json(Path(path), mutate, expected_hash=expected_hash)
    return result, changes


def restore_values(path, snapshot, bounds, *, root, expected_hash=None):
    values = {k: get_path(snapshot, k) for k in bounds if get_path(snapshot, k) is not None}
    return apply_values(path, values, bounds, root=root,
                        expected_hash=expected_hash, label='before_bounded_rollback')
