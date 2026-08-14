import io

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, BufferedInputFile

from bot.api_client import api_client, ApiError
from bot.keyboards import files_list_kb, file_actions_kb, confirm_kb, back_to_bot_kb, cancel_kb
from bot.states import FileStates
from bot.utils import escape_html, create_pending_action, truncate_for_telegram

router = Router(name="files")

MAX_INLINE_EDIT_BYTES = 100_000  # حد أقصى لتحرير ملف نصي مباشرة داخل تيليجرام


def _join(path: str, name: str) -> str:
    return f"{path}/{name}" if path else name


def _parent(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


async def _render_dir(state: FSMContext, bot_id: str, path: str, page: int = 0) -> tuple[str, object]:
    try:
        entries = await api_client.list_files(bot_id, path)
    except ApiError as exc:
        return f"⚠️ تعذر قراءة المجلد: {exc.detail}", back_to_bot_kb(bot_id)
    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    await state.update_data(current_bot_id=bot_id, current_path=path, file_entries=entries, file_page=page)
    title = f"📁 <code>/{escape_html(path)}</code>" if path else "📁 <code>/ (جذر البوت)</code>"
    if not entries:
        title += "\n\n(مجلد فارغ)"
    return title, files_list_kb(entries, page, bot_id, has_parent=bool(path))


@router.callback_query(F.data.startswith("bot:files:"))
async def cb_open_files(call: CallbackQuery, state: FSMContext) -> None:
    bot_id = call.data.split(":", 2)[2]
    text, kb = await _render_dir(state, bot_id, "")
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("fl:page:"))
async def cb_files_page(call: CallbackQuery, state: FSMContext) -> None:
    page = int(call.data.split(":")[2])
    data = await state.get_data()
    text, kb = await _render_dir(state, data["current_bot_id"], data.get("current_path", ""), page)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "fl:up")
async def cb_files_up(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    new_path = _parent(data.get("current_path", ""))
    text, kb = await _render_dir(state, data["current_bot_id"], new_path)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "fl:back")
async def cb_files_back(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    text, kb = await _render_dir(state, data["current_bot_id"], data.get("current_path", ""), data.get("file_page", 0))
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("fl:o:"))
async def cb_file_open(call: CallbackQuery, state: FSMContext) -> None:
    idx = int(call.data.split(":")[2])
    data = await state.get_data()
    entries = data.get("file_entries", [])
    if idx >= len(entries):
        await call.answer("انتهت صلاحية هذه القائمة، جاري التحديث…", show_alert=True)
        text, kb = await _render_dir(state, data["current_bot_id"], data.get("current_path", ""))
        await call.message.edit_text(text, reply_markup=kb)
        return
    entry = entries[idx]
    await state.update_data(selected_idx=idx)
    icon = "📁" if entry["is_dir"] else "📄"
    size = f"{entry['size']} بايت" if not entry["is_dir"] else ""
    await call.message.edit_text(
        f"{icon} <b>{escape_html(entry['name'])}</b>\n{size}",
        reply_markup=file_actions_kb(idx, entry["is_dir"], data["current_bot_id"]),
    )
    await call.answer()


@router.callback_query(F.data.startswith("fl:enter:"))
async def cb_file_enter(call: CallbackQuery, state: FSMContext) -> None:
    idx = int(call.data.split(":")[2])
    data = await state.get_data()
    entries = data.get("file_entries", [])
    entry = entries[idx]
    new_path = _join(data.get("current_path", ""), entry["name"])
    text, kb = await _render_dir(state, data["current_bot_id"], new_path)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("fl:dl:"))
async def cb_file_download(call: CallbackQuery, state: FSMContext) -> None:
    idx = int(call.data.split(":")[2])
    data = await state.get_data()
    entries = data.get("file_entries", [])
    entry = entries[idx]
    full_path = _join(data.get("current_path", ""), entry["name"])
    await call.answer("⏳ جاري التحميل…")
    try:
        content = await api_client.download_file(data["current_bot_id"], full_path)
    except ApiError as exc:
        await call.message.answer(f"⚠️ فشل التحميل: {exc.detail}")
        return
    await call.message.answer_document(BufferedInputFile(content, filename=entry["name"]))


@router.callback_query(F.data.startswith("fl:edit:"))
async def cb_file_edit_start(call: CallbackQuery, state: FSMContext) -> None:
    idx = int(call.data.split(":")[2])
    data = await state.get_data()
    entries = data.get("file_entries", [])
    entry = entries[idx]
    if entry["size"] > MAX_INLINE_EDIT_BYTES:
        await call.answer("الملف كبير جدًا للتعديل السريع داخل تيليجرام.", show_alert=True)
        return
    full_path = _join(data.get("current_path", ""), entry["name"])
    try:
        content = await api_client.read_file(data["current_bot_id"], full_path)
    except ApiError as exc:
        await call.answer(f"خطأ: {exc.detail}", show_alert=True)
        return
    await state.update_data(edit_path=full_path)
    await state.set_state(FileStates.waiting_edit_content)
    body = truncate_for_telegram(content, 3500)
    await call.message.edit_text(
        f"✏️ محتوى <code>{escape_html(entry['name'])}</code> حاليًا:\n\n<pre>{escape_html(body)}</pre>\n\n"
        "أرسل الآن النص الكامل الجديد للملف كرسالة واحدة، أو ألغِ العملية:",
        reply_markup=cancel_kb("fl:back"),
    )
    await call.answer()


@router.message(FileStates.waiting_edit_content)
async def on_file_edit_content(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    path = data["edit_path"]
    try:
        await api_client.write_file(data["current_bot_id"], path, message.text or "")
    except ApiError as exc:
        await message.answer(f"⚠️ فشل الحفظ: {exc.detail}")
        return
    await state.set_state(None)
    await message.answer(f"✅ تم حفظ <code>{escape_html(path)}</code>.")
    text, kb = await _render_dir(state, data["current_bot_id"], data.get("current_path", ""), data.get("file_page", 0))
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "fl:upload")
async def cb_file_upload_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FileStates.waiting_upload)
    await call.message.edit_text(
        "⬆️ أرسل الآن الملف (كـ Document) الذي تريد رفعه/استبداله في هذا المجلد.\n"
        "ملاحظة: رفع ملف ZIP في جذر البوت سيُفكّ ضغطه تلقائيًا في مجلد البوت.",
        reply_markup=cancel_kb("fl:back"),
    )
    await call.answer()


@router.message(FileStates.waiting_upload, F.document)
async def on_file_upload(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    doc = message.document
    from bot.config import settings
    if doc.file_size and doc.file_size > settings.MAX_TELEGRAM_FILE_MB * 1024 * 1024:
        await message.answer("⚠️ الملف أكبر من الحد المسموح.")
        return
    file = await message.bot.get_file(doc.file_id)
    buf = io.BytesIO()
    await message.bot.download_file(file.file_path, destination=buf)
    target_name = _join(data.get("current_path", ""), doc.file_name)
    try:
        await api_client.upload_bot_file(data["current_bot_id"], target_name, buf.getvalue())
    except ApiError as exc:
        await message.answer(f"⚠️ فشل الرفع: {exc.detail}")
        return
    await state.set_state(None)
    await message.answer(f"✅ تم رفع <code>{escape_html(doc.file_name)}</code>.")
    text, kb = await _render_dir(state, data["current_bot_id"], data.get("current_path", ""), data.get("file_page", 0))
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("fl:rename:"))
async def cb_file_rename_start(call: CallbackQuery, state: FSMContext) -> None:
    idx = int(call.data.split(":")[2])
    await state.update_data(selected_idx=idx)
    await state.set_state(FileStates.waiting_rename)
    await call.message.edit_text("🏷 أرسل الاسم الجديد (بدون مسارات):", reply_markup=cancel_kb("fl:back"))
    await call.answer()


@router.message(FileStates.waiting_rename)
async def on_file_rename(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    entry = data["file_entries"][data["selected_idx"]]
    full_path = _join(data.get("current_path", ""), entry["name"])
    new_name = (message.text or "").strip()
    try:
        await api_client.rename_file(data["current_bot_id"], full_path, new_name)
    except ApiError as exc:
        await message.answer(f"⚠️ فشل: {exc.detail}")
        return
    await state.set_state(None)
    await message.answer("✅ تمت إعادة التسمية.")
    text, kb = await _render_dir(state, data["current_bot_id"], data.get("current_path", ""), data.get("file_page", 0))
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("fl:move:"))
async def cb_file_move_start(call: CallbackQuery, state: FSMContext) -> None:
    idx = int(call.data.split(":")[2])
    await state.update_data(selected_idx=idx)
    await state.set_state(FileStates.waiting_move)
    await call.message.edit_text(
        "✂️ أرسل المسار الجديد الكامل (نسبةً لجذر البوت)، مثال: <code>archive/old.py</code>",
        reply_markup=cancel_kb("fl:back"),
    )
    await call.answer()


@router.message(FileStates.waiting_move)
async def on_file_move(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    entry = data["file_entries"][data["selected_idx"]]
    full_path = _join(data.get("current_path", ""), entry["name"])
    destination = (message.text or "").strip()
    try:
        await api_client.move_file(data["current_bot_id"], full_path, destination)
    except ApiError as exc:
        await message.answer(f"⚠️ فشل النقل: {exc.detail}")
        return
    await state.set_state(None)
    await message.answer("✅ تم النقل.")
    text, kb = await _render_dir(state, data["current_bot_id"], data.get("current_path", ""), data.get("file_page", 0))
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("fl:copy:"))
async def cb_file_copy_start(call: CallbackQuery, state: FSMContext) -> None:
    idx = int(call.data.split(":")[2])
    await state.update_data(selected_idx=idx)
    await state.set_state(FileStates.waiting_copy)
    await call.message.edit_text(
        "📋 أرسل مسار النسخة الجديدة الكامل (نسبةً لجذر البوت)، مثال: <code>backup/old.py</code>",
        reply_markup=cancel_kb("fl:back"),
    )
    await call.answer()


@router.message(FileStates.waiting_copy)
async def on_file_copy(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    entry = data["file_entries"][data["selected_idx"]]
    full_path = _join(data.get("current_path", ""), entry["name"])
    destination = (message.text or "").strip()
    try:
        await api_client.copy_file(data["current_bot_id"], full_path, destination)
    except ApiError as exc:
        await message.answer(f"⚠️ فشل النسخ: {exc.detail}")
        return
    await state.set_state(None)
    await message.answer("✅ تم النسخ.")
    text, kb = await _render_dir(state, data["current_bot_id"], data.get("current_path", ""), data.get("file_page", 0))
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("fl:del:"))
async def cb_file_delete_ask(call: CallbackQuery, state: FSMContext) -> None:
    idx = int(call.data.split(":")[2])
    data = await state.get_data()
    entry = data["file_entries"][idx]
    full_path = _join(data.get("current_path", ""), entry["name"])
    token = create_pending_action("file_delete", {
        "bot_id": data["current_bot_id"], "path": full_path,
        "dir_path": data.get("current_path", ""), "page": data.get("file_page", 0),
    })
    await call.message.edit_text(
        f"⚠️ هل تريد حذف <code>{escape_html(entry['name'])}</code>؟ لا يمكن التراجع.",
        reply_markup=confirm_kb(token),
    )
    await call.answer()
