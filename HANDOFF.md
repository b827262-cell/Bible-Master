# 交接文件：地端模型設定 + 聖經網站開發計劃

整理日期：2026-11-01（14:00 停止後）。給新專案目錄、新對話使用。
內容分三部分：A 三台機器的最終設定、B 怎麼用 Harness 操作、C 聖經網站計劃與目前進度。
詳細計劃另見 `bible-site/PLAN.md`。
**2026-11-01 15:30 更新：專案已複製到 `/home/b827262/project/AI/Bible-Master/`（原目錄 `tools/Harness-model/` 保留不動）。下文的 `tools/Harness-model/bible-site/` 都改讀作 `Bible-Master/bible-site/`，`.verify/mark.txt` 在 `Bible-Master/.verify/`。建站已拆成 5 份小任務提示，在 `bible-site/prompts/01..05-*.md`。**

---

## A. 三台地端模型：最終設定

排序原則（使用者指定）：token 數 > 分數 > 時間。

| 機器 | 位置 | 硬體 | 模型 | 最終設定 | 實測結果 |
|---|---|---|---|---|---|
| **E500** | 本機 `127.0.0.1:8082` | RTX 3060 12GB | Bonsai 2 27B PQ2_0 | 160K、medium 思考、溫度 0.4 | 約 6.8K token，約 98 到 100 分 |
| **TUF A16** | `10.0.3.67`（ssh 使用者 `b822726`），server `127.0.0.1:8083`，經 tunnel 到本機 `18083` | 8GB GPU、14GB RAM | Bonsai 2 9B Q2_0 | 128K、開啟思考（`enable_thinking:true`）、溫度 0.4 | 約 11K token，約 59 到 69 分（不思考只有約 34 分） |
| **De1050 / dp1050** | `10.0.3.70`（ssh 使用者 `b827262`），Ollama，經 tunnel 到本機 `18087` | GTX 1050 Ti 4GB、32GB RAM | Qwen3.5 4B Q4_K_M（Ollama 模型 `qwen35-4b-fast-48k`） | 48K、不思考、`top_k 1`（貪婪）、溫度 0.4 | 平均約 68 分；v3 題約 79 分 |

### 最終測試題（v3：IPv4 區段運算）三台比較
- E500：100 / 100 / 100，約 5.9K token，約 190 秒。
- A16：45 / 42 / 42，約 12K token，約 126 秒。
- De1050（溫度 0.2、思考漏進程式碼的舊設定）：0 / 0 / 0。改成不思考、貪婪後約 79 分。
- 題目與評分：`tools/llm-bench/v3/{prompt.txt,grade.py,reference/,final_test.py,results/}`。
- 自動調參：`tools/llm-bench/autotune/{run.py,summary.py,final_pick.py,results/}`。
- 舊題（Mark 經文卡、日期、排程）：`tools/llm-bench/{題目.md,grade.py,reference/,results/}`。
- 模型自己說「測試全過」不可信，一律用外部評分腳本。

### 各機器啟動檔與設定位置
- **E500**：`~/project/Bonsai-demo/start_e500_pq2_160k.sh`
  - 關鍵參數：`BONSAI_CTX=163840`、`BONSAI_KV4=1`、`BONSAI_NGL=99`、`--parallel 1 -b 512 -ub 256`、`--temp 0.4 --min-p 0 --presence-penalty 1.0 --repeat-penalty 1.0 --repeat-last-n 64`、`--chat-template-kwargs '{"reasoning_effort":"medium"}'`。
  - 備份：`.before-t04-final`。
- **TUF A16**：A16 上的 `~/project/Bonsai-demo/start_tufa16_9b_q2_128k.sh`
  - 關鍵參數：`BONSAI_CTX=131072`、`BONSAI_KV4=0`（f16 KV，q4_0 會傷品質）、`PORT=8083`、alias `bonsai2-9b-q2-tufa16-128k`、`--temp 0.4`、`--chat-template-kwargs '{"enable_thinking":true}'`。
  - 這個模板會忽略 `reasoning_effort`，只有 `enable_thinking` 有用。
  - 備份：`.before-low-final`、`.before-nothink-final`、`.before-think-t04`。
- **De1050**：Ollama 模型 `qwen35-4b-fast-48k`，Modelfile 內容：`num_ctx 49152`、`num_gpu 99`、`temperature 0.4`、`top_k 1`、`top_p 0.95`、`min_p 0`、`repeat_penalty 1`。
  - Ollama 重啟：`sudo systemctl start ollama`（dp1050 有免密碼 sudo）。
  - 備用：Bonsai 9B 由 systemd user unit `bonsai2-9b-q2-de1050.service` 跑在 `18085`，tunnel `bonsai-de1050-tunnel.service` 到 `18086`。
- **tunnel**：都是 E500 上的 systemd user service（`bonsai-a16-tunnel.service`、`bonsai-de1050-tunnel.service`）。所有 llama-server 都只綁 `127.0.0.1`。

### Harness 的 provider 設定
檔案：`~/.dsh/profiles/web/cordis.patch.yml`（備份在 `~/.dsh/backups/`，改之前先備份）。
- 自訂 `!!js` 標籤。驗證要用 yaml SafeLoader 加 `add_constructor(None, ...)`。
- `contextWindow` 要等於 server 的 `-c`（或 Ollama 的 `num_ctx`）。
- 模型選單中的名稱（用這些名稱選模型）：
  - `Bonsai 2 27B PQ2_0 160K medium t0.4 (E500)`：`maxTokens 32768`。
  - `A16 - Bonsai 2 9B Q2_0 - 128K think t0.4`：`maxTokens 32768`。
  - `De1050 - Qwen3.5 4B tuned (GPU 100%) - 48K no-think greedy`：`maxTokens 16384`，`contextWindow 49152`。
- **De1050 provider（`qwen35-de1050`）必要設定**：
  - `reasoning: "off"`，模型下設 `reasoningEfforts: {"off": none, low: low}` 和 `compat.thinkingFormat: openrouter`。因為 Ollama 的 `/v1` 預設會思考，要送 `reasoning:{effort:"none"}` 才會關。
  - `streamIdleTimeoutMs: 1800000`。Ollama 在模型寫完一整段工具呼叫之前不會送任何資料，預設 300 秒會被判逾時（曾連續 5 次 stream idle timeout）。
- 其他 provider 項目還在，但已不使用：`ollama-e500`、`ollama-de1050`、`ornith-a16`、`bonsai-de1050-q2`。

### 已知限制（很重要）
1. **Ollama `/v1` 不理會 Modelfile 的溫度**（一律用 1.0）。所以 De1050 用 `top_k 1` 讓輸出確定。
2. **Harness 每次呼叫的 agent 提示約 3 萬 token**。De1050 的 48K 視窗只剩約 1.8 萬可用；預填速度約 250 token/秒，光讀提示就要約 2.5 分鐘。De1050 每個任務要很小，一個任務一個新會話。
3. **小模型會捏造經文**（De1050 Bonsai 9B 的經文卡任務拿 3/10）。經文一律由腳本產生，不憑模型記憶。
4. 給小模型的資料要小：5KB 的節錄比 64KB 全文有效得多。
5. 「output token limit」常常其實是上下文塞滿。E500 曾把 8192 token 全花在思考而沒寫出檔案，所以 `maxTokens` 要夠大，單次指令也不要一次要求太多檔案。
6. 對話視窗：如果 Harness 對話用到接近視窗上限（例如 48K 的 41.5K），就開新會話，不要硬撐。
7. 14:00 之後三台機器上的服務與 agent 都已停止，要用時請重新啟動（見上面各機器的啟動檔）。

### Harness 操作備忘
- 啟動網頁版：`npx @deepseek-ai/dsh web --no-open`（網址 `127.0.0.1:3080`）。重啟後舊的登入連結會失效，要用新的。
- 用 Claude in Chrome 操作：先找「新建会话」，再點模型選擇器，選 submenu 裡的 menuitemradio；輸入框用 `find textbox` 取 ref（navigate 之後座標會變，不要用舊座標），輸入後按 Return。
- 貓聽（DS Bot）：Harness 左側欄 → DS Bot → 貓聽對話欄，不經過 Slack。設定在 `~/.dsh/bot/state.json`，模型 DeepSeek-V41-Flash-1017 High（雲端，會用額度）。它的工作區是 DS Bot 自己的，指令裡一律用絕對路徑，並先請它 `ls` 確認讀得到。

---

## B. 記憶與偏好
- 使用者用繁體中文。過程敘述用英文，結案報告用繁體中文，不用日文與簡體中文。程式碼、路徑、指令保持英文。
- 長期記憶在 `~/.claude/projects/-home-b827262-project/memory/`（`local-llm-hosts.md` 已更新最終設定）。換專案目錄後這份記憶不會自動跟過去，需要時請把本檔給新對話。

---

## C. 聖經網站計劃（和合本馬可福音）

### 目標與鐵則
- 靜態網站（只用 HTML、CSS、JavaScript）：章節目錄、逐章閱讀、全文搜尋、經文卡片。第一版為馬可福音 16 章、678 節。
- **經文只能來自腳本產生的 `data/mark.json`**（由 `.verify/mark.txt` 轉出），模型不准憑記憶寫經文。網頁用 fetch 讀 JSON，原始碼裡不可寫死經文。

### 分工（流程）
| 角色 | 機器 | 負責 | 交出 |
|---|---|---|---|
| 主編 | E500 | 寫全部網站檔案、依 `FAILS.md` 和 `REVIEW.md` 修正 | `site/`、`CHANGELOG.md` |
| 審核 | TUF A16 | 照 6 項檢查表審查，不改程式 | `REVIEW.md` |
| 測試 | De1050（新會話） | 只執行 `python3 bible-site/tools/check_all.py`，回報最後一行 | `TEST-REPORT.md` |
| 收尾 | Harness DS Bot 的貓聽 | 處理 `TODO.md` 未完成項目 | 更新 `TODO.md` |

流程：第 0 步腳本產生資料 → 第 1 輪主編建站 → 第 2 輪審核 → 第 3 輪測試 → 第 4 步主編修正（最多 3 輪）→ 第 5 步貓聽處理剩下的。整體預估 2 到 4 小時。

審核 6 項檢查表：1. 只從 JSON 讀經文；2. `verify_text.py` 678/678；3. 連結無失效；4. 無外部資源；5. 手機 375px 無橫向捲動；6. 全部繁體。

完成標準：`check_all.py` 結束代碼 0（3/3 通過）、檢查表 6 項全通過、`TODO.md` 清空或已由貓聽處理。

### 已完成的驗證工具（都在 `tools/Harness-model/bible-site/`）
| 檔案 | 功能 |
|---|---|
| `tools/build_data.py` | `mark.txt` → `data/mark.json`（16 章、678 節；各章節數 45,28,35,41,43,56,37,38,50,52,33,44,37,72,47,20） |
| `tools/verify_text.py` | 逐節比對 `mark.json` 和 `mark.txt`；`site/` 內有 12 字以上的經文片段就判不通過 |
| `tests/smoke.js` | 每章節數、總數，以及 6 個必要檔案 |
| `tests/site_checks.py` | 連結存在、無外部資源，用 headless Chrome 開頁面：`chapter.html?ch=1` 和 `?ch=16` 要顯示全部節；`search.html?q=耶穌` 要顯示 274 筆「馬可福音 章:節」 |
| `tools/check_all.py` | 一次跑上面三項，追加 `TEST-REPORT.md`，重寫 `FAILS.md`；全過才回傳 0 |
| `data/mark.json` | 已產生，678/678 驗證通過 |

`check_all.py` 已用正確與故意弄壞的樣本站驗證過，能抓到所有植入的錯誤。

### 目前進度與卡點
- **網站尚未建出來**：`site/` 是空的。E500 在 19 分鐘內沒有寫出任何檔案（推測原因，未確認：一次要求 6 個檔案，輸出額度在思考時用完）。
- 現況：`check_all.py` 為 1/3（經文比對 678/678 通過；節數與檔案、網站檢查都因 `site/` 為空而不通過）。
- 還沒做：`REVIEW.md`、`TODO.md`、`CHANGELOG.md`。
- 使用者選的是 Harness 版（完整流程），不是「快速直接呼叫」版。

### 下一步（建議）
1. 啟動 E500（`start_e500_pq2_160k.sh`）和 Harness，選 E500 160K medium 模型。
2. **把建站拆小**，一次只叫 E500 寫一到兩個檔案，每個檔案做完就跑 `check_all.py`：
   1. `app.js`（共用函式：載入 `../data/mark.json`）+ `style.css`
   2. `chapter.html`（`?ch=N`，顯示全部節）
   3. `index.html`（16 章目錄）
   4. `search.html`（支援 `?q=`，結果顯示「馬可福音 章:節」）
   5. `card.html`（選一節、下載成圖片）
3. 檔案齊全後：A16 審核 → De1050 新會話跑 `check_all.py` → E500 依 `FAILS.md` 修正（最多 3 輪）→ 剩下的寫進 `TODO.md` 交給貓聽。
4. 指令範本（主編、修正、審核、測試、收尾）已寫在 `bible-site/PLAN.md`，直接複製貼進 Harness。

### 搬到新專案目錄時
需要一起帶走：`tools/Harness-model/bible-site/` 和 `tools/Harness-model/.verify/mark.txt`（和合本原文，64KB）。`build_data.py` 用相對路徑 `bible-site/../.verify/mark.txt` 讀它（`verify_text.py` 從 `build_data.py` 匯入同一個 `SRC`），所以 `.verify/` 要放在 `bible-site/` 的上一層；不然只要改 `build_data.py` 裡的 `SRC`。另外 `tools/llm-bench/`（若還要再評測）。啟動檔在 `~/project/Bonsai-demo/`，Harness 設定在 `~/.dsh/`，這些在專案目錄之外，不需要搬。若搬了 `bible-site/`，PLAN.md 內的 `bible-site/...` 與貓聽指令的絕對路徑要一併改成新路徑。
