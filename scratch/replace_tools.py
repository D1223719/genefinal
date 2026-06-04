import sys

with open('app/tools.py', 'r', encoding='utf-8') as f:
    content = f.read()

target_str = "def quiz_master_tool(user_id: int, topic: Optional[str] = None)"
index = content.find(target_str)
if index == -1:
    print("Target string not found!")
    sys.exit(1)

prefix = content[:index]

new_code = """def quiz_master_tool(user_id: int, topic: Optional[str] = None, count: int = 1) -> Dict[str, Any]:
    \"\"\"
    QuizMasterTool: 根據長期弱點記憶或指定主題，結合向量資料庫檢索到的文件上下文 (RAG)，產生具有深度的多選題。
    支援產生單題或多題。
    \"\"\"
    db = SessionLocal()
    error_count = 0
    
    try:
        if not topic:
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
                else:
                    topic = "綜合知識"
    finally:
        db.close()
        
    # --- RAG: 檢索與主題相關的文件段落作為出題依據 ---
    context_str = ""
    sources = []
    try:
        from app.vector_store import hybrid_search
        # 檢索 3 個相關 Chunks
        retrieved_chunks = hybrid_search(topic, limit=3)
        if retrieved_chunks:
            context_str = "\\n".join([
                f"[來源檔名: {c['filename']}, 頁碼: {c['page_number']}]\\n{c['text']}"
                for c in retrieved_chunks
            ])
            sources = [
                {
                    "filename": c["filename"],
                    "page_number": c["page_number"],
                    "preview": c["text"][:150]
                }
                for c in retrieved_chunks
            ]
    except Exception as e:
        print(f"RAG search for quiz generation failed: {e}")

    llm = get_llm(temperature=0.4) # 適度創意與精確度的平衡
    
    if context_str:
        context_prompt = f\"\"\"
請特別參考以下從使用者上傳文檔中檢索出來的【相關上下文】來進行設計，確保考題的知識與細節完全符合文檔內容，不要出現文檔中沒有的通識或錯誤設定：

【相關上下文】
{{context_str}}
\"\"\"
    else:
        context_prompt = "（目前無可用之本地文檔上下文，請根據您的一般學術知識出題）"

    if count <= 1:
        prompt = f\"\"\"
你是一個嚴謹的 AI 學習導師，負責為使用者出題以評估學習成效。
請針對知識主題「{{topic}}」生成一題具有深度、概念理解性質的繁體中文多選題（四選一單選題）。

{{context_prompt}}

題目要求：
1. 必須以「繁體中文」撰寫。
2. 題目應該側重於核心概念的理解與分析，而非死記硬背。如果提供了【相關上下文】，請務必依據上下文的真實內容進行命題與解析，避免憑空幻想。
3. 提供 4 個選項：A, B, C, D。
4. 提供正確答案（必須是 "A"、"B"、"C"、"D" 其中之一）。
5. 提供詳盡、易懂且有啟發性的解答解析 (explanation)，並在解析中提到該概念與文檔的關聯性。

請嚴格遵循以下 JSON 格式回傳，不要有任何其他敘述：
{{{{
  "topic": "{{topic}}",
  "question": "題目描述...",
  "options": {{{{
    "A": "選項 A 敘述...",
    "B": "選項 B 敘述...",
    "C": "選項 C 敘述...",
    "D": "選項 D 敘述..."
  }}}},
  "answer": "正確答案字母",
  "explanation": "這題為什麼是這個答案的繁體中文解析..."
}}}}
\"\"\"
    else:
        prompt = f\"\"\"
你是一個嚴謹的 AI 學習導師，負責為使用者出題以評估學習成效。
請針對知識主題「{{topic}}」生成共 {{count}} 題具有深度、概念理解性質的繁體中文多選題（四選一單選題）。

{{context_prompt}}

題目要求：
1. 必須以「繁體中文」撰寫，且各題目之間不可重複，應側重於該主題不同側面的核心概念理解。
2. 題目應該側重於核心概念的理解與分析，而非死記硬背。如果提供了【相關上下文】，請務必依據上下文的真實內容進行命題與解析。
3. 每題提供 4 個選項：A, B, C, D。
4. 每題提供正確答案（必須是 "A"、"B"、"C"、"D" 其中之一）。
5. 每題提供詳盡、易懂且有啟發性的解答解析 (explanation)，並在解析中提到該概念與文檔的關聯性。

請嚴格遵循以下 JSON 格式回傳，不要有任何其他敘述：
{{{{
  "topic": "{{topic}}",
  "questions": [
    {{{{
      "question": "題目 1 描述...",
      "options": {{{{
        "A": "選項 A 敘述...",
        "B": "選項 B 敘述...",
        "C": "選項 C 敘述...",
        "D": "選項 D 敘述..."
      }}}},
      "answer": "正確答案字母",
      "explanation": "題目 1 的繁體中文解析..."
    }}}},
    ...
  ]
}}}}
\"\"\"

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        text_content = extract_text_content(response.content)
        cleaned_content = clean_json_string(text_content)
        result = json.loads(cleaned_content)
        
        # 驗證輸出完整性
        if count <= 1:
            required_keys = ["topic", "question", "options", "answer", "explanation"]
            for key in required_keys:
                if key not in result:
                    raise KeyError(f"Missing required key in Quiz output: {key}")
        else:
            required_keys = ["topic", "questions"]
            for key in required_keys:
                if key not in result:
                    raise KeyError(f"Missing required key in Quiz output: {key}")
            if not isinstance(result["questions"], list) or len(result["questions"]) == 0:
                raise ValueError("questions must be a non-empty list")
                
        result["sources"] = sources
        return result
    except Exception as e:
        print(f"QuizMasterTool error: {e}")
        # 失敗時的精緻預設回退題
        fallback_option = {
            "A": "它是該學科領域的核心基礎組件之一，有助於系統化分析。",
            "B": "它只是一個暫時性的技術，目前已被完全取代。",
            "C": "它的設計初衷是為了解決所有與運算無關的問題。",
            "D": "它不需要與任何其他組件協同運作，可完全獨立發揮全部功能。"
        }
        fallback_explanation = f"「{topic}」在當前技術與知識體系中扮演著核心的角色。選項 A 正確指出了其作為核心組件的學術地位；其餘選項過於絕對或偏離事實。"
        
        if count <= 1:
            return {
                "topic": topic,
                "question": f"關於「{topic}」的基礎學理，下列敘述何者最為正確？",
                "options": fallback_option,
                "answer": "A",
                "explanation": fallback_explanation,
                "sources": sources
            }
        else:
            return {
                "topic": topic,
                "questions": [
                    {
                        "question": f"關於「{topic}」的基礎學理，下列敘述何者最為正確？",
                        "options": fallback_option,
                        "answer": "A",
                        "explanation": fallback_explanation
                    }
                ],
                "sources": sources
            }

def generate_study_guide(user_id: int, topic: str) -> Dict[str, Any]:
    \"\"\"
    根據指定的主題與 RAG 檢索出的段落，生成一份結構化的繁體中文觀念複習導讀講義。
    \"\"\"
    context_str = ""
    sources = []
    try:
        from app.vector_store import hybrid_search
        retrieved_chunks = hybrid_search(topic, limit=4)
        if retrieved_chunks:
            context_str = "\\n".join([
                f"[來源檔名: {c['filename']}, 頁碼: {c['page_number']}]\\n{c['text']}"
                for c in retrieved_chunks
            ])
            sources = [
                {
                    "filename": c["filename"],
                    "page_number": c["page_number"],
                    "preview": c["text"][:150]
                }
                for c in retrieved_chunks
            ]
    except Exception as e:
        print(f"RAG search for study guide failed: {e}")
        
    llm = get_llm(temperature=0.3)
    
    if context_str:
        context_prompt = f\"\"\"
請根據以下從使用者上傳文檔中檢索出的【相關上下文】來生成這份講義，確保講義的內容精確且貼合文檔的描述：
{{context_str}}
\"\"\"
    else:
        context_prompt = "（目前無可用之本地文檔，請根據您的一般學術知識生成複習講義）"
        
    prompt = f\"\"\"
你是一個極具教學熱忱且專業的 AI 導師。
現在，請為使用者針對知識主題「{{topic}}」製作一份精緻、具備學術深度的繁體中文「觀念複習導讀講義」。

{{context_prompt}}

請以 Markdown 格式撰寫，內容結構應包含：
1. 💡 **核心觀念解析**：用易懂且精確的文字解釋「{{topic}}」是什麼、它的設計目的或主要用途。
2. 🔑 **關鍵重點整理**：列出 3-5 個該概念的核心要點或運作步驟。
3. ⚠️ **常見誤區 / 易混淆點**：指出學生在學習這個概念時常犯的錯誤或容易搞混的地方。
4. 📝 **小試身手觀念題**：提供一題簡單的觀念思考題，並附帶簡短說明，引導使用者思考。

請讓排版美觀、層次分明、語氣親切流暢，並完全以繁體中文撰寫。
\"\"\"
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        guide_content = extract_text_content(response.content)
        return {
            "topic": topic,
            "guide_content": guide_content,
            "sources": sources
        }
    except Exception as e:
        print(f"generate_study_guide error: {e}")
        return {
            "topic": topic,
            "guide_content": f"### 觀念複習講義：{{topic}}\\n\\n抱歉，生成講義時發生錯誤：{{str(e)}}\\n\\n建議您閱讀上傳的原始文件以進行複習。",
            "sources": sources
        }
"""

with open('app/tools.py', 'w', encoding='utf-8') as f:
    f.write(prefix + new_code)

print("Successfully replaced!")
