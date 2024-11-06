from telegram import Bot
import os
import io

async def send_processed_image_to_telegram(user_id: int, image_bytes: bytes):
    """Отправляет обработанное изображение пользователю в Telegram"""
    bot = Bot(token=os.getenv('BOT_TOKEN'))
    
    # Создаем объект файла из байтов
    file = io.BytesIO(image_bytes)
    file.name = "processed_image.jpg"
    
    # Отправляем файл пользователю
    await bot.send_document(
        chat_id=user_id,
        document=file,
        caption="Вот ваше обработанное изображение!"
    ) 