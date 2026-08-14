import io
import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.api_client import api_client, ApiError
from bot.config import settings
from bot.keyboards import create_type_kb, cancel_kb, bot_detail_kb
from bot.states import CreateBotStates

router = Router(name="bot_create")

NAME_RE = re.compile(r"^[a-zA-Z0-9_\- ]+$")


@router.callback_query(F.data == "bot:new")
async def cb_new_bot(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CreateBotStates.choosing_type)
    await call.message.edit_text("اختر نوع مصدر البوت الجديد:", reply_markup=create_type_kb())
    await call.answer()


@router.callback_query(CreateBotStates.choosing_type, F.data.startswith("new:type:"))
async def cb_choose_type(call: CallbackQuery, state: FSMContext) -> None:
    source_type = call.data.split(":", 2)[2]
    await state.update_data(source_type=source_type)
    await state.set_state(CreateBotStates.waiting_name)
    await call.message.edit_text(
        "📝 أرسل <b>اسم البوت</b> (أحرف/أرقام/مسافات/- و _ فقط، بين 2 و64 حرفًا):",
        reply_markup=cancel_kb("menu:bots"),
    )
    await call.answer()


@router.message(CreateBotStates.waiting_name)
async def on_bot_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not (2 <= len(name) <= 64) or not NAME_RE.match(name):
        await message.answer("⚠️ اسم غير صالح. حاول مجددًا (أحرف/أرقام/مسافات/- و _ فقط):")
        return
    await state.update_data(name=name)
    await state.set_state(CreateBotStates.waiting_entrypoint)
    await message.answer(
        "🚀 أرسل <b>ملف نقطة الدخول</b> (مثال: <code>main.py</code>)، أو أرسل نقطة <code>.</code> لاستخدام الافتراضي main.py:",
        reply_markup=cancel_kb("menu:bots"),
    )


@router.message(CreateBotStates.waiting_entrypoint)
async def on_bot_entrypoint(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    entrypoint = "main.py" if text in (".", "") else text
    if ".." in entrypoint or entrypoint.startswith("/") or not entrypoint.endswith(".py"):
        await message.answer("⚠️ نقطة دخول غير صالحة، يجب أن تنتهي بـ .py وبدون مسارات خطرة. حاول مجددًا:")
        return
    data = await state.get_data()
    await state.update_data(entrypoint=entrypoint)
    await state.set_state(CreateBotStates.waiting_source)

    source_type = data["source_type"]
    if source_type == "git":
        await message.answer("🔗 أرسل الآن <b>رابط مستودع Git</b>:", reply_markup=cancel_kb("menu:bots"))
    elif source_type == "zip":
        await message.answer("🗜 أرسل الآن <b>ملف ZIP</b> يحتوي على كود البوت:", reply_markup=cancel_kb("menu:bots"))
    else:
        await message.answer("📄 أرسل الآن <b>ملف .py</b> الخاص بالبوت:", reply_markup=cancel_kb("menu:bots"))


@router.message(CreateBotStates.waiting_source, F.text, F.text.regexp(r"^\S+$"))
async def on_bot_source_git(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data["source_type"] != "git":
        await message.answer("⚠️ هذا النوع يتطلب رفع ملف وليس نصًا. أرسل الملف المطلوب.")
        return
    git_url = message.text.strip()
    await _create_and_finish(message, state, git_url=git_url)


@router.message(CreateBotStates.waiting_source, F.document)
async def on_bot_source_file(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data["source_type"] == "git":
        await message.answer("⚠️ هذا النوع يتطلب رابط Git نصي وليس ملفًا.")
        return
    doc = message.document
    expected_ext = ".zip" if data["source_type"] == "zip" else ".py"
    if not doc.file_name.endswith(expected_ext):
        await message.answer(f"⚠️ الملف يجب أن يكون بامتداد {expected_ext}. أعد الإرسال:")
        return
    if doc.file_size and doc.file_size > settings.MAX_TELEGRAM_FILE_MB * 1024 * 1024:
        await message.answer("⚠️ الملف أكبر من الحد المسموح.")
        return
    file = await message.bot.get_file(doc.file_id)
    buf = io.BytesIO()
    await message.bot.download_file(file.file_path, destination=buf)
    await _create_and_finish(message, state, file_name=doc.file_name, file_bytes=buf.getvalue())


async def _create_and_finish(
    message: Message, state: FSMContext, git_url: str | None = None,
    file_name: str | None = None, file_bytes: bytes | None = None,
) -> None:
    data = await state.get_data()
    try:
        bot = await api_client.create_bot(
            name=data["name"], source_type=data["source_type"],
            entrypoint=data["entrypoint"], git_url=git_url,
        )
    except ApiError as exc:
        await message.answer(f"⚠️ فشل إنشاء البوت: {exc.detail}")
        return

    if file_name and file_bytes is not None:
        try:
            await api_client.upload_bot_file(bot["id"], file_name, file_bytes)
        except ApiError as exc:
            await message.answer(f"⚠️ تم إنشاء البوت لكن فشل رفع الملف: {exc.detail}")
            await state.clear()
            return

    await state.clear()
    await message.answer(
        f"✅ تم إنشاء البوت <b>{bot['name']}</b> بنجاح.",
        reply_markup=bot_detail_kb(bot["id"], bot["status"]),
    )
