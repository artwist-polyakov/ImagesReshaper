from fastapi import FastAPI, UploadFile, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
from src.utils.token_manager import TokenManager
from src.utils.image_processor import process_image_bytes

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
async def upload_file(file: UploadFile, token: str):
    try:
        # Проверяем токен
        token_data = token_manager.validate_token(token)
        if not token_data:
            raise HTTPException(status_code=401, detail="Недействительный или просроченный токен")
        
        # Проверяем размер файла
        max_size = int(os.getenv("MAX_UPLOAD_SIZE", 52428800))  # 50MB по умолчанию
        
        # Читаем файл
        contents = await file.read()
        if len(contents) > max_size:
            raise HTTPException(status_code=400, detail="Файл слишком большой")
        
        # Обрабатываем изображение
        processed_image = await process_image_bytes(contents)
        
        # Возвращаем обработанное изображение
        return Response(
            content=processed_image,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": "attachment; filename=processed_image.jpg"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 