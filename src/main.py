import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from src.image_processor import process_image, process_image_from_link
from src.utils.image_processor import get_image_dimensions, calculate_resize_options, process_image_bytes
from src.utils.token_manager import TokenManager
from src.utils.storage import storage  # Добавляем импорт
import html
import json
import io
import aiohttp

# Загрузка переменных окружения
load_dotenv()

# Создаем экземпляр TokenManager
token_manager = TokenManager()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Изменяем получение списка разрешенных пользователей
ALLOWED_USERS_STR = os.getenv('ALLOWED_USERS', '*')
ALLOWED_USERS = None if ALLOWED_USERS_STR == '*' else list(map(int, ALLOWED_USERS_STR.split(',')))

# Изменяем функцию проверки доступа (добавим новую)
def has_access(user_id: int) -> bool:
    """Проверяет, имеет ли пользователь доступ к боту"""
    return ALLOWED_USERS is None or user_id in ALLOWED_USERS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not has_access(update.effective_user.id):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return
    
    await update.message.reply_text(
        "Привет! Я могу помочь вам:\n"
        "1. Отправьте изображение напрямую\n"
        "2. Используйте команду /link <url> для обработки изображения по ссылке\n"
        "3. Используйте команду /load для загрузки через веб-интерфейс"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not has_access(update.effective_user.id):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return

    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите ссылку после команды /link")
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
        
        # Получаем размеры изображения
        width, height = get_image_dimensions(image_bytes)
        
        # Сохраняем байты изображения в контексте для последующей обработки
        context.user_data['pending_image'] = {
            'bytes': image_bytes,
            'original_size': (width, height)
        }
        
        # Получаем варианты изменения размера
        resize_options = calculate_resize_options(width, height)
        
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
        
        # Обновляем статусное сообщение с вариантами
        await status_message.edit_text(
            f"Изображение получено, его размеры: {width}x{height}.\n"
            "Как вы хотите преобразовать его под свой веб-сайт?",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logging.error(f"Ошибка при обработке изображения по ссылке: {e}")
        await status_message.edit_text("Произошла ошибка при обработке изображения.")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not has_access(update.effective_user.id):
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
            "Файл слишком большой! Вы можете:\n"
            "1. Использовать команду /link с прямой ссылкой на изображение\n"
            "2. Использовать команду /load для загрузки через веб-интерфейс"
        )
        return

    try:
        # Скачиваем файл
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        
        # Получаем размеры изображения
        width, height = get_image_dimensions(image_bytes)
        
        # Сохраняем байты изображения в контексте для последующей обработки
        context.user_data['pending_image'] = {
            'bytes': image_bytes,
            'original_size': (width, height)
        }
        
        # Получаем варианты изменения размера
        resize_options = calculate_resize_options(width, height)
        
        # оздаем клавиатуру с вариантами
        keyboard = []
        for idx, option in enumerate(resize_options):
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
        await update.message.reply_text(
            f"Изображение получено, его размеры: {width}x{height}.\n"
            "Как вы хотите преобразовать его под свой веб-сайт?",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logging.error(f"Ошибка при обработке изображения: {e}")
        await update.message.reply_text(
            "Файл слишком большой! Вы можете:\n"
            "1. Использовать команду /link с прямой ссылкой на изображение\n"
            "2. Использовать команду /load для загрузки через веб-интерфейс"
        )

async def handle_resize_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        # Получаем данные из callback
        data = json.loads(query.data)
        if data['action'] != 'resize':
            return
        
        user_id = update.effective_user.id
        
        # Пытаемся получить изображение из контекста телеграма
        pending_image = context.user_data.get('pending_image')
        
        # Если не нашли в контексте телеграма, проверяем общее хранилище
        if not pending_image:
            pending_image = storage.get_image(user_id)
            # Удаляем изображение из хранилища после получения
            if pending_image:
                storage.delete_image(user_id)
        
        if not pending_image:
            await query.answer("Изображение не найдено, попробуйте загрузить его снова.")
            return
        
        # Обрабатываем изображение с новыми размерами
        result = await process_image_bytes(
            pending_image['bytes'],
            target_width=data['width'],
            target_height=data['height']
        )
        
        # Отправляем обработанное изображение
        await query.message.reply_document(
            document=io.BytesIO(result.bytes),
            filename="processed_image.jpg",
            caption=f"Размер изображения: {data['width']}x{data['height']}\n"
                   f"Исходный размер файла: {result.original_size / 1024:.1f}KB\n"
                   f"Конечный размер файла: {result.final_size / 1024:.1f}KB\n"
                   f"Качество: {result.quality}%"
        )
        
        # Очищаем сохраненное изображение из контекста телеграма, если оно там было
        if 'pending_image' in context.user_data:
            del context.user_data['pending_image']
        
        # Удаляем сообщение с кнопками
        await query.message.delete()
        
    except Exception as e:
        logging.error(f"Ошибка при обработке callback: {e}")
        await query.answer("Произошла ошибка при обработке изображния.")

async def handle_load(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not has_access(update.effective_user.id):
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

async def cleanup_old_files(context: ContextTypes.DEFAULT_TYPE):
    """Периодически очищает старые файлы"""
    storage.cleanup_old_files()

def main():
    # Инициализация бота
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("link", handle_link))
    application.add_handler(CommandHandler("load", handle_load))
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.IMAGE,
        handle_image
    ))
    application.add_handler(CallbackQueryHandler(handle_resize_callback))
    
    # Добавляем задачу очистки старых файлов (каждый час), если job_queue доступен
    if application.job_queue:
        application.job_queue.run_repeating(cleanup_old_files, interval=3600)
    else:
        logging.warning("JobQueue не доступен. Автоматическая очистка файлов отключена.")
    
    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main() 