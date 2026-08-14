from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.api_client import api_client, ApiError
from bot.keyboards import env_kb, cancel_kb, bot_detail_kb
from bot.states import EnvStates
from bot.utils import escape_html

router = Router(name="env")


@router.callback_query(F.data.startswith("bot:env:"))
async def cb_env_view(call: CallbackQuery, state: FSMContext) -> None:
    bot_id = call.data.split(":", 2)[2]
    await state.update_data(current_bot_id=bot_id)
    try:
        bot = await api_client.get_bot(bot_id)
    except ApiError as exc:
        await call.answer(f"خطأ: {exc.detail}", show_alert=True)
        return
    env_vars = bot.get("env_vars") or {}
    if env_vars:
        body = "\n".join(f"{escape_html(k)}=<code>{escape_html(v)}</code>" for k, v in env_vars.items())
    else:
        body = "(لا توجد متغيرات بيئة بعد)"
    await call.message.edit_text(f"🔑 <b>متغيرات البيئة</b>\n\n{body}", reply_markup=env_kb(bot_id))
    await call.answer()


@router.callback_query(F.data.startswith("env:edit:"))
async def cb_env_edit_start(call: CallbackQuery, state: FSMContext) -> None:
    bot_id = call.data.split(":", 2)[2]
    await state.update_data(current_bot_id=bot_id)
    await state.set_state(EnvStates.waiting_env_text)
    await call.message.edit_text(
        "✏️ أرسل الآن كل المتغيرات دفعة واحدة، كل سطر بصيغة <code>KEY=VALUE</code>.\n"
        "سيتم استبدال كل متغيرات البيئة الحالية بما ترسله (أرسل نصًا فارغًا لمسحها كلها).",
        reply_markup=cancel_kb(f"bot:env:{bot_id}"),
    )
    await call.answer()


@router.message(EnvStates.waiting_env_text)
async def on_env_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    bot_id = data["current_bot_id"]
    raw = message.text or ""
    env_vars: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key:
            env_vars[key] = value.strip()

    try:
        bot = await api_client.update_env(bot_id, env_vars)
    except ApiError as exc:
        await message.answer(f"⚠️ فشل الحفظ: {exc.detail}")
        return
    await state.set_state(None)
    await message.answer(
        f"✅ تم تحديث متغيرات البيئة ({len(env_vars)} متغيّر). قد تحتاج لإعادة تشغيل البوت لتفعيلها.",
        reply_markup=bot_detail_kb(bot_id, bot["status"]),
    )
