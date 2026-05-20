import os
from pathlib import Path
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    # Gemini API 金鑰
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # 伺服器埠號
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # SQLite 資料庫連線字串
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./knowledge_agent.db")
    
    # 向量庫持久化路徑
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "vector_store.pkl")

    # 預設使用的 Gemini 模型
    # 對話與規劃使用 gemini-3.5-flash
    MODEL_NAME: str = "gemini-3.5-flash"
    
    # 預設 Embedding 模型
    EMBEDDING_MODEL_NAME: str = "gemini-embedding-2-preview"

settings = Settings()

# 檢查 API Key 是否有被設定（若為預設預留字串也視為未設定）
def is_api_key_configured() -> bool:
    return bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here")
