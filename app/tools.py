import json
import re
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings
from app.database import SessionLocal, Document, KnowledgeGraph, WeaknessMemory, add_graph_edge

# 初始化 Gemini LLM
def get_llm(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    """初始化並獲取 ChatGoogleGenerativeAI 實例"""
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY is not configured. Please edit .env file and set your API key.")
    
    return ChatGoogleGenerativeAI(
        model=settings.MODEL_NAME,
        google_api_key=api_key,
        temperature=temperature
    )

def extract_text_content(content) -> str:
    """
    安全擷取 LLM 回覆的文字內容。
    新版 Gemini 模型（3.5+）的 response.content 可能回傳 list 結構（含 type/text/extras），
    而非純字串。此函式統一將其轉為字串。
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # 從結構化回覆中提取所有 text 欄位
        texts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                texts.append(block["text"])
            elif isinstance(block, str):
                texts.append(block)
        return "\n".join(texts) if texts else str(content)
    return str(content)

def clean_json_string(text: str) -> str:
    """清理 LLM 回傳字串中的 Markdown json 標記，使其成為標準 JSON"""
    # 移除 ```json ... ``` 標記
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    return text.strip()

# ==========================================
# 1. ExtractorTool
# ==========================================

def extractor_tool(text: str) -> Dict[str, Any]:
    """
    ExtractorTool: 讀取文本，呼叫 LLM 進行深度分析，生成摘要與關鍵標籤。
    """
    llm = get_llm(temperature=0.1)
    
    prompt = f"""
你是一個專業的學術與文件分析專家。請閱讀以下文本，並完成兩項任務：
1. 精煉出 3 至 4 句的繁體中文摘要。
2. 提取出 3 到 6 個代表此文件核心概念的「繁體中文」關鍵標籤 (Tags)（例如：注意力機制、Transformer、深度學習等，每個標籤為短辭，長度小於 10 字）。

請嚴格遵循以下 JSON 格式回傳，不要有任何其他敘述：
{{
  "summary": "這裡填寫繁體中文摘要內容...",
  "tags": ["標籤一", "標籤二", "標籤三"]
}}

待分析文本：
{text[:4000]}  # 限制輸入字數以防超過 Context
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        cleaned_content = clean_json_string(extract_text_content(response.content))
        result = json.loads(cleaned_content)
        
        # 確保格式正確
        if "summary" not in result:
            result["summary"] = "無法產出有效摘要。"
        if "tags" not in result or not isinstance(result["tags"], list):
            result["tags"] = ["綜合知識"]
            
        return result
    except Exception as e:
        print(f"ExtractorTool error: {e}")
        return {
            "summary": f"處理文件時發生錯誤：{str(e)}",
            "tags": ["錯誤回報"]
        }

# ==========================================
# 2. GraphBuilderTool
# ==========================================

def graph_builder_tool(new_tags: List[str], summary: str) -> Dict[str, Any]:
    """
    GraphBuilderTool: 比對新標籤與庫中舊標籤，計算語意關聯並輸出 Nodes/Edges JSON，然後將關聯寫入 SQLite DB。
    """
    db = SessionLocal()
    existing_tags = set()
    try:
        # 從現有 Documents 撈取所有已存在的標籤
        docs = db.query(Document).all()
        for doc in docs:
            for tag in doc.tags:
                existing_tags.add(tag)
    finally:
        db.close()
        
    # 如果庫中沒有其他標籤，新標籤彼此之間建立基本的包含關係或自關聯即可
    existing_tags_list = list(existing_tags - set(new_tags))
    
    llm = get_llm(temperature=0.2)
    
    prompt = f"""
你是一個知識工程專家，負責建置結構化知識圖譜。
現在有幾個剛從新文件中提取出的新概念標籤：{new_tags}。
而知識庫中已經存在以下的舊概念標籤：{existing_tags_list[:20]}。

文件摘要背景資訊：
{summary}

請根據語意與背景，推論這些新標籤之間，或是新舊標籤之間是否存在實質的知識關聯？
有效的關係類型如下：
- "depends_on" (A依賴B，例如：Transformer 依賴 注意力機制)
- "contains" (A包含B，例如：深度學習 包含 卷積神經網路)
- "relates_to" (A與B高度相關，例如：強化學習 與 Q-Learning)

請輸出他們之間的關係邊界 (edges)，關係必須具備方向性與權重 (weight，0.0 到 1.0 的浮點數，代表關聯緊密度)。
請嚴格遵循以下 JSON 格式回傳（若無關聯可回傳空陣列，勿瞎編），不要有任何其他敘述：
{{
  "relations": [
    {{"source": "來源概念", "target": "目標概念", "relation": "depends_on/contains/relates_to", "weight": 0.8}}
  ]
}}
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        cleaned_content = clean_json_string(extract_text_content(response.content))
        result = json.loads(cleaned_content)
        
        relations = result.get("relations", [])
        
        # 寫入 SQLite Database
        count = 0
        for rel in relations:
            s = rel.get("source")
            t = rel.get("target")
            r = rel.get("relation")
            w = float(rel.get("weight", 1.0))
            if s and t and r:
                add_graph_edge(s, t, r, w)
                count += 1
                
        print(f"GraphBuilderTool: Successfully inserted {count} edges into KnowledgeGraph DB.")
        return result
    except Exception as e:
        print(f"GraphBuilderTool error: {e}")
        return {"relations": []}

# ==========================================
# 3. QuizMasterTool
# ==========================================

def quiz_master_tool(user_id: int) -> Dict[str, Any]:
    """
    QuizMasterTool: 根據長期弱點記憶產生多選題。
    """
    db = SessionLocal()
    topic = "綜合知識"
    error_count = 0
    try:
        # 找出使用者錯誤次數最高且大於 0 的弱點
        weakness = db.query(WeaknessMemory)\
                     .filter(WeaknessMemory.user_id == user_id)\
                     .order_by(WeaknessMemory.error_count.desc())\
                     .first()
        if weakness and weakness.error_count > 0:
            topic = weakness.topic
            error_count = weakness.error_count
        else:
            # 若無弱點，隨機從現有標籤中選一個，或從隨機文件中選
            doc = db.query(Document).order_by(Document.created_at.desc()).first()
            if doc and doc.tags:
                import random
                topic = random.choice(doc.tags)
    finally:
        db.close()
        
    llm = get_llm(temperature=0.6) # 稍微提高創意
    
    prompt = f"""
你是一個嚴謹的 AI 學習導師，負責為使用者出題以評估學習成效。
現在使用者在知識點「{topic}」有較多錯誤紀錄 (錯誤指數: {error_count})。
請針對「{topic}」這個主題，生成一題具有深度、概念理解性質的繁體中文多選題（四選一單選題）。

題目要求：
1. 必須以「繁體中文」撰寫。
2. 題目應該側重於核心概念的理解與分析，而非死記硬背。
3. 提供 4 個選項：A, B, C, D。
4. 提供正確答案（必須是 "A"、"B"、"C"、"D" 其中之一）。
5. 提供詳盡、易懂且有啟發性的解答解析 (explanation)。

請嚴格遵循以下 JSON 格式回傳，不要有任何其他敘述：
{{
  "topic": "{topic}",
  "question": "題目描述...",
  "options": {{
    "A": "選項 A 敘述...",
    "B": "選項 B 敘述...",
    "C": "選項 C 敘述...",
    "D": "選項 D 敘述..."
  }},
  "answer": "正確答案字母",
  "explanation": "這題為什麼是這個答案的繁體中文解析..."
}}
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        cleaned_content = clean_json_string(extract_text_content(response.content))
        result = json.loads(cleaned_content)
        
        # 驗證輸出完整性
        required_keys = ["topic", "question", "options", "answer", "explanation"]
        for key in required_keys:
            if key not in result:
                raise KeyError(f"Missing required key in Quiz output: {key}")
                
        return result
    except Exception as e:
        print(f"QuizMasterTool error: {e}")
        # 失敗時的精緻預設回退題
        return {
            "topic": topic,
            "question": f"關於「{topic}」的基礎學理，下列敘述何者最為正確？",
            "options": {
                "A": "它是該學科領域的核心基礎組件之一，有助於系統化分析。",
                "B": "它只是一個暫時性的技術，目前已被完全取代。",
                "C": "它的設計初衷是為了解決所有與運算無關的問題。",
                "D": "它不需要與任何其他組件協同運作，可完全獨立發揮全部功能。"
            },
            "answer": "A",
            "explanation": f"「{topic}」在當前技術與知識體系中扮演著核心的角色。選項 A 正確指出了其作為核心組件的學術地位；其餘選項過於絕對或偏離事實。"
        }
