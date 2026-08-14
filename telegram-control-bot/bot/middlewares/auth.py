"""
Middleware أمني: يقبل فقط الرسائل/الأزرار القادمة من TELEGRAM_ALLOWED_USER_ID.
أي مستخدم آخر يُتجاهل تمامًا دون أي رد يكشف أن البوت موجود أو يعمل
(لا رسالة خطأ، لا "غير مصرح لك" — تجاهل صامت بالكامل حسب المتطلبات).
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from bot.config import settings


class AllowedUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None and isinstance(event, Update):
            if event.message:
                user = event.message.from_user
            elif event.callback_query:
                user = event.callback_query.from_user

        if user is None or user.id != settings.TELEGRAM_ALLOWED_USER_ID:
            # تجاهل صامت — لا نُكمل السلسلة ولا نرد بأي شيء
            return None

        return await handler(event, data)
