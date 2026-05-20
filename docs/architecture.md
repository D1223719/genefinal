# 系統架構文件 (Architecture)

## 1. 核心技術選型
- **後端框架：FastAPI (Python)**
  - **選擇原因**：極致輕量、高效能，原生支援非同步 (AsyncIO) 與背景任務 (BackgroundTasks) 處理能力。這對於處理 LINE Webhook 嚴格的短暫回應時間限制非常理想。
- **LINE 串接 API：`line-bot-sdk-python` v3**
  - **選擇原因**：官方最新版本，基於 OpenAPI 生成，支援最新的 Messaging API 規格與 Webhook 事件處理。
- **資料庫：SQLite**
  - **選擇原因**：輕量、零配置、單一檔案 `.db` 即可運作，非常適合初期專案、小型 LINE Bot 用於紀錄狀態與追蹤清單，也便於備份與轉移。
- **資料庫 ORM：SQLAlchemy**
  - **選擇原因**：以物件導向的方式 (ORM) 操作資料庫，取代直接撰寫 SQL 語句。能讓程式碼更具可讀性，且未來若需無縫轉移到 PostgreSQL 或 MySQL 等關聯式資料庫也十分容易。
- **AI 模型：Gemini API (`google-generativeai`)**
  - **選擇原因**：提供強大的自然語言處理能力，用於分析股票資訊與總結追蹤清單，API 呼叫簡單。

## 2. 系統架構圖 (System Architecture)

```mermaid
graph TD
    User([LINE 使用者]) <-->|收發訊息| LinePlatform[LINE 伺服器]
    
    LinePlatform -->|HTTP POST (Webhook)| WebhookEndpoint[/FastAPI: /callback /]
    
    subgraph 伺服器端 (FastAPI Application)
        WebhookEndpoint -->|1. 驗證簽章| LineHandler[LINE Webhook Handler]
        LineHandler -->|2. 立即回傳 HTTP 200| LinePlatform
        LineHandler -->|3. 建立背景任務| BackgroundTasks[FastAPI BackgroundTasks]
        
        BackgroundTasks -->|讀寫歷史/狀態| Database[(SQLite 資料庫)]
        BackgroundTasks -->|送出分析請求| GeminiAPI[Gemini API]
        
        GeminiAPI -->|回傳分析結果| BackgroundTasks
        Database -->|提供清單/對話記憶| BackgroundTasks
        
        BackgroundTasks -->|主動回覆 (Reply Request)| LineAPI[LINE Messaging API]
    end
    
    LineAPI -->|發送分析文字訊息| LinePlatform
```

## 3. 專案目錄結構規劃 (Directory Structure)
為了保持程式碼的可擴充性與易讀性，專案將採用以下目錄結構進行切割：

```text
linebot/
├── main.py              # FastAPI 應用程式入口點，註冊 API Router 與 Lifespan
├── config.py            # 環境變數設定與讀取 (LINE/Gemini Token 等設定檔)
├── requirements.txt     # Python 相依套件列表
├── .env                 # 環境變數設定檔 (不進 Git)
├── .gitignore           # Git 忽略清單
├── docs/                # 專案文件
│   ├── PRD.md           # 產品需求文件
│   ├── SKILL.md         # 開發指南與 SDK 規範
│   └── architecture.md  # 系統架構文件 (本文件)
├── src/                 # 核心邏輯原始碼
│   ├── line_bot/        # LINE Bot 相關邏輯
│   │   ├── handler.py   # Webhook 事件解析與處理邏輯
│   │   └── reply.py     # 訊息回覆/推播 API 封裝
│   ├── database/        # 資料庫相關邏輯
│   │   ├── models.py    # SQLAlchemy 資料表模型 (Users, Messages, Watchlist)
│   │   ├── crud.py      # 資料庫操作介面 (Create, Read, Update, Delete)
│   │   └── session.py   # SQLite 連線與 Session 生成
│   └── ai/              # AI 相關邏輯
│       └── gemini.py    # 串接 Gemini API 與 Prompt 組裝邏輯
└── data/                # 本地資料儲存
    └── bot.db           # SQLite 資料庫檔案 (不進 Git)
```

## 4. 關鍵運作流程與時序設計

### 4.1 訊息接收與背景處理機制 (避免 LINE Webhook Timeout)
LINE 官方規定 Webhook 必須在數秒內回覆 HTTP 200，否則會判定失敗並重試。因呼叫 Gemini 生成分析通常會超過此限制，系統必須採用非同步背景處理：
1. **接收請求**：FastAPI `/callback` 端點接收 LINE 伺服器的請求。
2. **驗證與分發**：驗證 `X-Line-Signature`，若合法則交給 Webhook Handler。
3. **指派背景任務**：Handler 解析出使用者輸入的文字後，呼叫 FastAPI 的 `BackgroundTasks`，將「分析邏輯」交由背景執行。
4. **結束請求**：Handler 立刻回傳 `200 OK` 關閉 HTTP Request。
5. **背景非同步執行**：在背景中依序執行：「寫入資料庫 -> 呼叫 Gemini 分析 -> 呼叫 LINE Messaging API 將結果傳給使用者」。

### 4.2 資料庫記憶寫入機制 (對話上下文)
為了讓 Gemini 記得使用者的追蹤清單以及對話脈絡：
1. **寫入 User 訊息**：收到使用者訊息時，立即將內容寫入 `Messages` 表，標記 `role='user'`。
2. **組裝 AI Prompt**：從資料庫讀取該使用者的最近 N 筆紀錄 (交錯的 `user` 與 `model` 紀錄)，作為上下文 (Context) 送給 Gemini API。
3. **寫入 Model 訊息**：取得 Gemini 分析結果並成功傳送給使用者後，將該回覆內容寫入 `Messages` 表，標記 `role='model'`。
