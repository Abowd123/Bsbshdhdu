from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.keyboards import main_menu_kb, settings_menu_kb

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "👋 أهلًا بك في بوت التحكم الخاص بـ <b>WolfHost</b>.\n"
        "اختر من القائمة أدناه:",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("القائمة الرئيسية:", reply_markup=main_menu_kb())
    await call.answer()


@router.callback_query(F.data == "menu:settings")
async def cb_settings_menu(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("⚙️ الإعدادات:", reply_markup=settings_menu_kb())
    await call.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery) -> None:
    await call.answer()
