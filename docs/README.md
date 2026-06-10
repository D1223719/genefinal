# 🧠 AI 個人知識管理 Agent 系統 (AI PKM Agent)


這是一個結合了 **檢索增強生成 (RAG)**、**多智能體協作 (Multi-Agent 工作流)** 以及 **長期記憶與弱點追蹤機制** 的全端 AI 學習輔助系統。本專案不僅能幫您從零散的文件中建立結構化知識庫，還能化身為專屬的課業助教與出題老師，針對您的學習弱點進行強化複習。

### 👥 專案組員 (Team Members)
* **黃國傑** (D1223719)
* **楊永蘭** (D1245806)
* **蔡秉倫** (D1245587)
* **辛晴** (D1150271)
* **薛帆凱** (D1150313)

### 5. 🗂️ 檔案與圖譜同步管理 (File & Graph Management)
* **批次文件刪除**：內建文件清單選取框，支援一鍵批次刪除過期或上傳錯誤的文件。
* **孤立節點自動清除**：當文件被刪除時，系統除了清空相關的向量記憶，更會自動深入 SQLite 同步清理知識圖譜中不再被任何文件關聯的孤立概念標籤 (Orphan Nodes)，維持圖譜的純淨。

### 6. ⚡ 極速非同步與抗限流防護 (Robust & Async Pipeline)
* **獨立守護執行緒 (Daemon Threads)**：將龐大繁重的文件解析、切塊與圖譜建構任務，完全抽離 FastAPI 的主執行緒。即使一口氣上傳數十個檔案，前端網頁與對話 API 也絕不卡頓。
* **智慧休眠與重試防護 (Rate-Limit Proof)**：針對 Google API 免費版嚴格的每分鐘配額，系統在 LLM (文本萃取) 與 Embedding (向量化) 的每一道關卡都實作了完整的自動休眠重試機制。徹底解決 429 Resource Exhausted 報錯，確保大容量檔案穩定上傳到底。
* **全新 API Key 支援**：支援最新版 Google AI Studio AQ. 開頭的 API 金鑰格式，並內建記憶體強制覆蓋機制，更換金鑰即時生效。

---

## ✨ 核心特色與功能 (Key Features)

### 1. 📚 知識庫匯入與互動式語意圖譜 (Knowledge Graph)
* **自動化知識萃取**：支援上傳 PDF 或 Markdown 檔案，系統會在背景非同步解析文字、進行分塊 (Chunking)，並透過 LLM (Gemini) 自動產生高品質摘要與核心概念標籤 (Tags)。
* **知識關聯推論**：自動比對新舊標籤，透過 AI 推理概念之間的依賴 (depends_on)、包含 (contains) 等關係，建構個人的知識網絡。
* **D3.js 視覺化**：前端內建互動式力導向圖 (Force-Directed Graph)，讓生硬的文本轉換成視覺化的知識宇宙。

### 2. 💬 智能課業問答助教 (RAG Chat)
* **混合檢索 (Hybrid Search)**：結合向量語意搜尋與關鍵字搜尋，精確找出知識庫中的相關片段。
* **來源追溯 (Source Attribution)**：AI 的每一個回答都會在段落末尾清楚標註來源（例如：`[📄 檔案名稱 (第 X 頁)]`），確保回答有跡可循，解決 AI 幻覺問題。
* **自動意圖識別**：基於 LangGraph 開發的 `Planner Agent`，能自動分析您的一句話是想要「一般閒聊」、「查詢知識 (RAG)」還是「要求考試 (Quiz)」。
* **Premium 深色美學介面**：使用客製化 CSS、玻璃擬態 (Glassmorphism) 設計以及順暢的微動畫，打造極致的使用者體驗。

### 3. 🎯 觀念測驗與長期記憶弱點儀表板 (Quiz Master)
* **長期弱點記憶**：系統會偷偷記錄您的每一次答題狀況。答錯的主題錯誤指數會上升，並顯示在動態的「弱點儀表板」中。
* **動態出題引擎**：點擊「🎲 呼叫 Quiz Master」，AI 導師會優先挑選您最不熟悉的「紅燈」弱點主題，為您量身打造具有深度的四選一觀念選擇題。
* **完整詳解回饋**：不只給對錯，還會給出精闢的繁體中文解析，答對後系統會自動調降您的弱點指數。

### 4. 🔄 一鍵無痕重置模式
* 為了期末報告 Demo 展示需求，側邊欄內建「🚨 危機救援：一鍵重置」按鈕。點擊後能瞬間清空 SQLite 資料庫、向量庫與上傳檔案，讓系統完美回到初始狀態，方便隨時為下一位評審重新展示。

---

## 🛠️ 技術架構 (Tech Stack)

* **前端介面 (Frontend)**：`Streamlit` (搭配高度客製化 CSS / HTML / D3.js)
* **後端服務 (Backend)**：`FastAPI` (非同步處理與 RESTful API 提供)
* **AI & Agent 框架**：`LangChain`、`LangGraph` (控制 Planner -> RAG/Quiz 分流機制)
* **大型語言模型 (LLM)**：`Google Gemini` (負責文本理解、圖譜生成、對話與出題)
* **資料儲存 (Database)**：
  * **Relational DB**：`SQLite` (儲存文件 Metadata、對話短期記憶、弱點長期記憶、圖譜邊界)
  * **Vector DB**：`InMemoryVectorStore` (儲存文本 Chunks 向量化資料，並持久化至本地檔案)

---

## 🚀 快速啟動 (Quick Start)

### 1. 環境設定
請先將專案根目錄的 `.env.template` 複製並重新命名為 `.env`，並填入您的 Gemini API 金鑰：
```env
GEMINI_API_KEY=您的_API_KEY_填在這裡
PORT=8000
DATABASE_URL=sqlite:///./knowledge_agent.db
VECTOR_STORE_PATH=vector_store.pkl
```

### 2. 啟動後端 (FastAPI)
開啟一個終端機 (Terminal)，在專案根目錄下執行：
```bash
uvicorn app.main:app --port 8000 --reload
```

### 3. 啟動前端 (Streamlit)
開啟第二個終端機，執行：
```bash
streamlit run frontend.py
```
> 系統會自動開啟瀏覽器，預設網址為 `http://localhost:8501`。

---

## 👨‍💻 系統架構圖預覽
```mermaid
graph TD
    User([使用者 User]) -->|上傳文件 / 聊天問答| App[Streamlit 前端 UI]
    App -->|API 請求| FastAPI[FastAPI 後端]

    subgraph 背景處理管道 (Pipeline)
        FastAPI -->|文本萃取| Extractor[摘要 & 標籤提取]
        Extractor -->|建構圖譜| GraphBuilder[知識關聯推論]
        Extractor -->|文件切塊| EmbedModel[向量化 Embedding]
        EmbedModel --> VectorDB[(向量資料庫)]
        GraphBuilder --> MySQL[(SQLite 資料庫)]
    end

    subgraph 多智能體協作 (LangGraph Multi-Agent)
        FastAPI -->|對話訊息| Planner[大腦 Planner Agent]
        
        Planner -->|意圖分析: 問答| RAGAgent[RAG 檢索智能體]
        Planner -->|意圖分析: 測驗| QuizMaster[Quiz 測驗智能體]
        
        RAGAgent -->|Hybrid Search| VectorDB
        QuizMaster -->|讀取錯誤紀錄| MySQL
        
        RAGAgent -->|回覆與來源追溯| Output[Response]
        QuizMaster -->|動態生成題目| Output
    end
    
    Output --> FastAPI --> App
```
