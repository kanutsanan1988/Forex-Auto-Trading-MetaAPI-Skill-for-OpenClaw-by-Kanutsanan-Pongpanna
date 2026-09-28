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
from __future__ import annotations

"""OpenRouter signal and judge agents.

This module uses OpenRouter's HTTPS API directly.  It never imports an OpenAI
SDK and never sends an order.  Any failure is fail-closed: the caller receives
no trade decision and Python remains the only order executor.
"""

import hashlib
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


MODEL = "deepseek/deepseek-v4-flash-0731"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
STRATEGIES = ("trend", "range", "mean_reversion", "breakout", "counter_trend", "breakout_reversal")
RETRYABLE_HTTP_STATUS = {408, 425, 429, 500, 502, 503, 504}


class OpenRouterError(RuntimeError):
    pass


def _ai_mode_allowed() -> tuple[bool, str | None]:
    """Fail closed unless the trading system explicitly permits AI in mode 2."""
    try:
        from runtime_support import require_ai_mode
        require_ai_mode()
        return True, None
    except Exception as exc:
        return False, str(exc)


def _key_from_machine_dpapi(path: Path) -> str | None:
    """Read either supported DPAPI file representation on Windows.

    Existing installations may contain either ConvertFrom-SecureString text
    or a base64 ProtectedData blob. PowerShell decrypts both without placing
    the secret in config or command-line arguments.
    """
    if sys.platform != "win32" or not path.is_file():
        return None
    script = (
        "$raw=(Get-Content -LiteralPath $env:KANATSANAN_OPENROUTER_KEY_FILE -Raw).Trim(); "
        "try {$x=$raw|ConvertTo-SecureString -ErrorAction Stop; "
        "$p=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($x); "
        "try {[Runtime.InteropServices.Marshal]::PtrToStringBSTR($p); exit 0} "
        "finally {[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($p)}} catch {} "
        "Add-Type -AssemblyName System.Security; $b=[Convert]::FromBase64String($raw); "
        "foreach($s in @([Security.Cryptography.DataProtectionScope]::CurrentUser," 
        "[Security.Cryptography.DataProtectionScope]::LocalMachine)){try{" 
        "$p=[Security.Cryptography.ProtectedData]::Unprotect($b,$null,$s); "
        "$v=[Text.Encoding]::UTF8.GetString($p); if($v){$v; exit 0}}catch{}}; exit 1"
    )
    try:
        child_env = dict(os.environ)
        child_env["KANATSANAN_OPENROUTER_KEY_FILE"] = str(path)
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            check=True, capture_output=True, text=True, timeout=10, env=child_env,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value or None


def load_api_key(config: dict, root: Path | None = None) -> str | None:
    settings = config.get("openrouter", config)
    key = os.environ.get(str(settings.get("api_key_env", "OPENROUTER_API_KEY")))
    if key:
        return key.strip()
    configured = settings.get("api_key_file")
    if not configured:
        return None
    path = Path(configured)
    if not path.is_absolute() and root is not None:
        path = root / path
    if path.suffix == ".dpapi":
        return _key_from_machine_dpapi(path)
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _json_object(text: str) -> dict:
    if not isinstance(text, str) or not text.strip():
        raise OpenRouterError("OpenRouter response content was empty")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OpenRouterError("OpenRouter returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise OpenRouterError("OpenRouter response was not a JSON object")
    return value


def _confidence(value, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise OpenRouterError(f"OpenRouter {field} was not numeric") from exc
    if not math.isfinite(result):
        raise OpenRouterError(f"OpenRouter {field} was not finite")
    return max(0.0, min(1.0, result))


def _required_text(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OpenRouterError(f"OpenRouter {field} was missing")
    return value.strip()


def _text_list(value, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise OpenRouterError(f"OpenRouter {field} must be an array of non-empty strings")
    return [item.strip() for item in value[:12]]


def _call(config: dict, system: str, user: dict) -> dict:
    key = load_api_key(config, Path(__file__).resolve().parents[2])
    if not key:
        raise OpenRouterError("OpenRouter API key is not configured")
    payload = {
        "model": MODEL,
        "temperature": float(config.get("openrouter", {}).get("temperature", 0.1)),
        "max_tokens": int(config.get("openrouter", {}).get("max_tokens", 1200)),
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": json.dumps(user, ensure_ascii=False, separators=(",", ":"))}],
        "response_format": {"type": "json_object"},
    }
    encoded = json.dumps(payload).encode("utf-8")
    settings = config.get("openrouter", {})
    timeout = float(settings.get("timeout_seconds", 25))
    max_attempts = max(1, min(3, int(settings.get("max_attempts", 2))))
    retry_delay = max(0.0, min(5.0, float(settings.get("retry_delay_seconds", 1.0))))
    body = None
    last_error = None
    for attempt in range(1, max_attempts + 1):
        request = urllib.request.Request(
            API_URL, data=encoded, method="POST",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                     "HTTP-Referer": "https://openrouter.ai", "X-Title": "MT5 Gold Trading Dual Agents"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw_body = response.read().decode("utf-8")
            try:
                body = json.loads(raw_body)
            except json.JSONDecodeError as exc:
                # HTTP succeeded and may already be billed. Do not repeat the
                # same paid request merely because its envelope was malformed.
                raise OpenRouterError("OpenRouter returned an invalid JSON envelope") from exc
            break
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"
            if exc.code not in RETRYABLE_HTTP_STATUS or attempt >= max_attempts:
                raise OpenRouterError(f"OpenRouter request failed: {last_error}") from exc
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            try:
                delay = min(5.0, max(retry_delay, float(retry_after))) if retry_after else retry_delay
            except ValueError:
                delay = retry_delay
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = type(exc).__name__
            if attempt >= max_attempts:
                raise OpenRouterError(f"OpenRouter request failed: {last_error}") from exc
            time.sleep(retry_delay)
    if body is None:
        raise OpenRouterError(f"OpenRouter request failed: {last_error or 'unknown error'}")
    try:
        message = body["choices"][0]["message"]
        content = message.get("content") if isinstance(message, dict) else None
        return _json_object(content)
    except OpenRouterError:
        raise
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise OpenRouterError("OpenRouter response had no usable message") from exc


def _rules() -> str:
    return ("Analyze only the supplied closed-bar features. Use the same six strategy "
            "families as the Python system: trend, range, mean_reversion, breakout, "
            "counter_trend, breakout_reversal. Do not invent prices or news. Be explicit "
            "about confirming and contradicting evidence. This is analysis, not a guarantee.")


def get_signal(config: dict, frames: dict, python_signal: dict | None = None) -> dict:
    system = _rules() + " Return JSON with keys: side (buy/sell/no_trade), strategy, confidence (0..1), reason, supporting_evidence (array), risks (array)."
    # Keep this call blind to Python's answer so agreement/disagreement is real.
    result = _call(config, system, {"task": "independent_signal", "frames": frames})
    side = result.get("side")
    if side not in {"buy", "sell", "no_trade"}:
        raise OpenRouterError("OpenRouter signal had invalid side")
    strategy = result.get("strategy")
    if side == "no_trade":
        # Models sometimes explain the strategy in prose even when declining.
        # A no-trade signal has no executable strategy, so normalize it away.
        strategy = None
    elif strategy not in STRATEGIES:
        raise OpenRouterError("OpenRouter signal had invalid strategy")
    result["side"] = side
    result["strategy"] = strategy
    raw_confidence = result.get("confidence")
    result["confidence"] = 0.0 if side == "no_trade" and raw_confidence is None else _confidence(raw_confidence, "signal confidence")
    result["reason"] = _required_text(result.get("reason"), "signal reason")
    evidence = result.get("supporting_evidence")
    risks = result.get("risks")
    result["supporting_evidence"] = _text_list([] if evidence is None else evidence, "supporting_evidence")
    result["risks"] = _text_list([] if risks is None else risks, "signal risks")
    return result


def judge(config: dict, frames: dict, python_signal: dict, openrouter_signal: dict) -> dict:
    system = (_rules() + " You are the final judge. Compare both signal groups fairly. "
              "Choose no_trade when evidence is weak, contradictory, stale, or the two "
              "agents disagree without a clear winner. Return JSON with keys: decision "
              "(buy/sell/no_trade), selected_group (python/openrouter/none), confidence "
              "(0..1), reason, agreement (agree/disagree/one_sided), risks (array).")
    result = _call(config, system, {"task": "final_judge", "frames": frames,
                                    "python_signal": python_signal, "openrouter_signal": openrouter_signal})
    if result.get("decision") not in {"buy", "sell", "no_trade"}:
        raise OpenRouterError("OpenRouter judge had invalid decision")
    selected_group = result.get("selected_group")
    if selected_group not in {"python", "openrouter", "none"}:
        raise OpenRouterError("OpenRouter judge had invalid selected_group")
    agreement = result.get("agreement")
    if agreement not in {"agree", "disagree", "one_sided"}:
        raise OpenRouterError("OpenRouter judge had invalid agreement")
    raw_confidence = result.get("confidence")
    result["confidence"] = 0.0 if result["decision"] == "no_trade" and raw_confidence is None else _confidence(raw_confidence, "judge confidence")
    result["reason"] = _required_text(result.get("reason"), "judge reason")
    result["risks"] = _text_list([] if result.get("risks") is None else result.get("risks"), "judge risks")
    if result["decision"] != "no_trade":
        selected_signal = python_signal if selected_group == "python" else openrouter_signal if selected_group == "openrouter" else None
        if selected_signal is None or selected_signal.get("side") != result["decision"]:
            raise OpenRouterError("OpenRouter judge decision did not match its selected signal group")
    return result


def _cache_path() -> Path:
    return Path(__file__).resolve().parents[2] / "work" / "openrouter_decision_cache.json"


def _cache_key(config: dict, frames: dict, python_decision: dict) -> str:
    payload = {
        "model": MODEL,
        "settings": {key: value for key, value in config.get("openrouter", {}).items()
                     if key not in {"api_key_env", "api_key_file"}},
        "frames": frames,
        "python_decision": python_decision,
    }
    stable = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _load_cache(config: dict, cache_key: str) -> dict | None:
    max_age = max(0.0, float(config.get("openrouter", {}).get("cache_seconds", 90)))
    if max_age <= 0.0:
        return None
    try:
        cached = json.loads(_cache_path().read_text(encoding="utf-8"))
        if cached.get("model") != MODEL or cached.get("cache_key") != cache_key:
            return None
        if time.time() - float(cached["created_at"]) > max_age:
            return None
        result = cached["result"]
        if not isinstance(result, dict) or result.get("status") != "ok":
            return None
        result["cached"] = True
        return result
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def _save_cache(cache_key: str, result: dict) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        temp.write_text(json.dumps({"model": MODEL, "cache_key": cache_key,
                                    "created_at": time.time(), "result": result},
                                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        temp.replace(path)
    except OSError:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


def run_dual_agents(config: dict, frames: dict, python_decision: dict) -> dict:
    """Run signal agent then judge; return a complete auditable comparison."""
    if not bool(config.get("openrouter", {}).get("enabled", False)):
        return {"enabled": False, "status": "disabled", "trade_decision": python_decision}
    ai_allowed, blocked_reason = _ai_mode_allowed()
    if not ai_allowed:
        return {"enabled": False, "status": "blocked_by_mode", "reason": blocked_reason,
                "trade_decision": python_decision}
    python_signal = {
        "side": python_decision.get("side") or "no_trade",
        "strategy": python_decision.get("strategy"),
        "confidence": python_decision.get("confidence", 0.0),
        "reason": python_decision.get("reason", ""),
        "regime": python_decision.get("regime", {}).get("regime"),
        "candidates": python_decision.get("candidates", []),
    }
    cache_key = _cache_key(config, frames, python_decision)
    cached = _load_cache(config, cache_key)
    if cached is not None:
        return cached
    try:
        signal = get_signal(config, frames, python_signal)
        final = judge(config, frames, python_signal, signal)
        decision = copy_decision(python_decision)
        minimum_confidence = float(config.get("openrouter", {}).get("judge_min_confidence", 0.55))
        if final["decision"] != "no_trade" and final["confidence"] < minimum_confidence:
            final = dict(final)
            final.update(decision="no_trade", selected_group="none",
                         reason=f"judge confidence below minimum {minimum_confidence:.2f}")
        if final["decision"] == "no_trade":
            decision.update(side=None, strategy=None, confidence=0.0, stop_distance=None, reward_risk=None,
                            reason="final OpenRouter judge: " + str(final.get("reason", "no trade")))
        elif final["decision"] != python_signal["side"]:
            # The judge may select the OpenRouter direction, but execution
            # parameters must still come from a Python-calculated candidate.
            candidates = [c for c in python_decision.get("candidates", [])
                          if c.get("side") == final["decision"] and c.get("eligible")
                          and c.get("trade_enabled", True) and c.get("stop_distance") is not None
                          and c.get("reward_risk") is not None]
            candidates.sort(key=lambda c: float(c.get("confidence", 0.0)), reverse=True)
            if not candidates:
                decision.update(side=None, strategy=None, confidence=0.0, stop_distance=None, reward_risk=None,
                                reason="final judge selected a direction with no Python execution candidate")
            else:
                selected = candidates[0]
                decision.update(side=final["decision"], strategy=selected.get("strategy"),
                                confidence=min(float(selected.get("confidence", 0.0)), float(final.get("confidence", 0.0))),
                                stop_distance=selected.get("stop_distance"), reward_risk=selected.get("reward_risk"),
                                reason="final OpenRouter judge selected the opposite direction: " + str(final.get("reason", "")))
        result = {"enabled": True, "status": "ok", "cached": False, "python_signal": python_signal,
                  "openrouter_signal": signal, "judge": final, "trade_decision": decision}
        _save_cache(cache_key, result)
        return result
    except (OpenRouterError, ValueError, TypeError) as exc:
        if bool(config.get("openrouter", {}).get("fallback_to_python", True)):
            return {"enabled": True, "status": "fallback_python", "fallback": True,
                    "error": str(exc), "python_signal": python_signal,
                    "trade_decision": copy_decision(python_decision)}
        return {"enabled": True, "status": "error", "error": str(exc),
                "python_signal": python_signal, "trade_decision": fail_closed(python_decision, str(exc))}


def copy_decision(decision: dict) -> dict:
    return json.loads(json.dumps(decision))


def fail_closed(decision: dict, error: str) -> dict:
    result = copy_decision(decision)
    result.update(side=None, strategy=None, confidence=0.0, stop_distance=None, reward_risk=None,
                  reason="OpenRouter dual-agent unavailable: " + error)
    return result
