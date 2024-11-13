from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from shared.utils.token_manager import TokenManager
from shared.utils.storage import storage  # Добавляем импорт storage
import os
import html
import aiohttp
import json
import logging

token_manager = TokenManager()

# Получаем список разрешенных пользователей
ALLOWED_USERS_STR = os.getenv("ALLOWED_USERS", "*")
ALLOWED_USERS = (
    None if ALLOWED_USERS_STR == "*" else list(map(int, ALLOWED_USERS_STR.split(",")))
)


def has_access(user_id: int) -> bool:
    """Проверяет, имеет ли пользователь доступ к боту"""
    return ALLOWED_USERS is None or user_id in ALLOWED_USERS


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    if not update.effective_user or not has_access(update.effective_user.id):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return

    welcome_text = (
        f"Привет, {html.escape(update.effective_user.first_name)}!\n\n"
        "Я помогу вам оптимизировать изображения для веб-сайта.\n"
        "1. Отправьте изображение напрямую\n"
        "2. Используйте команду /link <url> для обработки изображения по ссылке\n"
        "3. Используйте команду /load для загрузки через веб-интерфейс"
    )

    await update.message.reply_text(welcome_text)


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /link"""
    if not update.effective_user or not has_access(update.effective_user.id):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return

    if not context.args:
        await update.message.reply_text(
            "Пожалуйста, укажите ссылку после команды /link"
        )
        return

    url = context.args[0]
    try:
        # Отправляем сообщение о начале обработки
        status_message = await update.message.reply_text("Загружаю изображение...")

        # Скачиваем изображение по ссылке
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await status_message.edit_text("Не удалось загрузить изображение")
                    return
                image_bytes = await response.read()

        # Получаем размеры и варианты изменения размера
        from shared.image_processing.processor import (
            get_image_dimensions,
            calculate_resize_options,
        )

        width, height = get_image_dimensions(image_bytes)
        resize_options = calculate_resize_options(width, height)

        # Сохраняем изображение
        storage.save_image(
            update.effective_user.id,
            {"bytes": image_bytes, "original_size": (width, height)},
        )

        # Создаем клавиатуру с вариантами
        keyboard = []
        for option in resize_options:
            callback_data = json.dumps(
                {
                    "action": "resize",
                    "width": option["width"],
                    "height": option["height"],
                }
            )
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{option['emoji']} {option['description']}",
                        callback_data=callback_data,
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Обновляем статусное сообщение с вариантами
        await status_message.edit_text(
            f"Изображение получено, его размеры: {width}x{height}.\n"
            "Как вы хотите преобразовать его под свой веб-сайт?",
            reply_markup=reply_markup,
        )

    except Exception as e:
        await status_message.edit_text(f"Ошибка при обработке изображения: {str(e)}")


async def load_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /load"""
    if not update.effective_user or not has_access(update.effective_user.id):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return

    try:
        # Создаем токен для пользователя
        token = token_manager.create_token(update.effective_user.id)
        webapp_url = os.getenv("WEBAPP_URL", "http://localhost:8000")

        # Формируем URL с токеном
        url = f"{webapp_url}?token={token}"

        # Создаем клавиатуру с кнопкой-ссылкой
        keyboard = [[InlineKeyboardButton("Загрузить изображение", url=url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем сообщение, которое удалится через час
        message = await update.message.reply_text(
            "Нажмите на кнопку ниже для загрузки изображения.\n\n"
            "Ссылка действительна в течение 1 часа.",
            reply_markup=reply_markup,
        )

        # Планируем удаление сообщения через час
        context.job_queue.run_once(
            lambda ctx: ctx.data.delete(), 3600, data=message  # 1 час в секундах
        )

    except Exception as e:
        await update.message.reply_text(f"Ошибка при создании ссылки: {str(e)}")
