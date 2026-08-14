import asyncio
import contextlib

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.api_client import api_client, ApiError
from bot.config import settings
from bot.keyboards import logs_kb
from bot.utils import truncate_for_telegram, escape_html, set_live_log_task, stop_live_log_task, has_live_log_task

router = Router(name="logs")

MAX_LIVE_ITERATIONS = 90  # 90 * 4s ≈ 6 دقائق كحد أقصى للتحديث التلقائي المتواصل


async def _render_logs_text(bot_id: str) -> str:
    try:
        logs = await api_client.get_logs(bot_id, tail=settings.LOG_TAIL_DEFAULT)
    except ApiError as exc:
        return f"⚠️ تعذر جلب السجلات: {exc.detail}"
    if not logs.strip():
        return "📜 لا توجد سجلات بعد."
    return f"📜 <b>آخر {settings.LOG_TAIL_DEFAULT} سطر:</b>\n\n<pre>{escape_html(truncate_for_telegram(logs, 3500))}</pre>"


@router.callback_query(F.data.startswith("bot:logs:"))
async def cb_logs_open(call: CallbackQuery) -> None:
    bot_id = call.data.split(":", 2)[2]
    text = await _render_logs_text(bot_id)
    await call.message.edit_text(text, reply_markup=logs_kb(bot_id, has_live_log_task(call.message.chat.id)))
    await call.answer()


@router.callback_query(F.data.startswith("log:refresh:"))
async def cb_logs_refresh(call: CallbackQuery) -> None:
    bot_id = call.data.split(":", 2)[2]
    text = await _render_logs_text(bot_id)
    try:
        await call.message.edit_text(text, reply_markup=logs_kb(bot_id, has_live_log_task(call.message.chat.id)))
    except TelegramBadRequest:
        pass  # نفس المحتوى بالضبط، تجاهل
    await call.answer()


async def _live_loop(bot: Bot, chat_id: int, message_id: int, bot_id: str) -> None:
    try:
        for _ in range(MAX_LIVE_ITERATIONS):
            await asyncio.sleep(settings.LOG_LIVE_REFRESH_SECONDS)
            text = await _render_logs_text(bot_id)
            with contextlib.suppress(TelegramBadRequest):
                await bot.edit_message_text(
                    text, chat_id=chat_id, message_id=message_id,
                    reply_markup=logs_kb(bot_id, True),
                )
    except asyncio.CancelledError:
        pass
    finally:
        with contextlib.suppress(TelegramBadRequest):
            text = await _render_logs_text(bot_id)
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id,
                reply_markup=logs_kb(bot_id, False),
            )


@router.callback_query(F.data.startswith("log:live_on:"))
async def cb_logs_live_on(call: CallbackQuery) -> None:
    bot_id = call.data.split(":", 2)[2]
    chat_id = call.message.chat.id
    task = asyncio.create_task(_live_loop(call.bot, chat_id, call.message.message_id, bot_id))
    set_live_log_task(chat_id, task)
    await call.answer("▶️ تم تفعيل التحديث التلقائي")
    text = await _render_logs_text(bot_id)
    await call.message.edit_text(text, reply_markup=logs_kb(bot_id, True))


@router.callback_query(F.data.startswith("log:live_off:"))
async def cb_logs_live_off(call: CallbackQuery) -> None:
    bot_id = call.data.split(":", 2)[2]
    stop_live_log_task(call.message.chat.id)
    await call.answer("⏹ تم إيقاف التحديث التلقائي")
    text = await _render_logs_text(bot_id)
    await call.message.edit_text(text, reply_markup=logs_kb(bot_id, False))
