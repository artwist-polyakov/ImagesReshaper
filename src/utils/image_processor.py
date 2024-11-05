import os
import tempfile
from PIL import Image
import io

async def process_image_file(input_file_path: str) -> str:
    """Обрабатывает изображение из файла"""
    temp_output = None
    try:
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_output.close()
        
        with Image.open(input_file_path) as img:
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
        if temp_output and os.path.exists(temp_output.name):
            os.remove(temp_output.name)
        raise e

async def process_image_bytes(image_bytes: bytes) -> bytes:
    """Обрабатывает изображение из байтов"""
    temp_input = None
    temp_output = None
    try:
        # Создаем временные файлы
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        
        # Сохраняем байты во временный файл
        temp_input.write(image_bytes)
        temp_input.close()
        temp_output.close()
        
        # Обрабатываем изображение
        processed_path = await process_image_file(temp_input.name)
        
        # Читаем обработанное изображение в байты
        with open(processed_path, 'rb') as f:
            return f.read()
            
    finally:
        # Очищаем временные файлы
        if temp_input and os.path.exists(temp_input.name):
            os.remove(temp_input.name)
        if temp_output and os.path.exists(temp_output.name):
            os.remove(temp_output.name) 