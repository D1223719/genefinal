from typing import TypedDict, Annotated, Sequence, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from app.config import settings
from app.database import get_chat_history, get_default_user_id, save_chat_message
from app.vector_store import hybrid_search
from app.tools import get_llm, quiz_master_tool

# ==========================================
# 1. 定義 AgentState 狀態結構
# ==========================================

class AgentState(TypedDict):
    messages: Sequence[BaseMessage]
    intent: str
    context: str
    quiz_data: Dict[str, Any]

# ==========================================
# 2. 定義節點 (Node) 邏輯
# ==========================================

def planner_node(state: AgentState) -> Dict[str, Any]:
    """
    Planner Node (規劃智能體):
    作為系統的大腦，負責分析使用者的最新訊息意圖，分類為 RAG（知識問答）、QUIZ（測驗要求）或 GENERAL（一般對話），
    藉此決定後續執行流程。
    """
    last_message = state["messages"][-1].content
    llm = get_llm(temperature=0.0)  # 使用 lowest temp 以獲得精確分類
    
    prompt = f"""
你是一個智慧路由智能體 (Intent Planner)。
請分析使用者的最新訊息，判定其真實意圖，並將其歸類為以下三類之一：
- "QUIZ"：當使用者要求測驗、出題、考試、複習、做練習題時（例如：「幫我出題」、「我想考試」、「來個測驗」、「複習Transformer」）。
- "RAG"：當使用者詢問具體知識、概念、要求解釋、查詢檔案內容或尋找資料時（例如：「請解釋什麼是Attention」、「Transformer怎麼運作」、「PDF寫了什麼」、「搜尋卷積網路」）。
- "GENERAL"：當使用者進行一般問候、閒聊、打招呼、自我介紹或無法歸入上述兩類時（例如：「哈囉」、「你好」、「你是誰」、「謝謝」）。

請只回傳以下三個單字之一，不要包含任何其他字詞與符號：
QUIZ, RAG, GENERAL

使用者訊息：
"{last_message}"
"""
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        intent = response.content.strip().upper()
        # 防呆過濾
        if intent not in ["QUIZ", "RAG", "GENERAL"]:
            if "QUIZ" in intent:
                intent = "QUIZ"
            elif "RAG" in intent or "解釋" in last_message or "什麼" in last_message or "查詢" in last_message:
                intent = "RAG"
            else:
                intent = "GENERAL"
    except Exception as e:
        print(f"Planner error: {e}")
        intent = "RAG"  # 預設回退為問答
        
    return {"intent": intent}


def rag_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    RAG & Memory Node (檢索與對話智能體):
    執行 Hybrid Search 獲取相關文件 Chunk，結合短期歷史對話，呼叫 LLM 產出具備來源追溯 (Source Attribution) 的繁體中文回答。
    """
    query = state["messages"][-1].content
    
    # 1. 執行混合檢索
    retrieved_chunks = hybrid_search(query, limit=4)
    
    # 2. 格式化 Context 並記錄來源
    context_str = ""
    sources = []
    
    for i, chunk in enumerate(retrieved_chunks):
        filename = chunk["filename"]
        page = chunk["page_number"]
        text = chunk["text"]
        context_str += f"[文件{i+1}: {filename}, 頁碼: {page}]\n內容: {text}\n\n"
        
        # 收集來源 metadata
        sources.append({
            "filename": filename,
            "page_number": page,
            "preview": text[:150]
        })
        
    # 3. 獲取短期對話歷史 (作為 RAG LLM 的 Memory Context)
    db_history = get_chat_history(limit=10)
    history_str = ""
    for msg in db_history:
        role_label = "使用者" if msg["role"] == "user" else "AI"
        history_str += f"{role_label}: {msg['content']}\n"
        
    llm = get_llm(temperature=0.3)
    
    system_prompt = """你是一個親切且學術嚴謹的 AI 個人知識管理助教。
你的任務是根據「檢索到的文件內容」與「歷史對話紀錄」，用親切流畅的「繁體中文」回答使用者的問題。

重要規則：
1. **來源追溯 (Source Attribution)**：你必須在回答的論點或段落末尾，標記其參考的資料來源檔名與頁碼，格式為：`[來源: 檔案名稱, 頁碼: X]`。
   - 例如：「Transformer 使用了 Self-Attention 機制來捕捉全域特徵 [來源: Attention_Is_All_You_Need.pdf, 頁碼: 3]。」
   - 如果某個回答不是來自檢索內容，而是你的一般知識，則不需要標記來源。
2. **誠實原則**：如果檢索到的內容中沒有相關資訊，且你也無法從歷史對話中推斷，請直說「在目前的知識庫中找不到相關記載，但我可以就一般理解為您說明：」，並給予一般的學術說明。
3. 請維持對話的連貫性。
"""

    human_prompt = f"""
【歷史對話記憶】
{history_str}
【新獲取的知識庫檢索內容】
{context_str}

【使用者最新問題】
"{query}"

請開始作答：
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        ai_reply = response.content
    except Exception as e:
        ai_reply = f"抱歉，在處理您的問答時發生 AI 模型調用錯誤：{str(e)}"
        
    return {
        "messages": [AIMessage(content=ai_reply)],
        "context": context_str
    }


def quiz_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Quiz Node (測驗複習智能體):
    調用 QuizMasterTool，針對使用者的知識弱點主題動態出題，並傳回題目。
    """
    user_id = get_default_user_id()
    
    # 產生測驗
    quiz = quiz_master_tool(user_id)
    topic = quiz["topic"]
    
    intro_message = f"好的！我從長期記憶庫中分析出您對 **「{topic}」** 這個知識點需要加強複習。我已為您精心出了一道觀念題目，請在下方作答："
    
    return {
        "messages": [AIMessage(content=intro_message)],
        "quiz_data": quiz
    }

# ==========================================
# 3. 定義路由 (Routing) 邏輯
# ==========================================

def route_intent(state: AgentState):
    """根據 Planner 判斷的意圖進行分流"""
    intent = state["intent"]
    if intent in ["RAG", "GENERAL"]:
        return "rag_agent"
    elif intent == "QUIZ":
        return "quiz_agent"
    return END

# ==========================================
# 4. 建立與編譯 LangGraph 工作流
# ==========================================

workflow = StateGraph(AgentState)

# 新增節點
workflow.add_node("planner", planner_node)
workflow.add_node("rag_agent", rag_agent_node)
workflow.add_node("quiz_agent", quiz_agent_node)

# 設定起點與條件邊
workflow.set_entry_point("planner")
workflow.add_conditional_edges(
    "planner",
    route_intent,
    {
        "rag_agent": "rag_agent",
        "quiz_agent": "quiz_agent"
    }
)

# 連接到終點
workflow.add_edge("rag_agent", END)
workflow.add_edge("quiz_agent", END)

# 編譯
agent_app = workflow.compile()
