import os
import tempfile
from PIL import Image
from telegram import File

async def process_image(tg_file: File) -> str:
    # Создание временного файла для входного изображения
    temp_input = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    temp_input.close()
    
    # Создание временного файла для выходного изображения
    temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    temp_output.close()
    
    try:
        # Загрузка файла
        await tg_file.download_to_drive(temp_input.name)
        
        # Открытие изображения
        with Image.open(temp_input.name) as img:
            # Конвертация в RGB если необходимо
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Начальное качество
            quality = 95
            
            while True:
                # Сохранение с текущим качеством
                img.save(
                    temp_output.name,
                    'JPEG',
                    quality=quality,
                    optimize=True,
                    progressive=True
                )
                
                # Проверка размера файла
                file_size = os.path.getsize(temp_output.name)
                
                if file_size <= 400 * 1024 or quality <= 5:  # 400KB в байтах
                    break
                
                # Уменьшение качества
                quality -= 5
        
        # Удаление входного временного файла
        os.remove(temp_input.name)
        return temp_output.name
        
    except Exception as e:
        # Очистка в случае ошибки
        if os.path.exists(temp_input.name):
            os.remove(temp_input.name)
        if os.path.exists(temp_output.name):
            os.remove(temp_output.name)
        raise e 