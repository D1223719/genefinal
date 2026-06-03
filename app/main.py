from app.database import engine
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, Depends, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import (
    init_db, get_db, save_chat_message, get_chat_history, 
    get_weaknesses, update_weakness, get_knowledge_graph, 
    get_chat_sessions, delete_chat_session,
    Document as DBDocument, SessionLocal, get_default_user_id
)
from app.vector_store import get_vector_store, persist_vector_store, get_embeddings
from app.tools import extractor_tool, graph_builder_tool
from app.agent import agent_app
from langchain_core.messages import HumanMessage, AIMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document as LCDocument

# 初始化資料庫表格與預設使用者
init_db()

app = FastAPI(
    title="AI 個人知識管理 Agent 系統 API",
    description="提供文件上傳解析、知識萃取、圖譜關聯、記憶對話與弱點複習的後端服務。",
    version="1.0.0"
)

# 允許跨域請求 (CORS) 供前端呼叫
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 建立上傳目錄
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# ==========================================
# Pydantic 請求資料格式定義
# ==========================================

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class QuizSubmitRequest(BaseModel):
    topic: str
    correct: bool

# ==========================================
# 背景非同步文件處理管線 (Document Processing Pipeline)
# ==========================================

def process_uploaded_file(file_path: Path, filename: str, file_type: str, doc_id: int):
    """
    背景非同步任務：
    1. 擷取文本內容。
    2. 使用 RecursiveCharacterTextSplitter 進行切塊 (Chunking)。
    3. 呼叫 ExtractorTool 獲取摘要與 Tags。
    4. 呼叫 GraphBuilderTool 分析並寫入知識關聯。
    5. 使用 Embedding 模型將 Chunks 寫入 persistent Vector DB。
    6. 更新 MySQL/SQLite 裡的 Document 記錄 (寫入摘要與 Tags)。
    """
    db = SessionLocal()
    try:
        print(f"Starting pipeline for document: {filename}...")
        
        # 1. 擷取文本與切塊
        lc_docs: List[LCDocument] = []
        full_text = ""
        
        if file_type == "pdf":
            try:
                from langchain_community.document_loaders import PyMuPDFLoader
                loader = PyMuPDFLoader(str(file_path))
            except ImportError:
                loader = PyPDFLoader(str(file_path))
                
            pages = loader.load()
            
            # 用於摘要萃取的完整文本 (限制前 6000 字避免 token 爆量)
            full_text = "\n".join([page.page_content for page in pages[:10]])
            
            # 使用 RecursiveCharacterTextSplitter 進行切塊
            splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=120)
            lc_docs = splitter.split_documents(pages)
        else:
            # Markdown 或純文字
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            full_text = content
            
            # 手動包裝為 LCDocument
            raw_doc = LCDocument(page_content=content, metadata={"source": filename, "page_number": 1})
            splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=120)
            lc_docs = splitter.split_documents([raw_doc])
            
        print(f"Document {filename} split into {len(lc_docs)} chunks.")
        
        # 檢查是否有萃取出實質文字
        if not lc_docs or not any(doc.page_content.strip() for doc in lc_docs):
            raise ValueError("此檔案內缺乏可萃取的文字內容 (可能是純圖片掃描檔)。請上傳具備文字層的 PDF 或 Markdown 檔案。")

        # 2. 結構萃取 (Extractor)
        extraction = extractor_tool(full_text)
        summary = extraction.get("summary", "無摘要")
        tags = extraction.get("tags", [])
        print(f"Extracted summary & tags: {tags}")
        
        # 3. 關係鏈結 (Graph Builder)
        graph_builder_tool(tags, summary)
        
        # 4. 寫入向量資料庫 (Vector DB)
        # 為每個 chunk 注入正確的 metadata 供 RAG 與來源追溯
        for doc in lc_docs:
            doc.metadata["document_id"] = doc_id
            doc.metadata["filename"] = filename
            doc.metadata["page_number"] = doc.metadata.get("page", 1)  # PyPDFLoader 會自動標記 "page"
            doc.metadata["tags"] = tags
            
        vector_store = get_vector_store()
        vector_store.add_documents(lc_docs)
        persist_vector_store(vector_store)
        print("Vector database persistence completed.")
        
        # 5. 更新 SQLite 資料庫的 Document 紀錄
        db_doc = db.query(DBDocument).filter(DBDocument.id == doc_id).first()
        if db_doc:
            db_doc.summary = summary
            db_doc.tags = tags
            db.commit()
            print(f"Successfully updated document record in SQL database.")
            
    except Exception as e:
        print(f"Error processing file {filename} in pipeline: {e}")
        # 錯誤時更新資料庫狀態
        db_doc = db.query(DBDocument).filter(DBDocument.id == doc_id).first()
        if db_doc:
            db_doc.summary = f"處理檔案時發生錯誤：{str(e)}"
            db.commit()
    finally:
        db.close()

# ==========================================
# Web API 路由端點實作
# ==========================================

@app.post("/api/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    上傳知識文件介面：
    接收檔案後先寫入上傳目錄，並在資料庫建立元資料條目。
    隨後發送背景非同步任務處理管線，立即回傳 HTTP 202 成功代碼給前端。
    """
    filename = file.filename
    file_ext = filename.split(".")[-1].lower()
    
    if file_ext not in ["pdf", "md", "txt"]:
        raise HTTPException(status_code=400, detail="僅支援 PDF, MD 或 TXT 格式檔案。")
        
    # 儲存實體檔案
    file_path = UPLOAD_DIR / filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 建立 SQLite Document Metadata
    user_id = get_default_user_id()
    
    # 若檔案已存在，先刪除舊紀錄避免 UNIQUE constraint 錯誤
    existing_doc = db.query(DBDocument).filter(DBDocument.filename == filename).first()
    if existing_doc:
        db.delete(existing_doc)
        db.commit()
        
    db_doc = DBDocument(
        user_id=user_id,
        filename=filename,
        file_type=file_ext,
        summary="檔案解析中，請稍候..."
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    # 啟動背景處理 pipeline
    background_tasks.add_task(
        process_uploaded_file, 
        file_path, 
        filename, 
        file_ext, 
        db_doc.id
    )
    
    return {
        "status": "success",
        "message": f"檔案 {filename} 已成功上傳，正在背景進行解析與關聯圖譜分析。",
        "document_id": db_doc.id
    }


@app.get("/api/documents")
async def list_documents(db: Session = Depends(get_db)):
    """獲取目前上傳的所有文件與摘要、標籤"""
    docs = db.query(DBDocument).order_by(DBDocument.created_at.desc()).all()
    return [{
        "id": d.id,
        "filename": d.filename,
        "file_type": d.file_type,
        "summary": d.summary,
        "tags": d.tags,
        "created_at": d.created_at.isoformat()
    } for d in docs]


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    知識問答 API：
    執行 LangGraph 智能體對話流，分析使用者意圖並輸出結果。
    同時自動將對話寫入 SQL 歷史對話資料表（短期記憶）。
    """
    user_msg = request.message
    session_id = request.session_id
    
    # 1. 儲存使用者對話紀錄
    save_chat_message("user", user_msg, session_id=session_id)
    
    # 2. 調用 LangGraph 工作流
    initial_state = {
        "messages": [HumanMessage(content=user_msg)],
        "intent": "",
        "context": "",
        "quiz_data": {}
    }
    
    try:
        final_state = agent_app.invoke(initial_state)
        ai_reply_msg = final_state["messages"][-1]
        ai_reply = ai_reply_msg.content
        
        # 確保 ai_reply 是字串 (Gemini有時會回傳包含 dict 的 list)
        if isinstance(ai_reply, list):
            ai_reply = "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in ai_reply)
        elif not isinstance(ai_reply, str):
            ai_reply = str(ai_reply)
            
        intent = final_state.get("intent", "RAG")
        quiz_data = final_state.get("quiz_data", {})
        
        # 3. 儲存 AI 回覆紀錄
        save_chat_message("assistant", ai_reply, session_id=session_id)
        
        return {
            "status": "success",
            "reply": ai_reply,
            "intent": intent,
            "quiz_data": quiz_data
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_reply = f"抱歉，在處理您的問答時發生 AI 模型調用錯誤：{str(e)}"
        try:
            save_chat_message("assistant", error_reply, session_id=session_id)
        except Exception:
            pass
        return {
            "status": "error",
            "reply": error_reply,
            "intent": "RAG",
            "quiz_data": {}
        }


@app.get("/api/history")
async def get_history(session_id: str = "default"):
    """獲取短期對話歷史紀錄"""
    history = get_chat_history(session_id=session_id, limit=30)
    return {"history": history}

@app.get("/api/chat/sessions")
async def get_sessions():
    """獲取使用者的對話紀錄清單"""
    sessions = get_chat_sessions()
    return {"sessions": sessions}

@app.delete("/api/chat/sessions/{session_id}")
async def delete_session(session_id: str):
    """刪除指定 session 的對話紀錄"""
    delete_chat_session(session_id)
    return {"status": "success", "message": "對話紀錄已刪除"}


@app.get("/api/graph")
async def get_graph():
    """獲取完整的知識圖譜（包含節點與邊），供 Streamlit 可視化渲染"""
    graph = get_knowledge_graph()
    return graph


@app.post("/api/quiz/submit")
async def submit_quiz(request: QuizSubmitRequest):
    """
    提交測驗結果 API：
    當使用者在前端回答多選題後，提交對錯。
    系統將據此更新使用者長期弱點記憶（答錯增加權重，答對降低）。
    """
    update_weakness(request.topic, request.correct)
    return {
        "status": "success",
        "message": f"已成功更新「{request.topic}」的長期弱點記憶分數。"
    }


@app.get("/api/weaknesses")
async def list_weaknesses():
    """列出目前的弱點主題與錯誤分數"""
    weaknesses = get_weaknesses()
    return {"weaknesses": weaknesses}


@app.post("/api/reset")
async def reset_system():
    """
    系統重設 API：
    清空上傳檔案、清空 SQLite 資料表、重設向量資料庫檔案。方便展示時一鍵重來。
    """
    # 1. 刪除 uploads 目錄中的檔案
    if UPLOAD_DIR.exists():
        shutil.rmtree(UPLOAD_DIR)
        UPLOAD_DIR.mkdir(exist_ok=True)
        
    # 2. 刪除 SQLite 資料庫檔案並重組
    db_file = Path("./knowledge_agent.db")
    if db_file.exists():
        try:
            # 關閉任何可能的連線，刪除檔案
            engine.dispose()
            os.remove(db_file)
            print("Successfully deleted SQLite database file.")
        except Exception as e:
            print(f"Error deleting SQLite file: {e}")
            
    init_db()  # 重建資料表與預設使用者
    
    # 3. 刪除向量 Persistent 檔案
    vector_file = Path(settings.VECTOR_STORE_PATH)
    if vector_file.exists():
        try:
            os.remove(vector_file)
            print("Successfully deleted vector store pkl file.")
        except Exception as e:
            print(f"Error deleting vector pkl file: {e}")
            
    return {"status": "success", "message": "系統已成功重置，所有上傳文件、歷史對話、弱點記憶與圖譜已清空。"}
