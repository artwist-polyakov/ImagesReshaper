import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from image_processor import process_image

# Загрузка переменных окружения
load_dotenv()

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
        "Привет! Отправь мне изображение, и я конвертирую его в прогрессивный JPEG размером менее 400KB."
    )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return

    # Получение файла
    photo = update.message.photo[-1] if update.message.photo else update.message.document
    if not photo:
        await update.message.reply_text("Пожалуйста, отправьте изображение.")
        return

    try:
        # Загрузка файла
        file = await context.bot.get_file(photo.file_id)
        
        # Обработка изображения
        processed_image_path = await process_image(file)
        
        # Отправка обработанного изображения
        with open(processed_image_path, 'rb') as img:
            await update.message.reply_document(img)
        
        # Удаление временного файла
        os.remove(processed_image_path)
        
    except Exception as e:
        logging.error(f"Ошибка при обработке изображения: {e}")
        await update.message.reply_text("Произошла ошибка при обработке изображения.")

def main():
    # Инициализация бота
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()

    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.IMAGE,
        handle_image
    ))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main() 