---
pane: w2:p5
role: qwen
files:
  - bible-site/site/devotional.html
  - bible-site/site/devotional.js
depends:
  - 121-restyle-blessing
timeout_min: 20
checks:
  - python3 bible-site/tests/site_checks.py devotional
  - python3 bible-site/tests/site_checks.py restyle
  - python3 bible-site/tools/check_all.py
  - python3 bible-site/tests/visual_checks.py
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，只能修改 front matter 列出的檔案：`bible-site/site/devotional.html` 與 `bible-site/site/devotional.js`。

請參照 `bible-site/design/sample-2026-11.html`（樣本三：每日禱讀）與 `bible-site/logs/herdr-dispatch/brief-20261113-restyle.md`，將禱讀頁 `bible-site/site/devotional.html` 與 `bible-site/site/devotional.js` 改版為 2026-11 新外觀，同時嚴格保留 `site_checks.py devotional` 的全部 41 條檢查契約：

1. **版面與樣本三「每日禱讀」視覺（`devotional.html` + `devotional.js`）**：
   - 使用 `.wrap`／`.panel` 容器，保留 `<p><a class="pill" href="home.html">← 回首頁</a></p>`、明體主標題 `<h1>每日禱讀</h1>`（≥ 20px）、`<label for="reading-date">選擇日期</label>`、`<input id="reading-date" type="date">`、`<p class="status" id="reading-status" role="status" aria-live="polite">正在載入禱讀資料…</p>`、`<article id="reading" class="dev"></article>`。
   - 保留 `devotional.html` 只載入 `app.js` 與 `devotional.js`（`re.findall(r'src="([^"]+)"', html_src) == ["app.js", "devotional.js"]`）。
2. **`devotional.js` 結構與微互動三種狀態（嚴格相容 `devotional_render`）**：
   - **重要 DOM 契約**（`site_checks.py` 的 `DEVOTIONAL_PROBE` 會取 `#reading` 內所有葉節點 `leaves = [...read.querySelectorAll("*")].filter(e => !e.querySelector("*"))`）：
     - `nodes[0]` 必須是 `<h2>` 且文字等於 `match.title`（無標題時為 `match.scripture_reference`）。
     - `nodes[1]` 必須是 `<p>` 且文字等於 `match.scripture_reference`（例如可加上 `.eyebrow` class）。
     - 接著是 `<h3>經文</h3>`，後面緊接每節一個 `<p>`（格式 `章:節 文字`，合併節 `章:節–末節 文字`），直到下一個 `<h3>`。
     - 接著依序為 `<h3>默想</h3>` + `<p>`、`<h3>反思</h3>` + `<p>`、`<h3>禱告</h3>` + `<p class="pray">`（**禱告段落加上 `class="pray"`**，套用樣本三的淺綠底塊 `background: var(--river-soft); border-radius: var(--r-md); padding: 20px 22px; font-family: var(--display); font-size: 1.2rem; line-height: 1.9;`！）。
   - **微互動狀態（`#reading-status`）**：
     - 載入資料與載入經文期間：`status.dataset.state = 'busy'`（文字 `'正在載入禱讀資料…'`／`'正在載入經文…'`）。
     - 渲染成功時：`status.removeAttribute('data-state')` 且 **`status.textContent = ''`**（必須是空字串，以通過 `devotional` 檢查「內容渲染成功時 `#reading-status` 是空字串」！）。
     - 無資料或錯誤時：`status.dataset.state = 'fix'`，文字維持既有三種繁體中文提示（`'此日期尚無已審核的禱讀內容。'`、`'禱讀資料載入失敗，請稍後再試。'`、`'經文載入失敗，請稍後再試。'`）。
3. **全套驗證**：
   - 完成後執行 `python3 bible-site/tests/site_checks.py devotional`、`python3 bible-site/tests/site_checks.py restyle`、`python3 bible-site/tools/check_all.py`、`python3 bible-site/tests/visual_checks.py`，確認全部通過。
   - **重要：請勿呼叫 `AskUserQuestion`，也切勿執行含 `<<'PY'` 多行 heredoc 或 `mkdir /tmp/...` 的複合 bash 指令（會觸發 Qwen CLI 審批確認視窗而導致 pane 進入 blocked 狀態），只執行 front matter `checks:` 列出的單行 `python3` 指令即可。**
