"""LLM wrapper — supports Ollama, Claude API, and OpenAI-compatible endpoints.

Execution follows `fallback_chain` in settings.json.
On billing/quota errors the next backend in the chain is tried automatically.
If the chain is exhausted due to billing errors and Ollama is not in the chain,
a BillingExhaustedException is raised so the caller can ask the user first.
"""
import base64
import json
import ssl
import sys
import time
import urllib.request
from pathlib import Path

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()

SETTINGS_FILE = Path(__file__).parent.parent / "settings.json"
SCHEMA        = Path(__file__).parent.parent / "schema.md"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

DEFAULT_SETTINGS = {
    "mode":           "ollama",
    "auto_ingest":    True,
    "fallback_chain": ["claude", "ollama"],
    "ollama": {
        "base_url":     "http://localhost:11434",
        "text_model":   "qwen3.5:9b",
        "vision_model": "qwen3-vl:8b",
    },
    "claude": {
        "api_key":    "",
        "text_model": "claude-sonnet-4-6",
    },
    "custom": {
        "base_url":   "",
        "api_key":    "",
        "text_model": "",
    },
}


class BillingExhaustedException(RuntimeError):
    """Raised when all backends in fallback_chain have run out of credit/quota
    and Ollama is not in the user's configured chain.

    Callers should present a confirmation dialog before retrying with Ollama.
    """
    def __init__(self, message: str, last_backend: str):
        super().__init__(message)
        self.last_backend = last_backend


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text())
    return DEFAULT_SETTINGS


_BILLING_PHRASES = (
    "credit balance is too low",
    "exceeded your current quota",
    "billing_hard_limit_reached",
    "insufficient_quota",
    "余额不足",
    "account balance",
)

def _is_billing_error(msg: str) -> bool:
    return any(p in msg.lower() for p in _BILLING_PHRASES)


def _resolve_custom_cfg(s: dict, backend: str) -> dict:
    """Return the custom-endpoint config dict for a given backend ID.

    Handles both the legacy ``"custom"`` id and ``"preset:<name>"`` ids that
    reference an entry in ``custom_presets``.
    """
    if backend.startswith("preset:"):
        name = backend[7:]
        for p in s.get("custom_presets", []):
            if p["name"] == name:
                return p
        raise RuntimeError(f"Preset '{name}' not found in settings")
    return s["custom"]


def _backend_display_name(s: dict, backend: str) -> str:
    """Human-readable name for warning messages."""
    if backend == "claude":
        return "Claude"
    if backend == "ollama":
        return "Ollama"
    if backend.startswith("preset:"):
        return backend[7:]
    return "自定义"


# ── Low-level HTTP helper ──────────────────────────────────────────────────────

def _post(url: str, payload: dict, headers: dict, timeout: int = 300) -> dict:
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json", **headers}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} from {url}: {body}") from e


# ── Single-backend helpers ─────────────────────────────────────────────────────

def _chat_single(s: dict, backend: str, messages: list[dict]) -> str:
    """Attempt one backend. Raises RuntimeError on any failure."""
    if backend == "ollama":
        cfg = s["ollama"]
        r = _post(
            f"{cfg['base_url']}/api/chat",
            {"model": cfg["text_model"], "messages": messages, "stream": False,
             "options": {"temperature": 0.2}},
            {},
        )
        return r["message"]["content"]

    elif backend == "claude":
        cfg = s["claude"]
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        user_msgs    = [m for m in messages if m["role"] != "system"]
        payload: dict = {"model": cfg["text_model"], "max_tokens": 4096, "messages": user_msgs}
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        r = _post(
            "https://api.anthropic.com/v1/messages",
            payload,
            {"x-api-key": cfg["api_key"], "anthropic-version": "2023-06-01"},
        )
        return r["content"][0]["text"]

    else:  # "custom" or "preset:<name>" — OpenAI-compatible
        cfg = _resolve_custom_cfg(s, backend)
        r = _post(
            f"{cfg['base_url'].rstrip('/')}/chat/completions",
            {"model": cfg["text_model"], "messages": messages, "temperature": 0.2},
            {"Authorization": f"Bearer {cfg['api_key']}"},
        )
        return r["choices"][0]["message"]["content"]


def _describe_single(s: dict, backend: str, image_b64: str) -> str:
    """Attempt one backend for image description. Raises RuntimeError on any failure."""
    prompt = (
        "请详细描述这张图片。包括：图片展示的内容、可见的文字或标签、"
        "图表或图形及其含义、关键概念。如涉及技术内容请具体说明。"
        "请用中文回答。"
    )

    if backend == "ollama":
        cfg = s["ollama"]
        r = _post(
            f"{cfg['base_url']}/api/chat",
            {
                "model":    cfg["vision_model"],
                "messages": [{"role": "user", "content": prompt, "images": [image_b64]}],
                "stream":   False,
                "options":  {"temperature": 0.1},
            },
            {},
        )
        return r["message"]["content"]

    elif backend == "claude":
        cfg = s["claude"]
        r = _post(
            "https://api.anthropic.com/v1/messages",
            {
                "model":      cfg["text_model"],
                "max_tokens": 1024,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {
                            "type": "base64", "media_type": "image/jpeg", "data": image_b64,
                        }},
                        {"type": "text", "text": prompt},
                    ],
                }],
            },
            {"x-api-key": cfg["api_key"], "anthropic-version": "2023-06-01"},
        )
        return r["content"][0]["text"]

    else:  # "custom" or "preset:<name>" — OpenAI-compatible
        cfg = _resolve_custom_cfg(s, backend)
        r = _post(
            f"{cfg['base_url'].rstrip('/')}/chat/completions",
            {
                "model":    cfg["text_model"],
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                        {"type": "text", "text": prompt},
                    ],
                }],
                "temperature": 0.1,
            },
            {"Authorization": f"Bearer {cfg['api_key']}"},
        )
        return r["choices"][0]["message"]["content"]


# ── Public API ─────────────────────────────────────────────────────────────────

def _build_chain(s: dict, preferred_backend: str | None) -> list[str]:
    """
    Build the ordered list of backends to try.

    The fallback_chain in settings is the authoritative list.
    If a preferred_backend is given (e.g. from parallel routing), it is
    moved to the front ONLY if it is already present in the chain.
    Backends not in the user's chain are never silently added.
    """
    chain = list(s.get("fallback_chain") or [s.get("mode", "ollama")])
    if not preferred_backend or preferred_backend not in chain:
        return chain
    if chain[0] != preferred_backend:
        chain = [preferred_backend] + [b for b in chain if b != preferred_backend]
    return chain


def chat(
    messages: list[dict],
    backend: str | None = None,
    warn_cb=None,
    allow_ollama_fallback: bool = False,
) -> str:
    """Run chat inference following fallback_chain.

    Parameters
    ----------
    messages:
        Conversation messages.
    backend:
        Optional preferred backend (parallel routing hint). Only used if it is
        already present in the user's fallback_chain.
    warn_cb:
        Optional callback(msg: str) for billing-fallback log lines.
    allow_ollama_fallback:
        If True, Ollama is appended as last-resort even when not in chain.
        Only set this after the user has explicitly consented.
    """
    s = load_settings()
    chain = _build_chain(s, backend)

    # User explicitly consented to Ollama as emergency fallback
    if allow_ollama_fallback and "ollama" not in chain:
        chain = chain + ["ollama"]

    last_error: RuntimeError | None = None
    for i, b in enumerate(chain):
        try:
            return _chat_single(s, b, messages)
        except RuntimeError as e:
            if _is_billing_error(str(e)):
                b_name = _backend_display_name(s, b)
                if i < len(chain) - 1:
                    next_name = _backend_display_name(s, chain[i + 1])
                    msg = f"  WARNING: {b_name} 余额不足，已自动切换到 {next_name} 继续处理"
                else:
                    msg = f"  WARNING: {b_name} 余额不足，链中无更多后端可用"
                print(msg, file=sys.stderr, flush=True)
                if warn_cb:
                    warn_cb(msg)
                last_error = e
                continue
            raise  # non-billing errors propagate immediately

    # All chain entries exhausted due to billing — raise a typed exception so
    # callers can ask the user whether to fall back to local Ollama.
    if last_error is not None and "ollama" not in chain:
        raise BillingExhaustedException(
            "所有 API 后端余额均已耗尽，请确认是否启用本地 Ollama 继续处理",
            last_backend=chain[-1] if chain else "unknown",
        )

    raise last_error or RuntimeError("fallback_chain 中所有后端均失败")


def describe_image(
    source: "Path | str",
    backend: str | None = None,
    warn_cb=None,
    allow_ollama_fallback: bool = False,
) -> str:
    """Describe an image via vision model. source is a local Path or remote URL."""
    s = load_settings()
    chain = _build_chain(s, backend)

    if allow_ollama_fallback and "ollama" not in chain:
        chain = chain + ["ollama"]

    image_bytes = _fetch_bytes(source) if isinstance(source, str) else Path(source).read_bytes()
    image_b64   = base64.b64encode(image_bytes).decode()

    last_error: RuntimeError | None = None
    for i, b in enumerate(chain):
        try:
            return _describe_single(s, b, image_b64)
        except RuntimeError as e:
            if _is_billing_error(str(e)):
                b_name = _backend_display_name(s, b)
                if i < len(chain) - 1:
                    next_name = _backend_display_name(s, chain[i + 1])
                    msg = f"  WARNING: {b_name} 余额不足，已自动切换到 {next_name} 继续处理（视觉任务）"
                else:
                    msg = f"  WARNING: {b_name} 余额不足，链中无更多后端可用"
                print(msg, file=sys.stderr, flush=True)
                if warn_cb:
                    warn_cb(msg)
                last_error = e
                continue
            raise

    if last_error is not None and "ollama" not in chain:
        raise BillingExhaustedException(
            "所有 API 后端余额均已耗尽（视觉任务），请确认是否启用本地 Ollama 继续处理",
            last_backend=chain[-1] if chain else "unknown",
        )

    raise last_error or RuntimeError("describe_image: 所有后端均失败")


def test_connection(backend: str) -> dict:
    """Test connectivity to a backend with a minimal request.

    Returns::

        {"ok": True,  "latency_ms": 342}
        {"ok": False, "error": "Connection refused"}
    """
    s = load_settings()
    start = time.monotonic()
    probe = [{"role": "user", "content": "hi"}]
    try:
        if backend == "ollama":
            cfg = s.get("ollama", {})
            base = cfg.get("base_url", "http://localhost:11434")
            # Use /api/tags for a lightweight reachability check
            req = urllib.request.Request(f"{base}/api/tags")
            with urllib.request.urlopen(req, timeout=5, context=_SSL_CTX):
                pass
        elif backend == "claude":
            _chat_single(s, "claude", probe)
        else:
            _chat_single(s, backend, probe)
        latency = int((time.monotonic() - start) * 1000)
        return {"ok": True, "latency_ms": latency}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _fetch_bytes(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; wiki-kb/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
        return resp.read()


def schema_text() -> str:
    return SCHEMA.read_text(encoding="utf-8")
