import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from image_processor import process_image, process_image_from_link
from utils.token_manager import TokenManager
import html  # Добавьте этот импорт в начало файла

# Загрузка переменных окружения
load_dotenv()

# Создаем экземпляр TokenManager
token_manager = TokenManager()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Получение списка разрешенных пользователей из переменных окружения
ALLOWED_USERS = list(map(int, os.getenv('ALLOWED_USERS').split(',')))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return
    
    await update.message.reply_text(
        "Привет! Я могу помочь вам:\n"
        "1. Отправьте изображение напрямую\n"
        "2. Используйте команду /link <url> для обработки изображения по ссылке"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return

    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите ссылку после команды /link")
        return

    url = context.args[0]
    try:
        # Отправляем сообщение о начале обработки
        status_message = await update.message.reply_text("Обрабатываю изображение...")
        
        processed_image_path = await process_image_from_link(url)
        
        # Если вернулась строка с ошибкой
        if isinstance(processed_image_path, str) and not os.path.exists(processed_image_path):
            await status_message.edit_text(processed_image_path)
            return

        # Отправка обработанного изображения
        with open(processed_image_path, 'rb') as img:
            await update.message.reply_document(img)
        
        await status_message.delete()
        
        # Удаление временного файла
        os.remove(processed_image_path)
        
    except Exception as e:
        logging.error(f"Ошибка при обработке изображения по ссылке: {e}")
        await status_message.edit_text("Произошла ошибка при обработке изображения.")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return

    # Получение файла
    photo = update.message.photo[-1] if update.message.photo else update.message.document
    if not photo:
        await update.message.reply_text("Пожалуйста, отправьте изображение.")
        return

    # Проверка размера файла (20 МБ = 20 * 1024 * 1024 байт)
    if photo.file_size > 20 * 1024 * 1024:
        await update.message.reply_text(
            "Файл слишком большой! Для больших изображений используйте команду /link с прямой ссылкой на изображение."
        )
        return

    try:
        # Отправляем сообщение о начале обработки
        status_message = await update.message.reply_text("Обрабатываю изображение...")
        
        # Загрузка файла
        file = await context.bot.get_file(photo.file_id)
        
        # Обработка изображения
        processed_image_path = await process_image(file)
        
        # Отправка обработанного изображения
        with open(processed_image_path, 'rb') as img:
            await update.message.reply_document(img)
        
        await status_message.delete()
        
        # Удаление временного файла
        os.remove(processed_image_path)
        
    except Exception as e:
        logging.error(f"Ошибка при обработке изображения: {e}")
        await status_message.edit_text("Произошла ошибка при обработке изображения.")

async def handle_load(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return
    
    try:
        # Создаем токен для пользователя
        token = token_manager.create_token(update.effective_user.id)
        webapp_url = os.getenv('WEBAPP_URL', 'http://localhost:8000')
        
        # Формируем URL с токеном
        url = f"{webapp_url}?token={token}"
        
        # Создаем клавиатуру с кнопкой-ссылкой
        keyboard = [[InlineKeyboardButton("Загрузить изображение", url=url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Нажмите на кнопку ниже для загрузки изображения.\n\n"
            "Ссылка действительна в течение 1 часа.",
            reply_markup=reply_markup
        )
    except Exception as e:
        logging.error(f"Ошибка при создании ссылки: {e}")
        await update.message.reply_text("Произошла ошибка при создании ссылки.")

def main():
    # Инициализация бота и token manager
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("link", handle_link))
    application.add_handler(CommandHandler("load", handle_load))  # Новый обработчик
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.IMAGE,
        handle_image
    ))
    
    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main() 