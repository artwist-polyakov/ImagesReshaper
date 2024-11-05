from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
import os
from datetime import datetime
from src.utils.token_manager import TokenManager
from src.utils.image_processor import process_image_bytes

app = FastAPI()
token_manager = TokenManager()

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root(token: str):
    # Проверяем валидность токена
    token_data = token_manager.validate_token(token)
    if not token_data:
        return HTMLResponse(content="""
            <html>
                <body>
                    <div style="color: red;">Время действия ссылки истекло. Получите новую ссылку.</div>
                </body>
            </html>
        """)
    
    # Вычисляем оставшееся время
    expires_at = datetime.fromisoformat(token_data["expires_at"])
    remaining_time = expires_at - datetime.now()
    hours, remainder = divmod(remaining_time.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    return HTMLResponse(content=f"""
        <html>
            <head>
                <style>
                    .timer {{ background: gray; padding: 10px; color: white; }}
                    .drop-zone {{ 
                        border: 2px dashed #ccc; 
                        padding: 20px;
                        text-align: center;
                        margin: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="timer">Осталось {hours} часов {minutes} минут на загрузку картинки</div>
                <div class="drop-zone" id="dropZone">
                    Перетащите файл сюда или кликните для выбора
                    <input type="file" id="fileInput" style="display: none;" accept="image/*">
                </div>
                <script src="/static/js/upload.js"></script>
            </body>
        </html>
    """)

@app.post("/upload")
async def upload_file(file: UploadFile, token: str):
    # Проверяем токен
    token_data = token_manager.validate_token(token)
    if not token_data:
        raise HTTPException(status_code=400, detail="Token expired")
    
    # Проверяем размер файла
    max_size = int(os.getenv("MAX_UPLOAD_SIZE", 52428800))  # 50MB по умолчанию
    
    # Читаем файл
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(status_code=400, detail="File too large")
    
    try:
        # Обрабатываем изображение
        processed_image = await process_image_bytes(contents)
        return Response(content=processed_image, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 