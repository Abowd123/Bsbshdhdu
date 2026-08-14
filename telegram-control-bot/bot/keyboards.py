from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import settings
from bot.utils import status_line


def main_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🤖 البوتات", callback_data="menu:bots")
    b.button(text="⚙️ الإعدادات", callback_data="menu:settings")
    b.adjust(1)
    return b.as_markup()


def _pagination_row(b: InlineKeyboardBuilder, page: int, total_pages: int, prefix: str) -> None:
    if total_pages <= 1:
        return
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="◀️", callback_data=f"{prefix}:{page - 1}"))
    row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        row.append(InlineKeyboardButton(text="▶️", callback_data=f"{prefix}:{page + 1}"))
    b.row(*row)


def bots_list_kb(bots: list[dict], page: int) -> InlineKeyboardMarkup:
    page_size = settings.PAGE_SIZE
    total_pages = max(1, (len(bots) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    chunk = bots[page * page_size: (page + 1) * page_size]

    b = InlineKeyboardBuilder()
    for bot in chunk:
        label = f"{status_line(bot['status'])} {bot['name']}"
        b.row(InlineKeyboardButton(text=label, callback_data=f"bot:open:{bot['id']}"))
    _pagination_row(b, page, total_pages, "bots:page")
    b.row(InlineKeyboardButton(text="➕ بوت جديد", callback_data="bot:new"))
    b.row(InlineKeyboardButton(text="🔄 تحديث", callback_data=f"bots:page:{page}"))
    b.row(InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="menu:main"))
    return b.as_markup()


def bot_detail_kb(bot_id: str, status: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if status == "running":
        b.button(text="⏹ إيقاف", callback_data=f"bot:stop:{bot_id}")
        b.button(text="🔁 إعادة تشغيل", callback_data=f"bot:restart:{bot_id}")
    else:
        b.button(text="▶️ تشغيل", callback_data=f"bot:start:{bot_id}")
    b.button(text="📊 إحصائيات", callback_data=f"bot:stats:{bot_id}")
    b.button(text="📜 السجلات", callback_data=f"bot:logs:{bot_id}")
    b.button(text="📁 الملفات", callback_data=f"bot:files:{bot_id}")
    b.button(text="🧪 طرفية", callback_data=f"bot:console:{bot_id}")
    b.button(text="🔑 متغيرات البيئة", callback_data=f"bot:env:{bot_id}")
    b.button(text="🗑 حذف البوت", callback_data=f"bot:delete:{bot_id}")
    b.button(text="↩️ رجوع للقائمة", callback_data="menu:bots")
    b.adjust(2, 2, 2, 1, 1)
    return b.as_markup()


def back_to_bot_kb(bot_id: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="↩️ رجوع لتفاصيل البوت", callback_data=f"bot:open:{bot_id}")
    return b.as_markup()


def confirm_kb(token: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ تأكيد", callback_data=f"confirm:yes:{token}")
    b.button(text="❌ إلغاء", callback_data=f"confirm:no:{token}")
    b.adjust(2)
    return b.as_markup()


def create_type_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📄 ملف .py واحد", callback_data="new:type:single_file")
    b.button(text="🗜 ملف ZIP", callback_data="new:type:zip")
    b.button(text="🔗 رابط Git", callback_data="new:type:git")
    b.button(text="❌ إلغاء", callback_data="menu:bots")
    b.adjust(1)
    return b.as_markup()


def logs_kb(bot_id: str, live_active: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔄 تحديث", callback_data=f"log:refresh:{bot_id}")
    if live_active:
        b.button(text="⏹ إيقاف التحديث التلقائي", callback_data=f"log:live_off:{bot_id}")
    else:
        b.button(text="▶️ تحديث تلقائي (4 ث)", callback_data=f"log:live_on:{bot_id}")
    b.button(text="↩️ رجوع", callback_data=f"bot:open:{bot_id}")
    b.adjust(2, 1)
    return b.as_markup()


def env_kb(bot_id: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ تعديل المتغيرات", callback_data=f"env:edit:{bot_id}")
    b.button(text="↩️ رجوع", callback_data=f"bot:open:{bot_id}")
    b.adjust(1)
    return b.as_markup()


def files_list_kb(entries: list[dict], page: int, bot_id: str, has_parent: bool) -> InlineKeyboardMarkup:
    page_size = settings.PAGE_SIZE
    total_pages = max(1, (len(entries) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    chunk = list(enumerate(entries))[page * page_size: (page + 1) * page_size]

    b = InlineKeyboardBuilder()
    for idx, entry in chunk:
        icon = "📁" if entry["is_dir"] else "📄"
        b.row(InlineKeyboardButton(text=f"{icon} {entry['name']}", callback_data=f"fl:o:{idx}"))
    _pagination_row(b, page, total_pages, "fl:page")

    nav_row = []
    if has_parent:
        nav_row.append(InlineKeyboardButton(text="⬆️ المجلد الأعلى", callback_data="fl:up"))
    nav_row.append(InlineKeyboardButton(text="⬆️ رفع ملف هنا", callback_data="fl:upload"))
    b.row(*nav_row)
    b.row(InlineKeyboardButton(text="↩️ رجوع لتفاصيل البوت", callback_data=f"bot:open:{bot_id}"))
    return b.as_markup()


def file_actions_kb(idx: int, is_dir: bool, bot_id: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if is_dir:
        b.button(text="📂 فتح المجلد", callback_data=f"fl:enter:{idx}")
    else:
        b.button(text="⬇️ تحميل", callback_data=f"fl:dl:{idx}")
        b.button(text="✏️ تعديل سريع", callback_data=f"fl:edit:{idx}")
    b.button(text="✂️ نقل", callback_data=f"fl:move:{idx}")
    b.button(text="📋 نسخ", callback_data=f"fl:copy:{idx}")
    b.button(text="🏷 إعادة تسمية", callback_data=f"fl:rename:{idx}")
    b.button(text="🗑 حذف", callback_data=f"fl:del:{idx}")
    b.button(text="↩️ رجوع لقائمة الملفات", callback_data="fl:back")
    b.adjust(2, 2, 1, 1)
    return b.as_markup()


def console_kb(bot_id: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="▶️ تنفيذ أمر", callback_data=f"console:run:{bot_id}")
    b.button(text="↩️ رجوع", callback_data=f"bot:open:{bot_id}")
    b.adjust(1)
    return b.as_markup()


def settings_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="👤 بيانات الحساب", callback_data="settings:profile")
    b.button(text="🔒 تغيير كلمة المرور", callback_data="settings:password")
    b.button(text="🧾 سجل التدقيق", callback_data="settings:audit")
    b.button(text="🏠 القائمة الرئيسية", callback_data="menu:main")
    b.adjust(1)
    return b.as_markup()


def cancel_kb(back_callback: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="❌ إلغاء", callback_data=back_callback)
    return b.as_markup()
