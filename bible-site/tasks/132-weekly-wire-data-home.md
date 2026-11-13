---
pane: w2:p5
role: qwen
files:
  - bible-site/ASSETS-LICENSE.md
  - bible-site/site/assets/cover-1-mon.jpg
  - bible-site/site/assets/cover-2-tue.jpg
  - bible-site/site/assets/cover-3-wed.jpg
  - bible-site/site/assets/cover-4-thu.jpg
  - bible-site/site/assets/cover-5-fri.jpg
  - bible-site/site/assets/cover-6-sat.jpg
  - bible-site/site/assets/cover-7-sun.jpg
  - bible-site/data/home-week.json
  - bible-site/site/home.html
  - bible-site/site/style.css
depends:
  - 131-weekly-wire-checks
timeout_min: 20
checks:
  - python3 bible-site/tests/site_checks.py home homeweek restyle
  - python3 bible-site/tests/visual_checks.py p0 p1 p2 --grep "home\.html"
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，不可改動 `bible-site/data/home.json`。
**重要：請勿呼叫 `AskUserQuestion`，也切勿執行含 `<<'PY'` 多行 heredoc 的 bash 指令，只執行單行指令即可。**

請依據 `bible-site/logs/herdr-dispatch/brief-20261113-weekly-wire.md` 的「1. 資料」與「2. 首頁 `site/home.html`」完成實作：

1. **複製七張封面圖並登記 `ASSETS-LICENSE.md`**：
   - 將 `output/imagegen/weekly-cover-20261113/cover-1-mon.jpg` … `cover-7-sun.jpg` 複製到 `bible-site/site/assets/`。
   - 在 `bible-site/ASSETS-LICENSE.md` 登記這 7 張圖：`cover-1-mon.jpg`～`cover-3-wed.jpg` 寫明 `AGY（Google Imagen 3）`，`cover-4-thu.jpg`～`cover-7-sun.jpg` 寫明 `Codex（OpenAI image_gen）`。
2. **建立 `bible-site/data/home-week.json`**：
   - 依 `output/imagegen/weekly-cover-20261113/weekly.json` 的 7 筆（不要改選主題、座標、圖說），建立：
     `{"enabled": true, "days": [...]}`
   - 每筆格式：`{"day": 1..7, "theme": "...", "book": "...", "ch": N, "v": N, "image": "assets/cover-X-xxx.jpg", "alt": "...", "light": "#rrggbb"}`（可視需要加 `"focus": "35% 50%"`）。
   - **光色亮度調整**：星期一～三維持 `#fae1c5`、`#f9e2bc`、`#fdebcb`；星期四～日保留各自色相調亮至相對亮度 `>= 0.72`：`#ece1d2`（四）、`#f6dec8`（五）、`#eee0d1`（六）、`#f1e0ce`（日）。
   - **鐵則：`home-week.json` 不可含經文文字！**
3. **更新 `bible-site/site/home.html`（與 `style.css` 如需微調）**：
   - 同時讀取 `../data/home.json` 與 `../data/home-week.json`。
   - 解析網址 `?day=1..7`（僅接受整數 `1`～`7`，非法值忽略）；若無 `?day` 且 `home-week.json` 的 `enabled === true`，則計算台灣時間（`Asia/Taipei`）今天星期幾（1=星期一 … 7=星期日）。
   - 驗證該天項目合法（`book` 為四福音之一、`ch`/`v` 為正整數、`image` 非空、`light` 為 `#rrggbb`），讀取經文 JSON 確認該節存在，並預載圖片確認可載入（`onerror` 或任一條件失敗時，安靜退回 `home.json` 預設封面，不顯示錯誤訊息）。
   - 套用當天封面時：
     - `#hero-ref` 顯示 `星期X · 主題 · 書卷 章:節（和合本）`（例：`星期一 · 清晨禱告 · 馬可福音 1:35（和合本）`）。
     - 設定 `--sunlight` 為當天的 `light`，使 `.home-verse`、暖光漸層與按鈕描邊呼應當天光色，對比維持 `>= 7:1`。
     - `#read-link` 連到 `chapter.html?book=KEY&ch=CH#vV`。
     - `#hero-img` 套用當天 `image`、`alt` 與適當 `object-position`（如 `focus || "35% 50%"`）。
     - 音樂仍使用 `home.json` 的 `music`。
   - 確保舊的 `home`、`restyle`、`homeweek` 與 `visual_checks.py` 全數通過。
