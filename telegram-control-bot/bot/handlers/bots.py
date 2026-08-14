from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.api_client import api_client, ApiError
from bot.keyboards import bots_list_kb, bot_detail_kb, back_to_bot_kb, confirm_kb
from bot.utils import status_line, format_bytes, create_pending_action, escape_html

router = Router(name="bots")


async def _render_bots_list(page: int = 0) -> tuple[str, object]:
    try:
        bots = await api_client.list_bots()
    except ApiError as exc:
        return f"⚠️ تعذر جلب البوتات: {exc.detail}", bots_list_kb([], 0)
    if not bots:
        return "لا توجد بوتات بعد. أنشئ واحدًا جديدًا:", bots_list_kb([], 0)
    running = sum(1 for b in bots if b["status"] == "running")
    text = f"🤖 <b>البوتات</b> ({len(bots)} إجمالًا، {running} تعمل الآن):"
    return text, bots_list_kb(bots, page)


@router.callback_query(F.data == "menu:bots")
async def cb_bots_menu(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    text, kb = await _render_bots_list(0)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("bots:page:"))
async def cb_bots_page(call: CallbackQuery) -> None:
    page = int(call.data.split(":")[2])
    text, kb = await _render_bots_list(page)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


def _bot_detail_text(bot: dict, stats: dict | None) -> str:
    lines = [
        f"🤖 <b>{escape_html(bot['name'])}</b>",
        f"الحالة: {status_line(bot['status'])}",
        f"نوع المصدر: {bot['source_type']}",
        f"نقطة الدخول: <code>{escape_html(bot['entrypoint'])}</code>",
        f"عدد مرات إعادة التشغيل: {bot['restart_count']}",
    ]
    if bot.get("last_error"):
        lines.append(f"⚠️ آخر خطأ: {escape_html(bot['last_error'])[:300]}")
    if stats:
        lines.append("")
        lines.append(
            f"CPU: {stats['cpu_percent']:.1f}%  |  "
            f"RAM: {format_bytes(stats['memory_usage_mb'] * 1024 * 1024)} / "
            f"{format_bytes(stats['memory_limit_mb'] * 1024 * 1024)} "
            f"({stats['memory_percent']:.1f}%)"
        )
        lines.append(f"العمليات: {stats.get('process_count', 0)}")
    return "\n".join(lines)


@router.callback_query(F.data.startswith("bot:open:"))
async def cb_bot_open(call: CallbackQuery, state: FSMContext) -> None:
    bot_id = call.data.split(":", 2)[2]
    await state.update_data(current_bot_id=bot_id)
    try:
        bot = await api_client.get_bot(bot_id)
    except ApiError as exc:
        await call.answer(f"خطأ: {exc.detail}", show_alert=True)
        return
    stats = None
    if bot["status"] == "running":
        try:
            stats = await api_client.get_stats(bot_id)
        except ApiError:
            stats = None
    await call.message.edit_text(
        _bot_detail_text(bot, stats),
        reply_markup=bot_detail_kb(bot_id, bot["status"]),
    )
    await call.answer()


@router.callback_query(F.data.startswith("bot:stats:"))
async def cb_bot_stats(call: CallbackQuery) -> None:
    bot_id = call.data.split(":", 2)[2]
    try:
        bot = await api_client.get_bot(bot_id)
        stats = await api_client.get_stats(bot_id)
    except ApiError as exc:
        await call.answer(f"خطأ: {exc.detail}", show_alert=True)
        return
    if stats is None:
        await call.answer("البوت غير مُشغّل حاليًا، لا توجد إحصائيات لحظية.", show_alert=True)
        return
    await call.message.edit_text(_bot_detail_text(bot, stats), reply_markup=bot_detail_kb(bot_id, bot["status"]))
    await call.answer()


@router.callback_query(F.data.startswith("bot:start:"))
async def cb_bot_start(call: CallbackQuery) -> None:
    bot_id = call.data.split(":", 2)[2]
    try:
        bot = await api_client.start_bot(bot_id)
    except ApiError as exc:
        await call.answer(f"فشل التشغيل: {exc.detail}", show_alert=True)
        return
    await call.answer("✅ جاري التشغيل")
    await call.message.edit_text(_bot_detail_text(bot, None), reply_markup=bot_detail_kb(bot_id, bot["status"]))


@router.callback_query(F.data.startswith("bot:stop:"))
async def cb_bot_stop(call: CallbackQuery) -> None:
    bot_id = call.data.split(":", 2)[2]
    try:
        bot = await api_client.stop_bot(bot_id)
    except ApiError as exc:
        await call.answer(f"فشل الإيقاف: {exc.detail}", show_alert=True)
        return
    await call.answer("⏹ تم الإيقاف")
    await call.message.edit_text(_bot_detail_text(bot, None), reply_markup=bot_detail_kb(bot_id, bot["status"]))


@router.callback_query(F.data.startswith("bot:restart:"))
async def cb_bot_restart(call: CallbackQuery) -> None:
    bot_id = call.data.split(":", 2)[2]
    try:
        bot = await api_client.restart_bot(bot_id)
    except ApiError as exc:
        await call.answer(f"فشل إعادة التشغيل: {exc.detail}", show_alert=True)
        return
    await call.answer("🔁 تمت إعادة التشغيل")
    await call.message.edit_text(_bot_detail_text(bot, None), reply_markup=bot_detail_kb(bot_id, bot["status"]))


@router.callback_query(F.data.startswith("bot:delete:"))
async def cb_bot_delete_ask(call: CallbackQuery) -> None:
    bot_id = call.data.split(":", 2)[2]
    token = create_pending_action("bot_delete", {"bot_id": bot_id})
    await call.message.edit_text(
        "⚠️ هل أنت متأكد من حذف هذا البوت نهائيًا؟ لا يمكن التراجع عن هذا الإجراء.",
        reply_markup=confirm_kb(token),
    )
    await call.answer()
