from cryptography.fernet import Fernet
import json
from datetime import datetime, timedelta
from collections import deque
import os
import base64

class TokenManager:
    def __init__(self):
        # Получаем или генерируем ключ
        key = os.getenv("TOKEN_SECRET_KEY")
        if not key:
            key = Fernet.generate_key().decode()
            print(f"WARNING: TOKEN_SECRET_KEY not set. Generated new key: {key}")
            os.environ["TOKEN_SECRET_KEY"] = key
        else:
            # Проверяем, что ключ корректный
            try:
                # Пытаемся декодировать ключ
                key_bytes = base64.urlsafe_b64decode(key + '=' * (-len(key) % 4))
                # Если длина не 32 байта, генерируем новый ключ
                if len(key_bytes) != 32:
                    raise ValueError("Invalid key length")
            except:
                key = Fernet.generate_key().decode()
                print(f"WARNING: Invalid TOKEN_SECRET_KEY. Generated new key: {key}")
                os.environ["TOKEN_SECRET_KEY"] = key

        self.key = key.encode()
        self.fernet = Fernet(self.key)
        self.tokens = deque()
        
    def cleanup_tokens(self):
        """Удаляет просроченные токены"""
        now = datetime.now()
        while self.tokens and self.tokens[0]["expires_at"] < now:
            self.tokens.popleft()
    
    def create_token(self, user_id: int) -> str:
        """Создает новый токен"""
        self.cleanup_tokens()
        
        expires_at = datetime.now() + timedelta(hours=1)
        token_data = {
            "user_id": user_id,
            "expires_at": expires_at.isoformat()
        }
        
        # Шифруем данные
        token = self.fernet.encrypt(json.dumps(token_data).encode())
        
        # Сохраняем в очередь
        self.tokens.append({
            "token": token,
            "user_id": user_id,
            "expires_at": expires_at
        })
        
        return token.decode()
    
    def validate_token(self, token: str) -> dict:
        """Проверяет валидность токена"""
        self.cleanup_tokens()
        
        try:
            token_bytes = token.encode()
            decrypted_data = self.fernet.decrypt(token_bytes)
            token_data = json.loads(decrypted_data)
            
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if expires_at < datetime.now():
                return None
                
            return token_data
        except:
            return None 