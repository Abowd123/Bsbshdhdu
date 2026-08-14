from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.api_client import api_client, ApiError
from bot.keyboards import settings_menu_kb, cancel_kb
from bot.states import SettingsStates
from bot.utils import escape_html

router = Router(name="settings_menu")


@router.callback_query(F.data == "settings:profile")
async def cb_profile(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        profile = await api_client.get_profile()
    except ApiError as exc:
        await call.answer(f"خطأ: {exc.detail}", show_alert=True)
        return
    text = (
        "👤 <b>بيانات الحساب</b>\n\n"
        f"البريد: {escape_html(profile['email'])}\n"
        f"اسم المستخدم: {escape_html(profile['username'])}\n"
        f"الصلاحية: {profile['role']}\n"
        f"التحقق بخطوتين: {'مفعّل ✅' if profile['totp_enabled'] else 'غير مفعّل ❌'}\n"
        f"تاريخ الإنشاء: {profile['created_at']}"
    )
    await call.message.edit_text(text, reply_markup=settings_menu_kb())
    await call.answer()


@router.callback_query(F.data == "settings:password")
async def cb_password_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsStates.waiting_current_password)
    await call.message.edit_text(
        "🔒 أرسل <b>كلمة المرور الحالية</b>:\n"
        "⚠️ سيتم حذف رسالتك فور معالجتها للحفاظ على الخصوصية.",
        reply_markup=cancel_kb("menu:settings"),
    )
    await call.answer()


@router.message(SettingsStates.waiting_current_password)
async def on_current_password(message: Message, state: FSMContext) -> None:
    await state.update_data(current_password=message.text)
    await state.set_state(SettingsStates.waiting_new_password)
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer("أرسل الآن <b>كلمة المرور الجديدة</b>:", reply_markup=cancel_kb("menu:settings"))


@router.message(SettingsStates.waiting_new_password)
async def on_new_password(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    new_password = message.text
    try:
        await message.delete()
    except Exception:
        pass
    try:
        await api_client.change_password(data["current_password"], new_password)
    except ApiError as exc:
        await message.answer(f"⚠️ فشل تغيير كلمة المرور: {exc.detail}", reply_markup=settings_menu_kb())
        await state.clear()
        return
    await state.clear()
    await message.answer("✅ تم تغيير كلمة المرور بنجاح.", reply_markup=settings_menu_kb())


@router.callback_query(F.data == "settings:audit")
async def cb_audit_log(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        logs = await api_client.get_audit_logs(limit=20)
    except ApiError as exc:
        await call.answer(f"خطأ: {exc.detail}", show_alert=True)
        return
    if not logs:
        text = "🧾 لا يوجد سجل تدقيق بعد."
    else:
        lines = ["🧾 <b>آخر العمليات الحساسة:</b>\n"]
        for entry in logs:
            lines.append(
                f"• <code>{entry['created_at']}</code> — {escape_html(entry['action'])} "
                f"({escape_html(entry['resource_type'])})"
            )
        text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=settings_menu_kb())
    await call.answer()
