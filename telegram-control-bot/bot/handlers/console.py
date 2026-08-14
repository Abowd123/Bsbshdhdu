from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards import console_kb, cancel_kb, confirm_kb
from bot.states import ConsoleStates
from bot.utils import create_pending_action, escape_html

router = Router(name="console")


@router.callback_query(F.data.startswith("bot:console:"))
async def cb_console_menu(call: CallbackQuery, state: FSMContext) -> None:
    bot_id = call.data.split(":", 2)[2]
    await state.update_data(current_bot_id=bot_id)
    await call.message.edit_text(
        "🧪 <b>طرفية محدودة</b>\n"
        "تنفّذ أمرًا واحدًا داخل حاوية البوت (نفس صلاحيات الطرفية في لوحة الويب، أوامر مسموحة فقط).",
        reply_markup=console_kb(bot_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("console:run:"))
async def cb_console_run_start(call: CallbackQuery, state: FSMContext) -> None:
    bot_id = call.data.split(":", 2)[2]
    await state.update_data(current_bot_id=bot_id)
    await state.set_state(ConsoleStates.waiting_command)
    await call.message.edit_text(
        "أرسل الأمر المراد تنفيذه (سيُطلب تأكيد قبل التنفيذ فعليًا):",
        reply_markup=cancel_kb(f"bot:console:{bot_id}"),
    )
    await call.answer()


@router.message(ConsoleStates.waiting_command)
async def on_console_command(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    command = (message.text or "").strip()
    if not command:
        await message.answer("أرسل نصًا للأمر.")
        return
    await state.set_state(None)
    token = create_pending_action("console_run", {"bot_id": data["current_bot_id"], "command": command})
    await message.answer(
        f"⚠️ تنفيذ الأمر التالي داخل حاوية البوت:\n<code>{escape_html(command)}</code>\n\nهل تؤكد؟",
        reply_markup=confirm_kb(token),
    )
