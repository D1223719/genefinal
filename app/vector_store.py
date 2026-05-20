import os
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import settings

# 初始化 Embedding 模型
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """初始化並獲取 Google Gemini Embedding 模型"""
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == "your_gemini_api_key_here":
        # 如果未設定金鑰，拋出友好提示
        raise ValueError("GEMINI_API_KEY is not configured. Please edit .env file and set your API key.")
    
    return GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL_NAME,
        google_api_key=api_key
    )

def get_vector_store() -> InMemoryVectorStore:
    """載入或初始化持久化的向量資料庫"""
    embeddings = get_embeddings()
    store_path = Path(settings.VECTOR_STORE_PATH)
    
    if store_path.exists() and store_path.stat().st_size > 0:
        try:
            # 載入現有向量庫
            store = InMemoryVectorStore.load(str(store_path), embeddings)
            print(f"Successfully loaded persistent vector store from {store_path}")
            return store
        except Exception as e:
            print(f"Error loading persistent vector store: {e}. Re-initializing...")
            
    # 如果不存在或載入失敗，建立全新向量資料庫
    store = InMemoryVectorStore(embeddings)
    return store

def persist_vector_store(store: InMemoryVectorStore):
    """將向量資料庫持久化儲存至本機檔案"""
    store_path = Path(settings.VECTOR_STORE_PATH)
    try:
        # 確保父目錄存在
        store_path.parent.mkdir(parents=True, exist_ok=True)
        store.dump(str(store_path))
        print(f"Successfully persisted vector store to {store_path}")
    except Exception as e:
        print(f"Failed to persist vector store: {e}")

def hybrid_search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    混合檢索 (Hybrid Search)：
    結合 1. 語意搜尋 (Semantic Search) 與 2. 關鍵字搜尋 (Keyword Search)。
    回傳合併去重後的結果，並包含來源標註需要的 metadata。
    """
    store = get_vector_store()
    
    # --- 1. 語意檢索 ---
    semantic_results: List[Tuple[Document, float]] = []
    try:
        # similarity_search_with_score 回傳 (Document, score) 列表，分數越小通常代表距離越近 (Cosine Similarity 則越大)
        semantic_results = store.similarity_search_with_score(query, k=limit)
    except Exception as e:
        print(f"Semantic search error: {e}")
    
    # 格式化語意結果，將評分轉換為 0~1 的相關度 (假設 cosine distance，小於 1)
    results_map: Dict[str, Dict[str, Any]] = {}
    for doc, score in semantic_results:
        content = doc.page_content
        doc_id = doc.metadata.get("document_id")
        filename = doc.metadata.get("filename", "Unknown")
        page_number = doc.metadata.get("page_number", 1)
        tags = doc.metadata.get("tags", [])
        
        # 建立唯一標示鍵值，避免重複段落
        key = f"{filename}_{page_number}_{content[:30]}"
        
        # 將距離轉為相似度得分
        similarity_score = max(0.0, 1.0 - float(score))
        
        results_map[key] = {
            "text": content,
            "filename": filename,
            "page_number": page_number,
            "document_id": doc_id,
            "tags": tags,
            "semantic_score": similarity_score,
            "keyword_score": 0.0,
            "final_score": similarity_score * 0.7  # 語意佔 70% 權重
        }
        
    # --- 2. 關鍵字檢索 ---
    # 對語句進行基本斷詞 / 小寫匹配
    query_terms = [t.lower() for t in query.split() if len(t) > 0]
    
    # 遍歷 InMemoryStore
    if hasattr(store, "store") and isinstance(store.store, dict):
        for item_id, item in store.store.items():
            text = item.get("text", "").lower()
            metadata = item.get("metadata", {})
            
            # 計算簡單的關鍵詞頻率匹配分數
            matches = 0
            if query.lower() in text:
                matches += 3  # 完全包含 query 給予高分
            for term in query_terms:
                if term in text:
                    matches += 1
            
            if matches > 0:
                content = item.get("text", "")
                filename = metadata.get("filename", "Unknown")
                page_number = metadata.get("page_number", 1)
                doc_id = metadata.get("document_id")
                tags = metadata.get("tags", [])
                
                key = f"{filename}_{page_number}_{content[:30]}"
                
                keyword_score = min(1.0, matches / 5.0)  # 正規化到 0~1
                
                if key in results_map:
                    # 如果已經在語意檢索中，合併分數
                    results_map[key]["keyword_score"] = keyword_score
                    results_map[key]["final_score"] = (results_map[key]["semantic_score"] * 0.7) + (keyword_score * 0.3)
                else:
                    # 新增關鍵字發現的項目
                    results_map[key] = {
                        "text": content,
                        "filename": filename,
                        "page_number": page_number,
                        "document_id": doc_id,
                        "tags": tags,
                        "semantic_score": 0.0,
                        "keyword_score": keyword_score,
                        "final_score": keyword_score * 0.3  # 關鍵字佔 30% 權重
                    }

    # --- 3. 排序與限額回傳 ---
    sorted_results = sorted(results_map.values(), key=lambda x: x["final_score"], reverse=True)
    return sorted_results[:limit]
