from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.api_client import api_client, ApiError
from bot.keyboards import bots_list_kb
from bot.utils import pop_pending_action, escape_html, truncate_for_telegram
from bot.handlers.files import _render_dir

router = Router(name="confirm")


@router.callback_query(F.data.startswith("confirm:no:"))
async def cb_confirm_no(call: CallbackQuery) -> None:
    token = call.data.split(":", 2)[2]
    pop_pending_action(token)
    await call.message.edit_text("❌ تم الإلغاء.")
    await call.answer()


@router.callback_query(F.data.startswith("confirm:yes:"))
async def cb_confirm_yes(call: CallbackQuery, state: FSMContext) -> None:
    token = call.data.split(":", 2)[2]
    pending = pop_pending_action(token)
    if pending is None:
        await call.answer("⚠️ انتهت صلاحية هذا الإجراء، أعد المحاولة.", show_alert=True)
        return

    if pending.action == "bot_delete":
        bot_id = pending.payload["bot_id"]
        try:
            await api_client.delete_bot(bot_id)
        except ApiError as exc:
            await call.message.edit_text(f"⚠️ فشل الحذف: {exc.detail}")
            await call.answer()
            return
        await call.answer("🗑 تم الحذف")
        try:
            bots = await api_client.list_bots()
        except ApiError:
            bots = []
        await call.message.edit_text("✅ تم حذف البوت.\n\nقائمة البوتات:", reply_markup=bots_list_kb(bots, 0))
        return

    if pending.action == "file_delete":
        bot_id = pending.payload["bot_id"]
        path = pending.payload["path"]
        try:
            await api_client.delete_file(bot_id, path)
        except ApiError as exc:
            await call.message.edit_text(f"⚠️ فشل الحذف: {exc.detail}")
            await call.answer()
            return
        await call.answer("🗑 تم الحذف")
        text, kb = await _render_dir(state, bot_id, pending.payload.get("dir_path", ""), pending.payload.get("page", 0))
        await call.message.edit_text(text, reply_markup=kb)
        return

    if pending.action == "console_run":
        bot_id = pending.payload["bot_id"]
        command = pending.payload["command"]
        try:
            result = await api_client.run_console(bot_id, command)
        except ApiError as exc:
            await call.message.edit_text(f"⚠️ فشل تنفيذ الأمر: {exc.detail}")
            await call.answer()
            return
        await call.answer("✅ تم التنفيذ")
        output = result.get("stdout") or result.get("output") or str(result)
        output = truncate_for_telegram(str(output), 3500)
        await call.message.edit_text(
            f"🧪 نتيجة تنفيذ <code>{escape_html(command)}</code>:\n\n<pre>{escape_html(output)}</pre>"
        )
        return

    await call.answer()
