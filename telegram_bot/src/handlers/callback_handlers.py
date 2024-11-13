from telegram import Update
from telegram.ext import ContextTypes
from shared.utils.storage import storage
from shared.image_processing.processor import process_image_bytes
import json
import logging
import io


async def handle_resize_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов для изменения размера изображения"""
    if not update.callback_query or not update.effective_user:
        return

    query = update.callback_query
    user_id = update.effective_user.id

    try:
        # Получаем данные из callback
        data = json.loads(query.data)

        if data.get("action") != "resize":
            return

        # Получаем параметры изменения размера
        target_width = data.get("width")
        target_height = data.get("height")

        await query.answer()
        # Обновляем сообщение, показывая процесс обработки
        processing_message = await query.edit_message_text("Обрабатываю изображение...")

        # Получаем сохраненное изображение
        image_data = storage.get_image(user_id)
        if not image_data:
            await processing_message.edit_text(
                "Изображение не найдено, попробуйте загрузить его снова"
            )
            return

        # Обрабатываем изображение
        result = await process_image_bytes(
            image_data["bytes"], target_width=target_width, target_height=target_height
        )

        # Отправляем обработанное изображение с информацией о сжатии
        await query.message.reply_document(
            document=io.BytesIO(result.bytes),
            filename="processed_image.jpg",
            caption=(
                f"Размер изображения: {target_width}x{target_height}\n"
                f"Исходный размер файла: {result.original_size // 1024}KB\n"
                f"Конечный размер файла: {result.final_size // 1024}KB\n"
                f"Степень сжатия: {(result.final_size / result.original_size) * 100:.1f}%\n"
                f"Качество: {result.quality}%"
            ),
        )

        # Удаляем сообщение с кнопками и индикацией загрузки
        await processing_message.delete()

        # Очищаем сохраненное изображение
        storage.delete_image(user_id)

    except Exception as e:
        logging.error(f"Ошибка при обработке callback: {str(e)}")
        await query.edit_message_text(f"Ошибка при обработке изображения: {str(e)}")
