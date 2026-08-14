from __future__ import annotations

import asyncio
import secrets
import time
from dataclasses import dataclass, field

TELEGRAM_MSG_LIMIT = 4096

STATUS_EMOJI = {
    "running": "🟢",
    "stopped": "⚪️",
    "crashed": "🔴",
    "error": "🔴",
    "created": "🟡",
    "installing": "🟡",
    "deleting": "🟠",
}


def status_line(status: str) -> str:
    return f"{STATUS_EMOJI.get(status, '⚫️')} {status}"


def format_bytes(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num) < 1024:
            return f"{num:.1f}{unit}"
        num /= 1024
    return f"{num:.1f}TB"


def truncate_for_telegram(text: str, limit: int = TELEGRAM_MSG_LIMIT - 200) -> str:
    if len(text) <= limit:
        return text
    return "…(تم القص)…\n" + text[-limit:]


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ---------------------------------------------------------------------------
# مخزن مؤقت (في الذاكرة فقط) لعمليات تحتاج تأكيد بزر "تأكيد/إلغاء".
# لا نضع تفاصيل العملية الحساسة داخل callback_data نفسها (محدودة بـ 64 بايت
# وتبقى ظاهرة في تاريخ المحادثة)، بل نخزّن توكن قصير عشوائي يشير إليها هنا،
# وتُحذف فور الاستخدام أو بعد انتهاء صلاحيتها.
# ---------------------------------------------------------------------------
@dataclass
class PendingAction:
    action: str
    payload: dict
    created_at: float = field(default_factory=time.time)


_PENDING: dict[str, PendingAction] = {}
_PENDING_TTL_SECONDS = 300


def create_pending_action(action: str, payload: dict) -> str:
    _gc_pending()
    token = secrets.token_hex(4)
    _PENDING[token] = PendingAction(action=action, payload=payload)
    return token


def pop_pending_action(token: str) -> PendingAction | None:
    return _PENDING.pop(token, None)


def _gc_pending() -> None:
    now = time.time()
    expired = [t for t, p in _PENDING.items() if now - p.created_at > _PENDING_TTL_SECONDS]
    for t in expired:
        _PENDING.pop(t, None)


# ---------------------------------------------------------------------------
# مهام تحديث السجلات الحية (Live logs) — مهمة asyncio واحدة كحد أقصى لكل محادثة
# ---------------------------------------------------------------------------
_LIVE_LOG_TASKS: dict[int, asyncio.Task] = {}


def set_live_log_task(chat_id: int, task: asyncio.Task) -> None:
    stop_live_log_task(chat_id)
    _LIVE_LOG_TASKS[chat_id] = task


def stop_live_log_task(chat_id: int) -> None:
    task = _LIVE_LOG_TASKS.pop(chat_id, None)
    if task and not task.done():
        task.cancel()


def has_live_log_task(chat_id: int) -> bool:
    task = _LIVE_LOG_TASKS.get(chat_id)
    return bool(task and not task.done())
