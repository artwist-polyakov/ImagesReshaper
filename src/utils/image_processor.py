from PIL import Image
import io
import os
import aiohttp
from telegram import File
import logging
from dataclasses import dataclass
from typing import Tuple, List
import asyncio

@dataclass
class ProcessingResult:
    bytes: bytes
    original_size: int
    final_size: int
    quality: int

async def check_quality(img: Image.Image, quality: int) -> Tuple[int, int, bytes]:
    """Асинхронно проверяет размер изображения при заданном качестве"""
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    size = output.tell()
    return quality, size, output.getvalue()

async def process_image_bytes(image_bytes: bytes) -> ProcessingResult:
    """Обрабатывает изображение, оптимизируя размер файла"""
    max_file_size = int(os.getenv('MAX_PROCESSED_FILE_SIZE', 400 * 1024))
    original_size = len(image_bytes)
    
    if original_size <= max_file_size:
        return ProcessingResult(
            bytes=image_bytes,
            original_size=original_size,
            final_size=original_size,
            quality=100
        )
    
    with Image.open(io.BytesIO(image_bytes)) as img:
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Асинхронно проверяем все контрольные точки качества
        control_points = [95, 80, 60, 40, 20, 5]
        tasks = [check_quality(img, q) for q in control_points]
        quality_sizes = await asyncio.gather(*tasks)
        quality_sizes.sort(reverse=True)  # Сортируем по качеству (от большего к меньшему)
        
        # Находим первое качество, дающее подходящий размер
        for quality, size, bytes_data in quality_sizes:
            if size <= max_file_size:
                return ProcessingResult(
                    bytes=bytes_data,
                    original_size=original_size,
                    final_size=size,
                    quality=quality
                )
        
        # Если не нашли подходящее качество, возвращаем минимальное
        return ProcessingResult(
            bytes=quality_sizes[-1][2],  # bytes при минимальном качестве
            original_size=original_size,
            final_size=quality_sizes[-1][1],  # size при минимальном качестве
            quality=quality_sizes[-1][0]  # минимальное качество
        )

async def process_image_file(file: File) -> Tuple[str, ProcessingResult]:
    """Обрабатывает файл изображения из Telegram"""
    # Создаем временный файл для сохранения результата
    output_path = f"data/processed_{file.file_unique_id}.jpg"
    
    # Скачиваем файл
    await file.download_to_drive(output_path)
    
    # Читаем файл в байты
    with open(output_path, 'rb') as f:
        image_bytes = f.read()
    
    # Обрабатываем изображение
    result = await process_image_bytes(image_bytes)
    
    # Сохраняем обработанное изображение
    with open(output_path, 'wb') as f:
        f.write(result.bytes)
    
    return output_path, result

async def process_image_from_url(url: str) -> Tuple[str, ProcessingResult]:
    """Обрабатывает изображение по URL"""
    # Создаем временный файл для сохранения результата
    output_path = f"data/processed_{hash(url)}.jpg"
    
    # Скачиваем изображение
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise ValueError("Не удалось загрузить изображение")
            image_bytes = await response.read()
    
    # Обрабатываем изображение
    try:
        result = await process_image_bytes(image_bytes)
        
        # Сохраняем обработанное изображение
        with open(output_path, 'wb') as f:
            f.write(result.bytes)
        
        return output_path, result
    except Exception as e:
        raise Exception(f"Ошибка при обработке изображения: {str(e)}")