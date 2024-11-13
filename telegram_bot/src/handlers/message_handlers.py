from telegram import Update
from telegram.ext import ContextTypes
from shared.image_processing.processor import (
    process_image_bytes,
    get_image_dimensions,
    calculate_resize_options,
)
from shared.utils.storage import storage
from shared.utils.telegram_sender import send_resize_options_to_telegram
import logging

# Максимальный размер файла (20 МБ)
MAX_FILE_SIZE = 20 * 1024 * 1024


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик входящих изображений"""
    if not update.effective_user:
        return

    user_id = update.effective_user.id

    try:
        # Получение файла
        photo = (
            update.message.photo[-1]
            if update.message.photo
            else update.message.document
        )
        if not photo:
            await update.message.reply_text("Пожалуйста, отправьте изображение.")
            return

        # Проверка размера файла до скачивания
        if photo.file_size > MAX_FILE_SIZE:
            await update.message.reply_text(
                "Файл слишком большой! Вы можете:\n"
                "1. Использовать команду /link с прямой ссылкой на изображение\n"
                "2. Использовать команду /load для загрузки через веб-интерфейс"
            )
            return

        # Скачиваем файл
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()

        # Получаем размеры изображения
        width, height = get_image_dimensions(image_bytes)

        # Рассчитываем варианты изменения размера
        resize_options = calculate_resize_options(width, height)

        # Сохраняем изображение с правильной структурой
        storage.save_image(
            user_id, {"bytes": image_bytes, "original_size": (width, height)}
        )

        # Отправляем варианты в Telegram
        await send_resize_options_to_telegram(
            user_id, image_bytes, width, height, resize_options
        )

    except Exception as e:
        logging.error(f"Ошибка при обработке изображения: {str(e)}")
        await update.message.reply_text(
            "Произошла ошибка при обработке изображения. Вы можете:\n"
            "1. Использовать команду /link с прямой ссылкой на изображение\n"
            "2. Использовать команду /load для загрузки через веб-интерфейс"
        )
