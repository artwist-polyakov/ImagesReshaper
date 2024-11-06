from telegram import File
from src.utils.image_processor import process_image_file
import tempfile
import os
import requests

async def process_image(tg_file: File) -> str:
    """Обработка изображения из Telegram"""
    temp_input = None
    try:
        # Создание временного файла
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_input.close()
        
        # Загрузка файла
        await tg_file.download_to_drive(temp_input.name)
        
        # Обработка изображения
        return await process_image_file(temp_input.name)
        
    finally:
        if temp_input and os.path.exists(temp_input.name):
            os.remove(temp_input.name)

async def process_image_from_link(url: str) -> str:
    """Обработка изображения по ссылке"""
    temp_input = None
    try:
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            return "Не удалось загрузить файл по ссылке"

        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            return "По ссылке находится не изображение"

        # Создаем временный файл
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_input.write(response.content)
        temp_input.close()

        # Обрабатываем изображение
        return await process_image_file(temp_input.name)

    except Exception as e:
        return f"Произошла ошибка при обработке изображения: {str(e)}"
        
    finally:
        if temp_input and os.path.exists(temp_input.name):
            os.remove(temp_input.name)