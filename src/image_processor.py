import os
import tempfile
from PIL import Image
from telegram import File
import requests
from urllib.parse import urlparse
import io

async def process_image(tg_file: File) -> str:
    temp_input = None
    temp_output = None
    
    try:
        # Создание временных файлов
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_input.close()
        temp_output.close()
        
        # Загрузка и обработка файла
        await tg_file.download_to_drive(temp_input.name)
        
        with Image.open(temp_input.name) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            quality = 95
            while True:
                img.save(
                    temp_output.name,
                    'JPEG',
                    quality=quality,
                    optimize=True,
                    progressive=True
                )
                
                file_size = os.path.getsize(temp_output.name)
                if file_size <= 400 * 1024 or quality <= 5:
                    break
                quality -= 5
        
        return temp_output.name
        
    except Exception as e:
        raise e
    
    finally:
        # Гарантированная очистка временных файлов
        if temp_input and os.path.exists(temp_input.name):
            os.remove(temp_input.name)
        # Не удаляем temp_output, так как он нужен для отправки
        # Его нужно будет удалить после отправки в основном обработчике

async def process_image_from_link(url: str) -> str:
    temp_input = None
    temp_output = None
    
    try:
        # Проверка URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return "Пожалуйста, предоставьте корректную ссылку на изображение"

        response = requests.get(url, stream=True)
        if response.status_code != 200:
            return "Не удалось загрузить файл по ссылке"

        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            return "По ссылке находится не изображение"

        # Создаем временные файлы
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        
        # Сохраняем загруженное изображение во временный файл
        temp_input.write(response.content)
        temp_input.close()
        temp_output.close()

        # Используем ту же логику обработки, что и в process_image
        with Image.open(temp_input.name) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            quality = 95
            while True:
                img.save(
                    temp_output.name,
                    'JPEG',
                    quality=quality,
                    optimize=True,
                    progressive=True
                )
                
                file_size = os.path.getsize(temp_output.name)
                if file_size <= 400 * 1024 or quality <= 5:
                    break
                quality -= 5

        return temp_output.name

    except Exception as e:
        return f"Произошла ошибка при обработке изображения: {str(e)}"
        
    finally:
        # Гарантированная очистка временных файлов
        if temp_input and os.path.exists(temp_input.name):
            os.remove(temp_input.name)
        # temp_output будет удален после отправки в основном обработчике