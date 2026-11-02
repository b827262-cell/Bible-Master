# Bible-Master 一鍵啟動前台與後台服務交付報告

- **報告日期**：2026-11-02
- **受測與交付專案**：`Bible-Master`（和合本四福音靜態專案與地端 AI 運維架構）
- **交付標的**：前台 & 後台一鍵啟動管理系統、後台運維管理平台、相關自動化與轉址模組
- **目標讀者**：專案經理 (PM)、技術審核員

---

## 一、需求背景與設計目標

Bible-Master 收錄和合本四福音（馬太 28 章 1,071 節、馬可 16 章 678 節、路加 24 章 1,149 節、約翰 21 章 878 節，共 3,776 節）。為使開發、測試、展示及模型協作更加敏捷，本案依專案規格設計一套**標準化一鍵啟動與服務管理體系**：

1. **前台服務 (Frontend)**：提供終端使用者瀏覽四福音經文、目錄、跨卷全文檢索與經文卡片製作。
2. **後台服務 (Backend)**：提供專案運維儀表板、經文資料庫即時監控、地端 AI 模型叢集（E500/A16/De1050/Harness）連線探測、線上測試執行控制台（Terminal Console）與報告檢視。
3. **一鍵啟動腳本 (Unified CLI)**：提供具備守護進程管理、衝突偵測、Tailscale 網路適配與平滑退出能力的服務控制腳本。
4. **鐵則相容**：維持經文只從 `data/*.json` 讀取的原則，無外部 CDN 依賴，介面全繁體中文，且完全通過專案全套客觀自動化驗證。

---

## 二、系統架構與服務配置

```
Bible-Master/
├── start.sh                      # 🚀 一鍵啟動主腳本 (可執行檔，支援 start/stop/restart/status/test/logs)
├── service.sh -> start.sh        # 服務快捷別名
├── logs/                         # 執行階段日誌與進程 PID 存放目錄 (.gitignore 已排除)
│   ├── frontend.log / .pid       # 前台輸出日誌與監聽進程 PID
│   └── backend.log / .pid        # 後台輸出日誌與監聽進程 PID
└── bible-site/
    ├── start.sh -> ../start.sh   # 子目錄執行支援捷徑
    ├── index.html                # 根路徑自動重定向頁面 (導向 /site/index.html)
    ├── site/                     # 🌐【前台服務】(Port: 8090)
    │   ├── index.html            # 四福音目錄導覽
    │   ├── chapter.html          # 逐章閱讀頁面
    │   ├── search.html           # 全文檢索與結果標記
    │   ├── card.html             # 經文圖片卡片生成器
    │   ├── style.css             # 淺色/深色無障礙樣式
    │   └── app.js                # 前台核心資料加載與互動邏輯
    └── admin/                    # ⚙️【後台服務】(Port: 8091)
        ├── server.py             # 輕量 REST API 伺服器 (純 Python 3 標準庫，零依賴)
        ├── index.html            # 後台運維儀表板
        ├── admin.css             # 後台現代化深/淺色響應式樣式 (純原生 CSS)
        └── admin.js              # 即時監控輪詢與測試串接邏輯
```

### 服務埠號與存取路徑一覽表

| 服務項目 | 預設埠號 | 本機存取網址 | Tailscale / 區網存取網址 | 主要職責 |
|---|---|---|---|---|
| **前台閱讀網站** | `8090` | `http://127.0.0.1:8090/site/index.html`<br>*(或 `http://127.0.0.1:8090/` 自動跳轉)* | `http://100.76.46.86:8090/site/index.html` | 四福音閱讀、章節切換、全文搜尋、卡片生成、深淺色無障礙閱讀。 |
| **後台管理儀表板** | `8091` | `http://127.0.0.1:8091/` | `http://100.76.46.86:8091/` | 專案總覽、四福音資料校驗、地端 AI 叢集探測、一鍵執行全檢驗、報告檢視。 |

---

## 三、後台功能亮點 (Port 8091)

1. **四福音經文資料庫監控**
   - 實時比對馬太（28 章 1071 節）、馬可（16 章 678 節）、路加（24 章 1149 節）、約翰（21 章 878 節）。
   - 確保四福音總節數 **3,776 / 3,776 節** 100% 精準無缺漏。
   - 附帶快速閱讀直達連結與原文比對觸發器。
2. **地端 AI 模型叢集即時探測**
   - **E500** (`127.0.0.1:8082`，RTX 3060 12GB · Bonsai 2 27B 160K，主編角色)：即時健康與延遲檢測。
   - **TUF A16 Tunnel** (`127.0.0.1:18083`，Bonsai 2 9B 128K，審核角色)：隧道在線探測。
   - **De1050 Tunnel** (`127.0.0.1:18087`，GTX 1050 Ti · Qwen 3.5 4B 48K，測試角色)：Ollama 隧道探測。
   - **Harness Web** (`127.0.0.1:3080`)：操作控制台連線探測（支援 HTTP 401 認證狀態識別）。
3. **一鍵品質檢驗與體檢控制台 (Interactive Terminal Console)**
   - 於後台網頁按鈕即可觸發後端執行：
     - `check_all.py`（經文比對 + 節數檔案 + Chrome 渲染檢驗 3/3 核心項）
     - `visual_checks.py`（47 項視覺對比、焦點外框與無障礙項）
     - `verify_text.py`（原文比對）
     - `smoke.js`（冒煙測試）
     - `build_data.py`（資料庫重建）
   - 終端輸出即時回傳於網頁控制台，並自動更新全站健康狀態徽章。
4. **專案歷史與報告切換檢視**
   - 線上即時切換檢視 `TEST-REPORT.md`、`FAILS.md`、`DISPATCH-REPORT.md`、`PROGRESS.md` 與 `CHANGELOG.md`。

---

## 四、CLI 啟動腳本操作指引 (start.sh)

`start.sh` 具備自動環境偵測、埠號佔用偵測（自動識別既有程序避免衝突）、PID 追蹤與守護管理功能：

### 1. 一鍵背景啟動雙端服務（預設）
```bash
./start.sh
# 或
./start.sh start
```

### 2. 即時查看運行狀態與叢集健康
```bash
./start.sh status
```
*輸出範例：*
```text
==============================================================================
           📖  Bible-Master 和合本四福音 · 前台 & 後台一鍵服務系統          
==============================================================================

--- [ 服務運行狀態 ] ---
 🌐 前台網站 (Port 8090): ● 運行中 (PID: 1277554)
    - 本機入口:   http://127.0.0.1:8090/site/index.html
    - Tailscale:  http://100.76.46.86:8090/site/index.html
 ⚙️  管理後台 (Port 8091): ● 運行中 (PID: 1277567)
    - 儀表板入口: http://127.0.0.1:8091/
    - Tailscale:  http://100.76.46.86:8091/

--- [ 地端 AI 模型叢集連線狀態 ] ---
 🤖 E500 主編 (RTX 3060 · 27B · :8082):        ● 在線
 🤖 A16 審核 Tunnel (Bonsai 9B · :18083):      ○ 離線
 🤖 De1050 測試 Tunnel (Qwen 4B · :18087):     ● 在線
 🖥️  Harness Web 控制台 (:3080):                ● 在線
```

### 3. 停止與重啟服務
```bash
./start.sh stop      # 安全發送 SIGTERM，釋放 8090 與 8091 埠號
./start.sh restart   # 一鍵重啟
```

### 4. 前景除錯模式
```bash
./start.sh -f        # 前景模式運行，按 Ctrl+C 可一併乾淨關閉前台與後台
```

### 5. 即時追蹤日誌
```bash
./start.sh logs           # 同時追蹤前台與後台日誌 (tail -f)
./start.sh logs frontend  # 僅看前台日誌
./start.sh logs backend   # 僅看後台日誌
```

### 6. 一鍵執行完整驗證套件
```bash
./start.sh test           # 自動依序執行 check_all.py 與 visual_checks.py
```

### 7. 註冊為 Linux 系統服務 (systemd user service)
```bash
./start.sh --systemd
# 產出設定檔至 ~/.config/systemd/user/bible-master.service
# 開機自動啟動：systemctl --user enable --now bible-master.service
```

---

## 五、客觀驗證與品質標準

所有變更均通過專案規定的外部客觀檢查腳本，無憑模型自稱：

1. **核心整合驗證 (`tools/check_all.py`)**：
   - 經文比對：通過（馬太 1071/1071、馬可 678/678、路加 1149/1149、約翰 878/878，無寫死經文）
   - 節數與檔案：通過（四福音總節數 3776/3776，必要檔案無缺漏）
   - 網站檢查：通過（ headless Chrome 實際開頁面驗證連結、外部資源、搜尋耶穌 1183 筆、深層錨點捲動）
   - **總結判定：3/3 項檢查全部通過（結束碼 0）**。

2. **視覺與無障礙驗證 (`tests/visual_checks.py`)**：
   - 涵蓋 320px、375px、768px、1440px 寬度響應式佈局。
   - 淺色與深色模式 WCAG 對比度均 ≥ 4.5:1。
   - 焦點外框實線 ≥ 2px、觸控區域 ≥ 44px、無水平溢出捲動。
   - **總結判定：47/47 項檢查全部通過（結束碼 0）**。

3. **雙端生命週期驗證**：
   - 前台（Port 8090）與後台（Port 8091）之啟動、並行運作、重新啟動、停止皆已在環境實測驗證，無埠號殘留或記憶體洩漏現象。

---

## 六、交付檔案清單

| 檔案路徑 | 狀態 | 說明 |
|---|---|---|
| `start.sh` | 新增 (可執行) | 一鍵啟動與服務運維管理腳本 |
| `service.sh` | 新增 (軟連結) | 導向 `start.sh` 的便捷指令 |
| `bible-site/start.sh` | 新增 (軟連結) | 支援於 `bible-site/` 子目錄下直接啟動 |
| `bible-site/index.html` | 新增 | 根目錄訪問時自動轉址至 `/site/index.html` |
| `bible-site/admin/server.py` | 新增 (可執行) | 後台 REST API 與靜態服務主程式 |
| `bible-site/admin/index.html` | 新增 | 後台運維儀表板 HTML |
| `bible-site/admin/admin.css` | 新增 | 後台專用樣式（支援系統深淺色主題） |
| `bible-site/admin/admin.js` | 新增 | 後台即時探測與測試控制台邏輯 |
| `.gitignore` | 更新 | 納入 `logs/` 與 `*.pid` 避免雜訊提交 |
| `SERVICE-REPORT.md` | 新增 | 本交付報告 |
