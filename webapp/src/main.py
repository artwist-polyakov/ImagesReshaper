from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from shared.utils.token_manager import TokenManager
from shared.image_processing.processor import (
    process_image_bytes,
    get_image_dimensions,
    calculate_resize_options,
)
from shared.utils.telegram_sender import send_resize_options_to_telegram
from shared.utils.storage import storage
import os

app = FastAPI()

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Создаем экземпляр TokenManager
token_manager = TokenManager()


@app.get("/")
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.post("/upload")
async def upload_file(file: UploadFile, token: str):
    try:
        # Проверяем токен
        token_data = token_manager.verify_token(token)
        user_id = token_data["user_id"]

        # Читаем файл
        contents = await file.read()

        # Получаем размеры изображения
        width, height = get_image_dimensions(contents)

        # Рассчитываем варианты изменения размера
        resize_options = calculate_resize_options(width, height)

        # Сохраняем изображение с правильной структурой
        storage.save_image(
            user_id, {"bytes": contents, "original_size": (width, height)}
        )

        # Отправляем варианты в Telegram
        await send_resize_options_to_telegram(
            user_id, contents, width, height, resize_options
        )

        return {"message": "Изображение успешно загружено"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
