import os
import logging
from dotenv import load_dotenv
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
)
from handlers.command_handlers import start_command, link_command, load_command
from handlers.message_handlers import handle_image
from handlers.callback_handlers import handle_resize_callback
from shared.utils.storage import storage

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Получаем список разрешенных пользователей
ALLOWED_USERS_STR = os.getenv("ALLOWED_USERS", "*")
ALLOWED_USERS = (
    None if ALLOWED_USERS_STR == "*" else list(map(int, ALLOWED_USERS_STR.split(",")))
)


def has_access(user_id: int) -> bool:
    """Проверяет, имеет ли пользователь доступ к боту"""
    return ALLOWED_USERS is None or user_id in ALLOWED_USERS


async def cleanup_old_files(context: ContextTypes.DEFAULT_TYPE):
    """Периодически очищает старые файлы"""
    storage.cleanup_old_files()


def main():
    # Инициализация бота
    application = Application.builder().token(os.getenv("BOT_TOKEN")).build()

    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("link", link_command))
    application.add_handler(CommandHandler("load", load_command))
    application.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image)
    )
    application.add_handler(CallbackQueryHandler(handle_resize_callback))

    # Добавляем задачу очистки старых файлов
    if application.job_queue:
        application.job_queue.run_repeating(cleanup_old_files, interval=3600)
    else:
        logging.warning(
            "JobQueue не доступен. Автоматическая очистка файлов отключена."
        )

    # Запуск бота
    application.run_polling()


if __name__ == "__main__":
    main()
