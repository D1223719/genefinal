import streamlit as st
import requests
import os
import json
import time
import uuid
import markdown
from typing import Dict, Any, List

# 設定網頁標題與外觀
st.set_page_config(
    page_title="AI 個人知識管理 Agent 系統",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 後端 API 基礎路徑
API_URL = "http://localhost:8000/api"

# ==========================================
# 1. 極致美化：CSS 深色 Premium 質感樣式注入
# ==========================================
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">

<style>
    /* 隱藏右上角 Streamlit 預設選單與 Deploy 按鈕，保持畫面整潔專業 */
    #MainMenu {visibility: hidden;}
    header {background-color: transparent !important;}
    .stDeployButton {display: none;}
    
    /* 全域字體與背景 */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background-color: #0d0d12 !important;
        color: #e2e2e9 !important;
    }
    
    /* 標題 Outfit 字體 */
    h1, h2, h3, .main-title {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    
    /* Sidebar 美化 */
    [data-testid="stSidebar"] {
        background-color: #14141d !important;
        border-right: 1px solid #232333;
    }
    
    /* 漸層標題與裝飾 */
    .gradient-text {
        background: linear-gradient(135deg, #7F00FF 0%, #FF007F 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
    }
    
    .cyan-gradient-text {
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
    }
    
    /* Premium Glassmorphism 卡片 */
    .glass-card {
        background: rgba(22, 22, 33, 0.7);
        border: 1px solid rgba(48, 48, 68, 0.5);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        margin-bottom: 20px;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    }
    .glass-card:hover {
        border-color: rgba(127, 0, 255, 0.5);
        transform: translateY(-2px);
        box-shadow: 0 12px 40px 0 rgba(127, 0, 255, 0.15);
    }
    
    /* 精緻對話泡泡樣式 */
    .chat-bubble-user {
        background: linear-gradient(135deg, #6c00d4 0%, #b8006c 100%);
        color: white;
        padding: 14px 18px;
        border-radius: 18px 18px 0px 18px;
        margin-bottom: 15px;
        max-width: 80%;
        margin-left: auto;
        box-shadow: 0 4px 15px rgba(108, 0, 212, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: left;
    }
    
    .chat-bubble-assistant {
        background: rgba(30, 30, 45, 0.8);
        color: #e2e2e9;
        padding: 14px 18px;
        border-radius: 18px 18px 18px 0px;
        margin-bottom: 15px;
        max-width: 80%;
        margin-right: auto;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(48, 48, 68, 0.6);
        text-align: left;
    }
    
    /* 來源引用卡片 Chip */
    .source-chip {
        display: inline-flex;
        align-items: center;
        background: rgba(0, 242, 254, 0.1);
        border: 1px solid rgba(0, 242, 254, 0.3);
        color: #00f2fe;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 8px;
        margin-top: 6px;
        transition: all 0.2s ease;
    }
    .source-chip:hover {
        background: rgba(0, 242, 254, 0.2);
        transform: scale(1.03);
    }
    
    /* 複習測驗玻璃按鈕 */
    .quiz-option-btn {
        background: rgba(26, 26, 38, 0.8) !important;
        border: 1px solid rgba(48, 48, 68, 0.8) !important;
        color: #e2e2e9 !important;
        padding: 12px 20px !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        display: block !important;
        width: 100% !important;
        text-align: left !important;
        margin-bottom: 10px !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1) !important;
    }
    .quiz-option-btn:hover {
        background: rgba(127, 0, 255, 0.1) !important;
        border-color: #7F00FF !important;
        color: #ffffff !important;
        transform: translateX(4px) !important;
        box-shadow: 0 4px 15px rgba(127, 0, 255, 0.2) !important;
    }
    
    /* 弱點分析儀表板進度條 */
    .weakness-bar-bg {
        background: rgba(30, 30, 45, 0.6);
        border-radius: 8px;
        width: 100%;
        height: 12px;
        overflow: hidden;
        border: 1px solid rgba(48, 48, 68, 0.5);
    }
    .weakness-bar-fill {
        background: linear-gradient(90deg, #ff007f 0%, #ff4b2b 100%);
        height: 100%;
        border-radius: 8px;
        box-shadow: 0 0 10px rgba(255, 0, 127, 0.5);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 輔助 API 呼叫函式
# ==========================================

def get_backend_status() -> bool:
    """檢查後端服務是否已啟動"""
    try:
        res = requests.get(f"{API_URL}/documents", timeout=2)
        return res.status_code == 200
    except Exception:
        return False

def upload_file_to_api(uploaded_file) -> Dict[str, Any]:
    """呼叫後端 API 上傳檔案"""
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
    try:
        res = requests.post(f"{API_URL}/upload", files=files)
        return res.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def send_chat_message(message: str, session_id: str = "default", force_intent: str = None) -> Dict[str, Any]:
    """發送聊天訊息"""
    try:
        res = requests.post(f"{API_URL}/chat", json={"message": message, "session_id": session_id, "force_intent": force_intent})
        return res.json()
    except Exception as e:
        return {"status": "error", "reply": f"連線至後端失敗：{str(e)}", "intent": "RAG"}

def get_chat_sessions_api() -> List[Dict[str, Any]]:
    """獲取歷史對話清單"""
    try:
        res = requests.get(f"{API_URL}/chat/sessions")
        return res.json().get("sessions", [])
    except Exception:
        return []

def delete_session_api(session_id: str) -> bool:
    """刪除指定對話紀錄"""
    try:
        res = requests.delete(f"{API_URL}/chat/sessions/{session_id}")
        return res.status_code == 200
    except Exception:
        return False

def submit_quiz_result(topic: str, correct: bool) -> Dict[str, Any]:
    """提交測驗答題狀態"""
    try:
        res = requests.post(f"{API_URL}/quiz/submit", json={"topic": topic, "correct": correct})
        return res.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_documents_list() -> List[Dict[str, Any]]:
    """獲取已上傳文件清單"""
    try:
        res = requests.get(f"{API_URL}/documents")
        return res.json()
    except Exception:
        return []


def delete_document_api(document_id: int) -> bool:
    try:
        res = requests.delete(f"{API_URL}/documents/{document_id}")
        return res.status_code == 200
    except Exception:
        return False

def get_quiz_history_api() -> List[Dict[str, Any]]:
    try:
        res = requests.get(f"{API_URL}/quiz/history")
        return res.json().get("quiz_history", [])
    except Exception:
        return []

def delete_quiz_history_api(quiz_id: int) -> bool:
    try:
        res = requests.delete(f"{API_URL}/quiz/history/{quiz_id}")
        return res.status_code == 200
    except Exception:
        return False

def get_weaknesses_list() -> List[Dict[str, Any]]:
    """獲取弱點清單"""
    try:
        res = requests.get(f"{API_URL}/weaknesses")
        return res.json().get("weaknesses", [])
    except Exception:
        return []

def get_knowledge_graph_data() -> Dict[str, Any]:
    """獲取知識圖譜 Nodes 與 Edges"""
    try:
        res = requests.get(f"{API_URL}/graph")
        return res.json()
    except Exception:
        return {"nodes": [], "edges": []}

def reset_entire_system() -> Dict[str, Any]:
    """重設全系統"""
    try:
        res = requests.post(f"{API_URL}/reset")
        return res.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==========================================
# 3. 前端會話狀態 (Session State) 初始化
# ==========================================
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "current_quiz" not in st.session_state:
    st.session_state.current_quiz = None
if "quiz_answered" not in st.session_state:
    st.session_state.quiz_answered = False
if "quiz_selected_option" not in st.session_state:
    st.session_state.quiz_selected_option = None
if "quiz_result_correct" not in st.session_state:
    st.session_state.quiz_result_correct = None
if "trigger_api_key_warn" not in st.session_state:
    st.session_state.trigger_api_key_warn = False
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = str(uuid.uuid4())

# ==========================================
# 4. 主頁面 (Main Page) 設計與導航
# ==========================================
st.markdown('<h1 class="gradient-text" style="font-size: 2.8rem; margin-bottom: 10px;">AI 個人知識管理 Agent 系統</h1>', unsafe_allow_html=True)
st.markdown('<p style="color: #a2a2b5; font-size: 1.1rem; margin-top: 0px; margin-bottom: 25px;">將零散文檔自動化生成結構化知識圖譜，並結合長期記憶弱點，提供個人客製化的 AI 觀念複習機制。</p>', unsafe_allow_html=True)

# 後端未啟動時的防呆遮罩
backend_ok = get_backend_status()
if not backend_ok:
    st.markdown("""
    <div class="glass-card" style="border-color: #ff007f; background: rgba(30, 10, 20, 0.4);">
        <h3 style="color: #ff007f; margin-top:0px;">🚨 找不到後端伺服器 (FastAPI)</h3>
        <p>請確認以下步驟以啟動完整的系統服務：</p>
        <ol>
            <li>確保您已在根目錄建立 <code>.env</code> 檔案，並填入有效的 <code>GEMINI_API_KEY</code>。</li>
            <li>開啟一個新的終端機，執行以下指令啟動 FastAPI 服務：<br>
                <code style="background: #1e1e2d; padding: 4px 8px; border-radius: 4px; display: block; margin-top: 5px;">uvicorn app.main:app --port 8000 --reload</code>
            </li>
            <li>啟動後，重新整理本 Streamlit 網頁。</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

tab_options = ["💬 智能對話助教 (RAG Chat)", "📚 知識庫與圖譜 (Knowledge Graph)", "🎯 觀念測驗與複習 (Quiz Master)"]
selected_tab = st.segmented_control("導航", tab_options, default=tab_options[0], label_visibility="collapsed")

# ==========================================
# 5. 側邊欄 (Sidebar) 設計
# ==========================================
with st.sidebar:

    st.markdown("---")
    
    if not selected_tab or selected_tab == "💬 智能對話助教 (RAG Chat)":
        st.markdown("### 💬 對話歷史紀錄")
        
        if st.button("📝 新增對話", type="primary", use_container_width=True):
            st.session_state.current_session_id = str(import_uuid.uuid4()) if "import_uuid" in globals() else str(__import__('uuid').uuid4())
            st.session_state.chat_messages = []
            st.rerun()

        sessions = get_chat_sessions_api()
        if not sessions:
            st.info("尚無歷史紀錄")
        else:
            st.markdown("<div style='max-height: 300px; overflow-y: auto;'>", unsafe_allow_html=True)
            for s in sessions:
                col1, col2 = st.columns([4, 1], gap="small")
                with col1:
                    btn_style = "secondary" if s["session_id"] != st.session_state.current_session_id else "primary"
                    if st.button(f"{s['preview']}", key=f"sel_{s['session_id']}", type=btn_style, use_container_width=True):
                        st.session_state.current_session_id = s["session_id"]
                        st.session_state.chat_messages = []
                        st.rerun()
                with col2:
                    if st.button("🗑️", key=f"del_{s['session_id']}", use_container_width=True):
                        delete_session_api(s["session_id"])
                        if st.session_state.current_session_id == s["session_id"]:
                            st.session_state.current_session_id = str(__import__('uuid').uuid4())
                            st.session_state.chat_messages = []
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
    elif selected_tab == "📚 知識庫與圖譜 (Knowledge Graph)":
        st.markdown("### 📚 知識庫操作")
        if st.button("➕ 新增知識庫", type="primary", use_container_width=True):
            st.toast("請在右側主畫面拖曳檔案來新增知識庫！", icon="📤")
            
        st.markdown("### 📄 歷史文件清單")
        
        docs = get_documents_list()
        if not docs:
            st.info("尚無上傳的知識庫文件")
        else:
            batch_mode = st.toggle("✅ 批次選取刪除")
            st.markdown("<div style='max-height: 300px; overflow-y: auto;'>", unsafe_allow_html=True)
            
            selected_docs = []
            for d in docs:
                preview = d["filename"][:15] + "..." if len(d["filename"]) > 15 else d["filename"]
                
                if batch_mode:
                    col_chk, col_doc = st.columns([1, 4])
                    with col_chk:
                        is_selected = st.checkbox(" ", key=f"chk_doc_{d['id']}")
                        if is_selected:
                            selected_docs.append(d['id'])
                    with col_doc:
                        st.button(f"📄 {preview}", key=f"doc_{d['id']}", disabled=True, use_container_width=True)
                else:
                    col1, col2 = st.columns([4, 1], gap="small")
                    with col1:
                        st.button(f"📄 {preview}", key=f"doc_{d['id']}", disabled=True, use_container_width=True)
                    with col2:
                        if st.button("🗑️", key=f"del_doc_{d['id']}", use_container_width=True):
                            delete_document_api(d['id'])
                            st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
            if batch_mode and selected_docs:
                if st.button(f"🗑️ 刪除已選取的 {len(selected_docs)} 份文件", type="primary", use_container_width=True):
                    with st.spinner("正在批次刪除中..."):
                        import time
                        for doc_id in selected_docs:
                            delete_document_api(doc_id)
                    st.success("批次刪除成功！")
                    time.sleep(1)
                    st.rerun()
            
    elif selected_tab == "🎯 觀念測驗與複習 (Quiz Master)":
        st.markdown("### 🎯 測驗與複習")
        if st.button("🎲 新增觀念測驗和複習", type="primary", use_container_width=True):
            st.toast("請點擊右側「呼叫 Quiz Master」來生成新測驗！", icon="🎲")
            
        st.markdown("### 📜 歷史測驗紀錄")
        
        quizzes = get_quiz_history_api()
        if not quizzes:
            st.info("尚無歷史測驗紀錄")
        else:
            st.markdown("<div style='max-height: 300px; overflow-y: auto;'>", unsafe_allow_html=True)
            for q in quizzes:
                col1, col2 = st.columns([4, 1], gap="small")
                with col1:
                    preview = f"[{q['topic']}] {q['question'][:10]}..."
                    is_active = (st.session_state.current_quiz and st.session_state.current_quiz.get("question") == q["question"])
                    btn_style = "primary" if is_active else "secondary"
                    if st.button(preview, key=f"quiz_{q['id']}", type=btn_style, use_container_width=True):
                        st.session_state.current_quiz = {
                            "topic": q["topic"],
                            "question": q["question"],
                            "options": q["options"],
                            "answer": q["answer"],
                            "explanation": q["explanation"]
                        }
                        st.session_state.quiz_answered = False
                        st.session_state.quiz_selected_option = None
                        st.session_state.quiz_result_correct = None
                        st.rerun()
                with col2:
                    if st.button("🗑️", key=f"del_quiz_{q['id']}", use_container_width=True):
                        delete_quiz_history_api(q['id'])
                        if st.session_state.current_quiz and st.session_state.current_quiz.get("question") == q["question"]:
                            st.session_state.current_quiz = None
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<p style="color: #555566; font-size: 0.8rem; text-align: center;">2026 AI 個人知識管理 Agent 期末專題 © Jeff</p>', unsafe_allow_html=True)
# ==========================================
# Tab 1: 智能對話助教 (RAG Chat)
# ==========================================
if not selected_tab or selected_tab == "💬 智能對話助教 (RAG Chat)":
    st.markdown('<h3 style="margin-top: 10px; margin-bottom: 20px;">💬 AI 課業問答助教</h3>', unsafe_allow_html=True)
    
    # 點點對話提示卡片
    st.markdown("""
    <div class="glass-card" style="padding: 16px; margin-bottom: 20px; font-size: 0.95rem;">
        💡 <b>小提示</b>：您可以點擊 <b style="color:#00f2fe;">「知識庫與圖譜」</b> 頁籤上傳 PDF 檔或 Markdown 文件。上傳後，在這裡詢問與該文件相關的問題，AI 助教會調用向量庫進行混合檢索，並<b>精確標註資訊來源的檔案與頁碼</b>！
    </div>
    """, unsafe_allow_html=True)

    # 顯示對話歷史
    chat_container = st.container(height=480)
    with chat_container:
        # 如果 state 空白，先去撈後端 API 取得現有歷史
        if not st.session_state.chat_messages:
            try:
                hist_res = requests.get(f"{API_URL}/history?session_id={st.session_state.current_session_id}").json()
                for h in hist_res.get("history", []):
                    st.session_state.chat_messages.append({"role": h["role"], "content": h["content"]})
            except Exception:
                pass
                
        # 顯示歷史訊息
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                user_content = msg["content"].replace("\n", "<br>")
                st.markdown(f'<div class="chat-bubble-user">{user_content}</div>', unsafe_allow_html=True)
            else:
                # 處理來源標註並在 Streamlit 中更精美地呈現
                content = msg["content"]
                
                # 尋找 [來源: xxx.pdf, 頁碼: X] 的正則
                import re
                source_patterns = re.findall(r'\[來源:\s*([^,\]]+),\s*頁碼:\s*([^\]]+)\]', content)
                
                # 將回答中的 [來源: ...] 清除或做標籤處理
                cleaned_content = re.sub(r'\[來源:\s*[^\]]+\]', '', content)
                
                # 為了避免 markdown parser 在 div 內遇到空行提早結束導致 </div> 外漏
                # 這裡強制先轉為 HTML 再放入 div 中
                html_content = markdown.markdown(cleaned_content, extensions=['fenced_code', 'tables'])
                
                chips_html = ""
                if source_patterns:
                    chips_html = "<div style='margin-top: 10px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px;'>"
                    for filename, page in source_patterns:
                        chips_html += f'<span class="source-chip">📄 {filename} (第 {page} 頁)</span>'
                    chips_html += "</div>"
                
                st.markdown(f"""
                <div class="chat-bubble-assistant">
                    <div>{html_content}</div>
                    {chips_html}
                </div>
                """, unsafe_allow_html=True)

    # 自然語言輸入框
    if prompt := st.chat_input("詢問助教：例如「請解釋 Transformer 的 Self-Attention 機制」"):
        # 顯示使用者輸入
        with chat_container:
            user_content = prompt.replace("\n", "<br>")
            st.markdown(f'<div class="chat-bubble-user">{user_content}</div>', unsafe_allow_html=True)
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        # 呼叫 API 取得 AI 回覆
        with st.spinner("AI 助教思考中..."):
            reply_data = send_chat_message(prompt, session_id=st.session_state.current_session_id)
            
        reply = reply_data.get("reply", "連線失敗。")
        intent = reply_data.get("intent", "RAG")
        
        # 顯示 AI 回覆
        with chat_container:
            import re
            source_patterns = re.findall(r'\[來源:\s*([^,\]]+),\s*頁碼:\s*([^\]]+)\]', reply)
            cleaned_reply = re.sub(r'\[來源:\s*[^\]]+\]', '', reply)
            
            # 使用 markdown 套件先轉為 HTML，避免 </div> 結尾外漏
            html_reply = markdown.markdown(cleaned_reply, extensions=['fenced_code', 'tables'])
            
            chips_html = ""
            if source_patterns:
                chips_html = "<div style='margin-top: 10px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px;'>"
                for filename, page in source_patterns:
                    chips_html += f'<span class="source-chip">📄 {filename} (第 {page} 頁)</span>'
                chips_html += "</div>"
                
            st.markdown(f"""
            <div class="chat-bubble-assistant">
                <div>{html_reply}</div>
                {chips_html}
            </div>
            """, unsafe_allow_html=True)
            
        st.session_state.chat_messages.append({"role": "assistant", "content": reply})
        
        # 如果判定意圖是 QUIZ，自動觸發重新載入以至測驗 Tab 刷出題目
        if intent == "QUIZ" and reply_data.get("quiz_data"):
            st.session_state.current_quiz = reply_data["quiz_data"]
            st.session_state.quiz_answered = False
            st.session_state.quiz_selected_option = None
            st.session_state.quiz_result_correct = None
            st.toast("🎯 助教已為您準備了專屬複習測驗！請切換至「觀念測驗與複習」頁籤作答。", icon="🎯")
            time.sleep(1)
            st.rerun()

# ==========================================
# Tab 2: 知識庫與圖譜 (Knowledge Graph)
# ==========================================
elif selected_tab == "📚 知識庫與圖譜 (Knowledge Graph)":
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<h3 style="margin-top: 10px;">📤 上傳與管理知識文件</h3>', unsafe_allow_html=True)
        
        # 拖拉上傳 (支援多檔與資料夾拖曳)
        uploaded_files = st.file_uploader(
            "選擇或拖曳 PDF/MD/TXT 檔案匯入 (支援選取多檔或直接拖曳資料夾)", 
            type=["pdf", "md", "txt"], 
            accept_multiple_files=True
        )
        
        if uploaded_files:
            if st.button("🚀 開始匯入知識管道", type="primary", use_container_width=True):
                with st.spinner(f"正在平行上傳 {len(uploaded_files)} 個檔案..."):
                    import concurrent.futures
                    success_count = 0
                    err_msgs = []
                    
                    def process_uf(uf):
                        return uf, upload_file_to_api(uf)
                        
                    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                        futures = [executor.submit(process_uf, uf) for uf in uploaded_files]
                        for future in concurrent.futures.as_completed(futures):
                            uf, res = future.result()
                            if res.get("status") == "success":
                                success_count += 1
                            else:
                                err_msgs.append(f"{uf.name}: {res.get('message')}")
                    
                if success_count > 0:
                    st.success(f"成功將 {success_count} 份檔案送入背景加速處理！")
                    if err_msgs:
                        with st.expander("部分檔案上傳失敗 / 略過"):
                            for err in err_msgs:
                                st.warning(err)
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("全部檔案上傳失敗！")
                    for err in err_msgs:
                        st.error(err)
                    
        st.markdown("---")
        st.markdown("#### 📂 知識庫已匯入文檔清單")
        
        docs_list = get_documents_list()
        if not docs_list:
            st.info("目前知識庫為空，請於上方上傳您的第一份文件！")
        else:
            for doc in docs_list:
                tags_badge = "".join([f'<span style="background: rgba(127,0,255,0.15); border: 1px solid rgba(127,0,255,0.3); color: #c8a2ff; font-size: 0.75rem; padding: 2px 8px; border-radius: 10px; margin-right: 5px; font-weight:600;">#{tag}</span>' for tag in doc["tags"]])
                tags_html = f'<div style="margin-top: 5px;">{tags_badge}</div>' if tags_badge else ""
                
                # 將 summary 內的換行替換為 <br> 以免被 Markdown 解析器錯誤分段
                safe_summary = doc["summary"].replace("\\n", "<br>")
                
                st.markdown(f"""
                <div class="glass-card" style="padding: 16px; margin-bottom: 12px; border-radius: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color: #00f2fe; font-size: 1.05rem;">📄 {doc["filename"]}</span>
                        <span style="background: rgba(255,255,255,0.05); color: #a2a2b5; font-size: 0.75rem; padding: 2px 6px; border-radius: 4px;">{doc["file_type"].upper()}</span>
                    </div>
                    <p style="font-size: 0.85rem; color: #a2a2b5; margin-top: 8px; margin-bottom: 10px;">{safe_summary}</p>
                    {tags_html}
                </div>
                """, unsafe_allow_html=True)
                
    with col2:
        st.markdown('<h3 style="margin-top: 10px;">🕸️ 互動式語意知識圖譜 (Knowledge Graph)</h3>', unsafe_allow_html=True)
        st.markdown('<p style="color: #8c8c9e; font-size: 0.85rem; margin-top: 0px;">節點大小代表概念出現在不同文件的頻率，連線代表 LLM 自動計算推論出的語意關聯邊。</p>', unsafe_allow_html=True)
        
        graph_data = get_knowledge_graph_data()
        
        if not graph_data.get("nodes"):
            st.info("暫無圖譜數據。當您上傳文件後，系統將自動比對關鍵概念並建構關聯圖譜！")
        else:
            # 使用 D3.js 渲染完美的 force-directed 互動關係圖
            nodes_json = json.dumps(graph_data["nodes"])
            edges_json = json.dumps(graph_data["edges"])
            
            d3_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://d3js.org/d3.v6.min.js"></script>
                <style>
                    body {{
                        margin: 0;
                        padding: 0;
                        background-color: #11111a;
                        overflow: hidden;
                        font-family: 'Inter', sans-serif;
                    }}
                    svg {{
                        width: 100vw;
                        height: 100vh;
                    }}
                    .link {{
                        stroke: rgba(127, 0, 255, 0.4);
                        stroke-opacity: 0.6;
                        stroke-width: 2px;
                        transition: stroke 0.3s, stroke-opacity 0.3s;
                    }}
                    .node {{
                        stroke: #0d0d12;
                        stroke-width: 2.5px;
                        cursor: pointer;
                        transition: filter 0.3s, stroke-width 0.3s;
                    }}
                    .node-label {{
                        fill: #e2e2e9;
                        font-size: 13px;
                        font-weight: 600;
                        pointer-events: none;
                        text-shadow: 0 2px 4px rgba(0,0,0,0.8);
                    }}
                    /* Glow effect */
                    .glow {{
                        filter: drop-shadow(0px 0px 8px rgba(0, 242, 254, 0.8));
                    }}
                    .glow-purple {{
                        filter: drop-shadow(0px 0px 8px rgba(127, 0, 255, 0.8));
                    }}
                </style>
            </head>
            <body>
                <svg id="canvas"></svg>
                <script>
                    const nodes = {nodes_json};
                    const links = {edges_json};
                    
                    const svg = d3.select("#canvas");
                    const width = window.innerWidth;
                    const height = window.innerHeight;
                    
                    // Zoom behavior
                    const g = svg.append("g");
                    svg.call(d3.zoom().on("zoom", (event) => {{
                        g.attr("transform", event.transform);
                    }}));
                    
                    // Force simulation
                    const simulation = d3.forceSimulation(nodes)
                        .force("link", d3.forceLink(links).id(d => d.id).distance(130))
                        .force("charge", d3.forceManyBody().strength(-200))
                        .force("center", d3.forceCenter(width / 2, height / 2))
                        .force("collision", d3.forceCollide().radius(35));
                        
                    // Draw links
                    const link = g.append("g")
                        .selectAll("line")
                        .data(links)
                        .enter().append("line")
                        .attr("class", "link");
                        
                    // Draw nodes
                    const node = g.append("g")
                        .selectAll("circle")
                        .data(nodes)
                        .enter().append("circle")
                        .attr("r", d => d.size || 15)
                        .attr("fill", (d, i) => {{
                            return i % 2 === 0 ? "#00f2fe" : "#7F00FF";
                        }})
                        .attr("class", (d, i) => i % 2 === 0 ? "node glow" : "node glow-purple")
                        .call(d3.drag()
                            .on("start", dragstarted)
                            .on("drag", dragged)
                            .on("end", dragended));
                            
                    // Labels
                    const label = g.append("g")
                        .selectAll("text")
                        .data(nodes)
                        .enter().append("text")
                        .attr("class", "node-label")
                        .attr("dy", d => (d.size || 15) + 16)
                        .attr("text-anchor", "middle")
                        .text(d => d.label);
                        
                    simulation.on("tick", () => {{
                        link
                            .attr("x1", d => d.source.x)
                            .attr("y1", d => d.source.y)
                            .attr("x2", d => d.target.x)
                            .attr("y2", d => d.target.y);

                        node
                            .attr("cx", d => d.x)
                            .attr("cy", d => d.y);

                        label
                            .attr("x", d => d.x)
                            .attr("y", d => d.y);
                    }});
                    
                    function dragstarted(event, d) {{
                        if (!event.active) simulation.alphaTarget(0.3).restart();
                        d.fx = d.x;
                        d.fy = d.y;
                    }}
                    
                    function dragged(event, d) {{
                        d.fx = event.x;
                        d.fy = event.y;
                    }}
                    
                    function dragended(event, d) {{
                        if (!event.active) simulation.alphaTarget(0);
                        d.fx = null;
                        d.fy = null;
                    }}
                </script>
            </body>
            </html>
            """
            
            st.components.v1.html(d3_html, height=520, scrolling=False)
            
            # 輔助關係說明表格
            with st.expander("🔍 檢視知識關聯明細數據表"):
                import pandas as pd
                df = pd.DataFrame(graph_data["edges"])
                if not df.empty:
                    df.columns = ["來源節點 (Source)", "目標節點 (Target)", "關係類型 (Relation)", "相關強度權重 (Weight)"]
                    st.dataframe(df.style.background_gradient(cmap="Purples", subset=["相關強度權重 (Weight)"]), use_container_width=True)

        # 檢查是否有文件正在處理中，如果是，2秒後自動重新整理
        if any("解析中" in d.get("summary", "") for d in docs_list):
            st.info("🔄 系統正在背景加速處理您的文件與建構圖譜，網頁將自動更新以顯示最新進度...")
            time.sleep(2)
            st.rerun()

# ==========================================
# Tab 3: 觀念測驗與複習 (Quiz Master)
# ==========================================
elif selected_tab == "🎯 觀念測驗與複習 (Quiz Master)":
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.markdown('<h3 style="margin-top: 10px;">📊 長期記憶弱點儀表板</h3>', unsafe_allow_html=True)
        st.markdown('<p style="color: #8c8c9e; font-size: 0.85rem; margin-top: 0px;">基於測驗錯誤歷史，追蹤需要加強的概念。測驗答錯，主題分數上升；答對，主題分數降低。</p>', unsafe_allow_html=True)
        
        weaknesses = get_weaknesses_list()
        all_quizzes = get_quiz_history_api()
        
        if not weaknesses:
            st.info("🌱 您的弱點記憶庫目前乾淨無比！請開始問答或上傳檔案，系統將在此分析您的知識弱點。")
        else:
            max_err = max([w["error_count"] for w in weaknesses]) if weaknesses else 1
            for w in weaknesses:
                # 換算百分比
                percent = int((w["error_count"] / max(1, max_err)) * 100)
                
                st.markdown(f"""
                <div style="margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.95rem; margin-bottom: 5px;">
                        <span style="font-weight: 700; color: #ff007f;">🔥 {w["topic"]}</span>
                        <span style="color: #ff007f; font-weight: 600;">錯誤指數: {w["error_count"]} 次</span>
                    </div>
                    <div class="weakness-bar-bg">
                        <div class="weakness-bar-fill" style="width: {max(5, percent)}%;"></div>
                    </div>
                    <div style="color: #666677; font-size: 0.75rem; text-align: right; margin-top: 4px;">上次測驗: {w["last_tested_at"][:16].replace("T", " ")}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 新增 查看歷史錯題
                with st.expander(f"🔍 查看「{w['topic']}」歷史錯題"):
                    topic_quizzes = [q for q in all_quizzes if q["topic"] == w["topic"]]
                    if not topic_quizzes:
                        st.info("尚無此主題的詳細考題紀錄。")
                    else:
                        for idx, q in enumerate(topic_quizzes):
                            st.markdown(f"**Q{idx+1}:** {q['question']}")
                            st.markdown(f"*正確解答:* `{q['answer']}`")
                            st.caption(f"{q['explanation']}")
                            st.divider()
                
    with col2:
        st.markdown('<h3 style="margin-top: 10px;">🎯 弱點觀念複習測驗</h3>', unsafe_allow_html=True)
        
        # 出題按鈕
        if st.button("🎲 呼叫 Quiz Master 生成專屬複習題", type="primary", use_container_width=True):
            with st.spinner("AI 導師正在調閱您的弱點記憶出題中..."):
                try:
                    # 我們直接發送一個隱藏對話意圖，讓 Agent 分流出題
                    # 或是直接發送 chat 意圖「幫我出幾題測驗來複習」
                    res = send_chat_message("幫我出幾題測驗來複習", force_intent="QUIZ")
                    if res.get("status") == "error":
                        st.error(res.get("reply", "未知錯誤"))
                    elif res.get("quiz_data"):
                        st.session_state.current_quiz = res["quiz_data"]
                        st.session_state.quiz_answered = False
                        st.session_state.quiz_selected_option = None
                        st.session_state.quiz_result_correct = None
                    else:
                        st.error("出題失敗，後端未傳回有效題目！")
                except Exception as e:
                    st.error(f"連線失敗：{e}")
                    
        custom_topic = st.chat_input("或在此指定範圍出題 (例如: 針對機器學習出題)", key="quiz_input")
        if custom_topic:
            with st.spinner(f"AI 導師正在針對「{custom_topic}」出題中..."):
                try:
                    res = send_chat_message(custom_topic, force_intent="QUIZ")
                    if res.get("status") == "error":
                        st.error(res.get("reply", "未知錯誤"))
                    elif res.get("quiz_data"):
                        st.session_state.current_quiz = res["quiz_data"]
                        st.session_state.quiz_answered = False
                        st.session_state.quiz_selected_option = None
                        st.session_state.quiz_result_correct = None
                    else:
                        st.error("出題失敗，後端未傳回有效題目！")
                except Exception as e:
                    st.error(f"連線失敗：{e}")
                    
        st.markdown("---")
        
        quiz = st.session_state.current_quiz
        
        if not quiz:
            st.info("請點擊上方按鈕，或在聊天室輸入「幫我出題」，AI 導師將為您生成複習測驗。")
        else:
            # 顯示題目
            st.markdown(f"""
            <div class="glass-card" style="border-left: 5px solid #7F00FF;">
                <span style="background: rgba(127, 0, 255, 0.2); color: #c8a2ff; font-size: 0.8rem; padding: 4px 10px; border-radius: 4px; font-weight:600; text-transform: uppercase;">
                    複習主題：{quiz["topic"]}
                </span>
                <h4 style="margin-top: 15px; font-size: 1.15rem; line-height: 1.5; color: #ffffff;">❓ {quiz["question"]}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # 使用 Streamlit columns 或 radio 做互動選擇
            options = quiz["options"]
            option_list = ["A", "B", "C", "D"]
            
            st.markdown("##### 選擇您的答案：")
            
            if not st.session_state.quiz_answered:
                # 渲染選項按鈕
                for opt in option_list:
                    if st.button(f"Option {opt}： {options[opt]}", key=f"opt_btn_{opt}", use_container_width=True, type="secondary"):
                        # 使用者點擊作答
                        st.session_state.quiz_selected_option = opt
                        st.session_state.quiz_answered = True
                        st.session_state.quiz_result_correct = (opt == quiz["answer"])
                        
                        # 呼叫 API 更新後端弱點分數
                        submit_quiz_result(quiz["topic"], st.session_state.quiz_result_correct)
                        st.rerun()
            else:
                # 答題後的精美結果呈現
                user_ans = st.session_state.quiz_selected_option
                correct_ans = quiz["answer"]
                is_correct = st.session_state.quiz_result_correct
                
                if is_correct:
                    st.markdown(f"""
                    <div style="background: rgba(0, 242, 254, 0.1); border: 2px solid #00f2fe; padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: center;">
                        <h2 style="color: #00f2fe; margin-top: 0px;">🎉 回答正確！</h2>
                        <p>您的選擇為 <b>{user_ans}</b>，此主題的弱點指數已自動調降！</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.balloons()
                else:
                    st.markdown(f"""
                    <div style="background: rgba(255, 0, 127, 0.1); border: 2px solid #ff007f; padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: center;">
                        <h2 style="color: #ff007f; margin-top: 0px;">❌ 回答錯誤！</h2>
                        <p>您的選擇為 <b>{user_ans}</b>，正確答案應為 <b style="color: #00f2fe; font-size:1.3rem;">{correct_ans}</b>。</p>
                        <p style="color: #ff007f; font-size: 0.9rem;">此主題的錯誤次數已記錄，未來將優先為您複習！</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # 顯示 AI 解析說明
                st.markdown(f"""
                <div class="glass-card" style="border-top: 4px solid #00f2fe; background: rgba(30,30,45,0.4);">
                    <h5 style="color: #00f2fe; margin-top:0px;">💡 AI 老師的深入解析說明：</h5>
                    <p style="line-height: 1.6; font-size: 0.95rem;">{quiz["explanation"]}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 下一題
                if st.button("🔄 繼續下一題測驗", type="primary", use_container_width=True):
                    st.session_state.current_quiz = None
                    st.session_state.quiz_answered = False
                    st.session_state.quiz_selected_option = None
                    st.session_state.quiz_result_correct = None
                    st.rerun()
