import os
import logging
import tempfile
import aiohttp
from PIL import Image
from telegram import File
from io import BytesIO

logger = logging.getLogger(__name__)

async def process_image(tg_file: File) -> str:
    # Создание временного файла для входного изображения
    temp_input = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    temp_input.close()
    
    # Создание временного файла для выходного изображения
    temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    temp_output.close()
    
    try:
        logger.info("Начинаю загрузку файла")
        # Загрузка файла
        await tg_file.download_to_drive(temp_input.name)
        logger.info(f"Файл загружен, размер: {os.path.getsize(temp_input.name)} байт")
        
        # Открытие изображения
        with Image.open(temp_input.name) as img:
            logger.info(f"Изображение открыто, размер: {img.size}, режим: {img.mode}")
            
            # Конвертация в RGB если необходимо
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
                logger.info("Изображение конвертировано в RGB")
            
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
                logger.info(f"Сохранено с качеством {quality}, размер: {file_size} байт")
                
                if file_size <= 400 * 1024 or quality <= 5:  # 400KB в байтах
                    break
                
                # Уменьшение качества
                quality -= 5
        
        # Удаление входного временного файла
        os.remove(temp_input.name)
        logger.info("Обработка завершена успешно")
        return temp_output.name
        
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {str(e)}", exc_info=True)
        # Очистка в случае ошибки
        if os.path.exists(temp_input.name):
            os.remove(temp_input.name)
        if os.path.exists(temp_output.name):
            os.remove(temp_output.name)
        raise e

async def process_image_from_url(url: str) -> str:
    """Загружает и обрабатывает изображение по URL."""
    # Создание временного файла для выходного изображения
    temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    temp_output.close()
    
    try:
        logger.info(f"Начинаю загрузку файла по URL: {url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                image_data = await response.read()
                logger.info(f"Файл загружен, размер: {len(image_data)} байт")

        # Открытие изображения из байтов
        with Image.open(BytesIO(image_data)) as img:
            logger.info(f"Изображение открыто, размер: {img.size}, режим: {img.mode}")
            
            # Конвертация в RGB если необходимо
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
                logger.info("Изображение конвертировано в RGB")
            
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
                logger.info(f"Сохранено с качеством {quality}, размер: {file_size} байт")
                
                if file_size <= 400 * 1024 or quality <= 5:  # 400KB в байтах
                    break
                
                # Уменьшение качества
                quality -= 5
        
        logger.info("Обработка завершена успешно")
        return temp_output.name
        
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {str(e)}", exc_info=True)
        if os.path.exists(temp_output.name):
            os.remove(temp_output.name)
        raise e