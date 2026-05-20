# 產品需求文件 (PRD) - 股票小幫手 LINE Bot

## 1. 產品概述
**產品名稱**：股票小幫手 LINE Bot (Stock Assistant Bot)  
**產品目標**：提供一個輕量、易用的 LINE 聊天機器人，讓使用者可以直接在 LINE 中透過 AI 進行股票分析，並管理個人的股票追蹤清單。  
**設計原則**：架構簡單、可執行、具備記憶對話與使用者狀態的能力，且不牽涉過於複雜的系統架構。

## 2. 核心功能需求
### 2.1 LINE 訊息接收與基礎回覆 (LINE Messaging API v3)
- **訊息接收**：接收使用者的文字訊息 (Text Message)。
- **非同步回覆**：因 AI 生成與資料庫操作可能耗時，設計上需將耗時操作移至背景處理，處理完畢後再透過 API 回傳結果給使用者。

### 2.2 AI 股票分析與對話 (Gemini API)
- **即時分析與問答**：使用者可輸入股票代號或名稱，Bot 會將請求發送給 Gemini，產生相關的股票資訊與分析回覆。
- **記憶對話脈絡**：在呼叫 Gemini 進行推論時，需附上前幾次的對話紀錄 (從資料庫撈取)，讓 AI 具備上下文記憶功能，能針對同一個話題延續討論。

### 2.3 使用者狀態與紀錄管理 (SQLite)
- **使用者註冊**：接收到訊息時，自動確認並記錄該 `userId` 至資料庫。
- **對話歷史紀錄**：詳細記錄使用者傳送的文字與 Bot 回覆的文字，作為 AI 記憶來源。
- **追蹤清單 (Watchlist)**：允許使用者透過特定指令 (或自然語言判斷) 將股票加入個人的追蹤名單中。

## 3. 使用者流程 (User Flow)
1. **加入好友與對話**
   - 使用者傳送任何訊息，系統自動記錄 `userId`。
2. **個股分析**
   - 使用者輸入：「幫我分析台積電 (2330)」或「2330 最近如何？」。
   - Bot 將問題連同過往對話紀錄送給 Gemini，取得分析後回覆給使用者。
   - 系統記錄一問一答至 SQLite。
3. **管理追蹤清單**
   - 使用者輸入：「新增 2330 到追蹤清單」或「移除 2330」。
   - 系統更新 SQLite 中的 Watchlist 紀錄，並回覆：「已成功將 2330 加入追蹤清單」。
4. **檢視追蹤清單**
   - 使用者輸入：「我的追蹤清單有哪些？」或「幫我總結一下我的追蹤清單」。
   - 系統從 SQLite 取出清單，可直接列出，或是結合 Gemini 給出整體的快速總覽。

## 4. 系統架構規劃
- **後端框架**：FastAPI (輕量、內建非同步與背景工作支援)。
- **LINE 串接**：`line-bot-sdk-python` v3。
- **AI 引擎**：`google-generativeai` (Gemini API)。
- **資料庫**：SQLite (`sqlite3` 或 `SQLAlchemy`)，單一檔案儲存即可，降低維護門檻。

### 資料庫綱要設計 (Schema Draft)
1. **Users 表**
   - `user_id`: String (Primary Key, LINE 的 userId)
   - `created_at`: Timestamp
2. **Messages 表 (記憶與對話脈絡)**
   - `id`: Integer (Primary Key, Auto Increment)
   - `user_id`: String (Foreign Key)
   - `role`: String ('user' 或是 'model')
   - `content`: Text (訊息內容)
   - `created_at`: Timestamp
3. **Watchlist 表 (追蹤清單)**
   - `id`: Integer (Primary Key, Auto Increment)
   - `user_id`: String (Foreign Key)
   - `stock_symbol`: String (股票代號)
   - `created_at`: Timestamp

## 5. 開發階段劃分 (Milestones)
- **Phase 1: 環境與基礎建置**
  - 建立 FastAPI 專案，設定 `.env` 環境變數 (LINE Tokens, Gemini API Key)。
  - 串接 LINE Bot Webhook，測試簡單的 Echo 機器人是否成功運作。
- **Phase 2: 資料庫與記憶機制**
  - 建立 SQLite 表格。
  - 實作對話時自動記錄 UserID 與 Message 至資料庫的功能。
- **Phase 3: AI 整合**
  - 串接 Gemini API。
  - 實作擷取 SQLite 歷史訊息並轉化為 Gemini Prompt 的機制。
  - 處理 LINE Webhook 的「背景執行」邏輯，避免等待 Gemini 回應超時。
- **Phase 4: 追蹤清單功能實作**
  - 解析使用者新增/刪除/查詢追蹤清單的意圖 (可透過 Gemini 工具調用或簡單的正則表達式)。
  - 完成對應的 SQLite 操作並給予使用者回饋。

## 6. 注意事項與限制
- **LINE 逾時重試機制**：LINE Webhook 必須在短時間內回傳 HTTP 200。因 Gemini 生成可能超過數秒，**強烈建議** 在 FastAPI 端點接收到請求後，直接回傳 `200 OK`，並將 "呼叫 Gemini 與回覆訊息" 的任務丟入 `BackgroundTasks` 執行。
- **資安防護**：絕對不可以將任何 API Key 或 Secret 寫死在程式碼中。
