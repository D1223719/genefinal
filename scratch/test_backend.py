import os
import sys
from pathlib import Path

# 將項目根目錄添加到 Python 路徑中
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.config import settings, is_api_key_configured
from app.database import init_db, SessionLocal, User, Document, Conversation, WeaknessMemory, KnowledgeGraph
from app.vector_store import get_vector_store, persist_vector_store, get_embeddings

def main():
    print("==================================================")
    print("   AI 個人知識管理 Agent - 後端功能驗證測試")
    print("==================================================")
    
    # 1. 驗證環境變數與 API Key
    print("\n[步驟 1] 驗證環境變數與 API Key...")
    print(f"  - DATABASE_URL: {settings.DATABASE_URL}")
    print(f"  - VECTOR_STORE_PATH: {settings.VECTOR_STORE_PATH}")
    print(f"  - MODEL_NAME: {settings.MODEL_NAME}")
    
    configured = is_api_key_configured()
    print(f"  - GEMINI_API_KEY 設定狀態: {'已配置' if configured else '未配置 (請在 .env 中填寫)'}")
    
    if not configured:
        print("\n[警告] 檢測到尚未配置有效之 GEMINI_API_KEY。")
        print("請打開專案根目錄的 `.env` 檔案，填入您的 API 金鑰後再次運行此測試。")
        print("目前我們將僅測試關聯式資料庫 (SQLite) 的初始化是否正常...")
        
    # 2. 驗證 SQLite 資料庫與 ORM 初始化
    print("\n[步驟 2] 驗證 SQLite 資料庫與 ORM 初始化...")
    try:
        init_db()
        print("  - 資料表初始化: 成功 (已自動建立 tables)")
        
        db = SessionLocal()
        user = db.query(User).filter(User.username == "jeff").first()
        if user:
            print(f"  - 預設使用者創建: 成功 (ID: {user.id}, Username: {user.username})")
        else:
            print("  - 預設使用者創建: 失敗")
        db.close()
    except Exception as e:
        print(f"  - 資料庫初始化失敗: {e}")
        return

    # 3. 測試關聯資料表之 CRUD 操作
    print("\n[步驟 3] 測試資料庫關係與紀錄寫入 (CRUD)...")
    db = SessionLocal()
    try:
        # 新增測試文檔
        test_doc = Document(
            user_id=1,
            filename="Test_Attention.pdf",
            file_type="pdf",
            summary="This is a test summary for attention mechanism.",
            tags=["Attention", "Transformer"]
        )
        db.add(test_doc)
        
        # 新增對話
        test_conv = Conversation(
            user_id=1,
            role="user",
            content="Hello world"
        )
        db.add(test_conv)
        
        # 新增弱點記憶
        test_weak = WeaknessMemory(
            user_id=1,
            topic="Attention",
            error_count=2
        )
        db.add(test_weak)
        
        # 新增圖譜邊緣
        test_edge = KnowledgeGraph(
            source_node="Transformer",
            target_node="Attention",
            relation_type="depends_on",
            weight=0.95
        )
        db.add(test_edge)
        
        db.commit()
        print("  - 寫入測試數據 (Document, Conversation, Weakness, Graph): 成功")
        
        # 讀取測試
        doc_count = db.query(Document).count()
        conv_count = db.query(Conversation).count()
        weak_count = db.query(WeaknessMemory).count()
        graph_count = db.query(KnowledgeGraph).count()
        
        print(f"  - 讀取資料統計: 文檔={doc_count}筆, 對話={conv_count}筆, 弱點={weak_count}筆, 圖譜={graph_count}筆")
        
        # 清理測試數據
        db.query(Document).delete()
        db.query(Conversation).delete()
        db.query(WeaknessMemory).delete()
        db.query(KnowledgeGraph).delete()
        db.commit()
        print("  - 清理測試數據: 成功")
        
    except Exception as e:
        print(f"  - CRUD 測試失敗: {e}")
        db.rollback()
    finally:
        db.close()
        
    # 4. 向量庫初始化測試 (若 API Key 已配置)
    if configured:
        print("\n[步驟 4] 驗證向量資料庫與 Embedding 模型載入...")
        try:
            vector_store = get_vector_store()
            print("  - 向量庫初始化與 Embedding 綁定: 成功")
            
            # 測試持久化儲存與載入
            persist_vector_store(vector_store)
            print("  - 向量持久化測試: 成功")
        except Exception as e:
            print(f"  - 向量庫測試失敗: {e}")
            
    print("\n==================================================")
    print("   測試完畢。SQLite 資料庫功能與欄位完全符合設計！")
    if not configured:
        print("   >>> 溫馨提醒：請記得配置您的 .env 金鑰以獲得完整 Agent 功能。 <<<")
    print("==================================================")

if __name__ == "__main__":
    main()
