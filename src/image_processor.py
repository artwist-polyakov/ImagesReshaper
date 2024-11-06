from telegram import File
from src.utils.image_processor import process_image_file, process_image_from_url

async def process_image(file: File) -> str:
    """Обрабатывает изображение из Telegram"""
    return await process_image_file(file)

async def process_image_from_link(url: str) -> str:
    """Обрабатывает изображение по ссылке"""
    return await process_image_from_url(url)