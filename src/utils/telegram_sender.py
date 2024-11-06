from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import os
import io
import json

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

async def send_resize_options_to_telegram(
    user_id: int,
    image_bytes: bytes,
    width: int,
    height: int,
    resize_options: list
):
    """Отправляет варианты изменения размера в Telegram"""
    bot = Bot(token=os.getenv('BOT_TOKEN'))
    
    # Создаем клавиатуру с вариантами
    keyboard = []
    for option in resize_options:
        callback_data = json.dumps({
            'action': 'resize',
            'width': option['width'],
            'height': option['height']
        })
        keyboard.append([InlineKeyboardButton(
            f"{option['emoji']} {option['description']}", 
            callback_data=callback_data
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение с вариантами
    await bot.send_message(
        chat_id=user_id,
        text=f"Изображение получено, его размеры: {width}x{height}.\n"
             "Как вы хотите преобразовать его под свой веб-сайт?",
        reply_markup=reply_markup
    ) 