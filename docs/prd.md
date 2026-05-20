# 產品需求文件 (PRD) - AI 個人知識管理 Agent 系統

## 1. 產品概述
**產品名稱**：AI 個人知識管理 Agent 系統 (AI Personal Knowledge Management System)
**產品目標**：協助使用者將零散的文件 (PDF、MD) 轉化為結構化的知識圖譜，並透過多智能體 (Multi-Agent) 架構提供精準的問答檢索與自動化測驗，達到高效學習與知識內化的目的。此系統將作為期末專題。
**核心價值**：
- 自動化知識處理 (匯入、萃取、關聯)。
- 具備短期對話記憶與長期知識弱點記憶的 AI 助教。
- 支援來源追溯 (Source Attribution) 的精準 RAG 檢索。

## 2. 核心功能需求

### 2.1 知識處理管線 (Knowledge Pipeline)
- **知識匯入**：支援上傳 PDF 與 Markdown 檔案，系統自動進行文字擷取、切塊 (Chunking)，並寫入向量資料庫 (Vector DB)。
- **結構萃取 (Extractor)**：呼叫 LLM 對文本進行深度分析，自動生成章節摘要與關鍵標籤 (Tags)。
- **關係鏈結 (Graph Builder)**：利用新匯入的知識與向量庫中的舊知識進行比對，計算語義關聯性，並輸出成 Nodes 與 Edges 的 JSON 格式，為未來的知識圖譜 (Knowledge Graph) 建立基礎。

### 2.2 多智能體協作與互動 (Multi-Agent System)
- **Planner Agent (規劃智能體)**：作為系統大腦，負責分析使用者的自然語言意圖，並動態調度適合的工具 (RAG 檢索或 Quiz 生成)。
- **RAG & Memory Agent (檢索與記憶智能體)**：
  - **混合檢索 (Hybrid Search)**：結合語意搜尋 (Semantic Search) 與關鍵字搜尋 (Keyword Search) 提高檢索準確率。
  - **來源標註 (Source Attribution)**：回答時必須附帶資料來源 (如檔名、頁碼或段落)，確保知識的可靠性。
  - **記憶管理**：
    - 短期記憶 (Short-term Memory)：維持對話上下文 (Conversation Context)。
    - 長期記憶 (Long-term Memory)：記錄使用者在測驗中常錯的知識點 (Weaknesses)。

### 2.3 學習與複習機制
- **複習生成 (Quiz Master)**：根據長期記憶中的「使用者常錯知識點」與歷史閱讀紀錄，自動生成多選題 (Multiple-choice Questions) 供使用者進行測驗。

## 3. 使用者流程 (User Flow)

1. **上傳知識 (Import)**
   - 使用者透過介面上傳 PDF/MD 檔案。
   - 系統背景執行文字處理、結構萃取與關聯計算，完成後提示使用者。
2. **知識問答 (RAG Chat)**
   - 使用者詢問：「請解釋 Transformer 的 Self-Attention 機制」。
   - Planner Agent 判定為知識查詢，交由 RAG Agent 檢索資料庫。
   - 系統回覆解答，並附上來源 (e.g., `[來源：Attention Is All You Need.pdf, 頁碼 3]`)。
3. **知識測驗 (Quiz & Review)**
   - 使用者輸入：「幫我出幾題測驗來複習」。
   - Planner Agent 呼叫 Quiz Master 工具。
   - Quiz Master 讀取記憶模組中的弱點，產生相關的多選題。
   - 使用者作答，系統根據對錯更新使用者的長期弱點記憶。

## 4. 工具調用規格 (Tool Calling)
系統必須實作以下核心 Tools 供 Agent 調用：
- `ExtractorTool`: 輸入原始文本，輸出摘要與標籤。
- `GraphBuilderTool`: 輸入新知識與舊知識，輸出 Nodes/Edges 關聯 JSON。
- `QuizMasterTool`: 輸入指定主題或弱點領域，讀取長期記憶模組輸出 JSON 格式的多選題。
