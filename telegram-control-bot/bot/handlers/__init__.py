from aiogram import Router

from bot.handlers import (
    start,
    bots,
    bot_create,
    files,
    console,
    env,
    logs,
    settings_menu,
    confirm,
    fallback,
)


def build_root_router() -> Router:
    root = Router(name="root")
    # الترتيب مهم: confirm ومعالجات FSM النصية يجب أن تُفحص قبل fallback العام
    root.include_router(start.router)
    root.include_router(bots.router)
    root.include_router(bot_create.router)
    root.include_router(files.router)
    root.include_router(console.router)
    root.include_router(env.router)
    root.include_router(logs.router)
    root.include_router(settings_menu.router)
    root.include_router(confirm.router)
    root.include_router(fallback.router)  # يجب أن يبقى الأخير دائمًا
    return root
