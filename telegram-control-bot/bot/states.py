from aiogram.fsm.state import State, StatesGroup


class CreateBotStates(StatesGroup):
    choosing_type = State()
    waiting_name = State()
    waiting_entrypoint = State()
    waiting_source = State()  # ملف .py / ZIP / رابط Git حسب النوع المختار


class EnvStates(StatesGroup):
    waiting_env_text = State()


class ConsoleStates(StatesGroup):
    waiting_command = State()


class FileStates(StatesGroup):
    waiting_edit_content = State()
    waiting_upload = State()
    waiting_rename = State()
    waiting_move = State()
    waiting_copy = State()


class SettingsStates(StatesGroup):
    waiting_current_password = State()
    waiting_new_password = State()
