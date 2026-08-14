from aiogram import Router
from aiogram.types import Message, CallbackQuery

from bot.keyboards import main_menu_kb

router = Router(name="fallback")


@router.message()
async def fallback_message(message: Message) -> None:
    await message.answer(
        "لم أفهم هذا الطلب. استخدم /start للعودة إلى القائمة الرئيسية.",
        reply_markup=main_menu_kb(),
    )


@router.callback_query()
async def fallback_callback(call: CallbackQuery) -> None:
    await call.answer("انتهت صلاحية هذا الزر أو غير معروف.", show_alert=True)
