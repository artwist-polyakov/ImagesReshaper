import os
import logging
import aiohttp
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
from image_processor import process_image, process_image_from_url

# Загрузка переменных окружения
load_dotenv()

# Настройка более подробного логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Получение списка разрешенных пользователей из переменных окружения
ALLOWED_USERS = list(map(int, os.getenv('ALLOWED_USERS').split(',')))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return
    
    await update.message.reply_text(
        "Привет! Я могу помочь сконвертировать изображение в прогрессивный JPEG размером менее 400KB.\n\n"
        "Есть два способа использования:\n"
        "1. Отправьте мне изображение напрямую (до 20MB)\n"
        "2. Используйте команду /link с URL изображения для больших файлов\n\n"
        "Пример: /link https://example.com/image.jpg"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return

    # Проверяем, есть ли URL после команды
    if not context.args:
        await update.message.reply_text(
            "Пожалуйста, укажите URL изображения после команды.\n"
            "Пример: /link https://example.com/image.jpg"
        )
        return

    url = context.args[0]
    
    try:
        # Отправляем сообщение о начале обработки
        status_message = await update.message.reply_text(
            "Начинаю загрузку и обработку изображения... Это может занять некоторое время."
        )

        # Обработка изображения по URL
        processed_image_path = await process_image_from_url(url)
        logger.info("Изображение успешно обработано")
        
        # Отправка обработанного изображения
        with open(processed_image_path, 'rb') as img:
            await update.message.reply_document(img)
            logger.info("Обработанное изображение отправлено пользователю")
        
        # Удаление временного файла
        os.remove(processed_image_path)
        await status_message.delete()
        
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка при загрузке изображения по URL: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "Не удалось загрузить изображение по указанной ссылке. "
            "Убедитесь, что ссылка корректна и доступна."
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка при обработке изображения. "
            "Убедитесь, что по ссылке находится поддерживаемый формат изображения."
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
        # Логируем информацию о файле
        file_size = photo.file_size
        logger.info(f"Получен файл размером: {file_size} байт")
        
        if file_size > 20 * 1024 * 1024:  # 20MB
            await update.message.reply_text(
                "Файл слишком большой. Максимальный размер - 20MB."
            )
            return

        # Отправляем сообщение о начале обработки
        status_message = await update.message.reply_text(
            "Начинаю обработку изображения... Это может занять некоторое время."
        )

        # Загрузка файла
        file = await context.bot.get_file(photo.file_id)
        logger.info("Файл получен от Telegram, начинаю обработку")
        
        # Обработка изображения
        processed_image_path = await process_image(file)
        logger.info("Изображение успешно обработано")
        
        # Отправка обработанного изображения
        with open(processed_image_path, 'rb') as img:
            await update.message.reply_document(img)
            logger.info("Обработанное изображение отправлено пользователю")
        
        # Удаление временного файла
        os.remove(processed_image_path)
        await status_message.delete()
        
    except TelegramError as e:
        logger.error(f"Ошибка Telegram при обработке изображения: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка при загрузке изображения. Возможно, файл слишком большой."
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка при обработке изображения. "
            "Убедитесь, что отправляете поддерживаемый формат изображения."
        )

def main():
    # Инициализация бота
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()

    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("link", handle_link))
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.IMAGE,
        handle_image
    ))

    # Запуск бота
    logger.info("Бот запущен и готов к работе")
    application.run_polling()

if __name__ == '__main__':
    main() 