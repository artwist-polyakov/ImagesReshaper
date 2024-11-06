from fastapi import FastAPI, UploadFile, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
from src.utils.token_manager import TokenManager
from src.utils.image_processor import process_image_bytes, get_image_dimensions, calculate_resize_options
from src.utils.telegram_sender import send_resize_options_to_telegram
import json
from src.utils.storage import storage

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
    # Читаем HTML файл
    with open("static/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.post("/upload")
async def upload_file(
    file: UploadFile,
    token: str
):
    try:
        # Проверяем токен
        token_data = token_manager.validate_token(token)
        if not token_data:
            raise HTTPException(status_code=401, detail="Недействительный или просроченный токен")
        
        # Проверяем размер файла
        contents = await file.read()
        max_size = int(os.getenv("MAX_UPLOAD_SIZE", 52428800))  # 50MB по умолчанию
        if len(contents) > max_size:
            raise HTTPException(status_code=400, detail="Файл слишком большой")
        
        # Получаем размеры изображения и варианты изменения размера
        width, height = get_image_dimensions(contents)
        resize_options = calculate_resize_options(width, height)
        
        # Отправляем сообщение с вариантами в Telegram
        user_id = token_data["user_id"]
        
        # Сохраняем изображение в общее хранилище
        storage.save_image(user_id, {
            'bytes': contents,
            'original_size': (width, height)
        })
        
        await send_resize_options_to_telegram(user_id, contents, width, height, resize_options)
        
        return {"status": "success", "message": "Изображение получено, проверьте Telegram для выбора размера"}
        
    except Exception as e:
        print(f"Ошибка при обработке загрузки: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))