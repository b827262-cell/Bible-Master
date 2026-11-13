---
pane: w2:p5
role: qwen
files:
  - bible-site/site/app.js
  - bible-site/site/style.css
  - bible-site/site/chapter.html
  - bible-site/site/index.html
depends:
  - 127-round3-c-devotional-heading
timeout_min: 25
checks:
  - python3 bible-site/tests/site_checks.py chapter index bookmarks
  - python3 bible-site/tools/check_all.py
  - python3 bible-site/tests/visual_checks.py
  - python3 bible-site/tests/deploy_checks.py
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，只能修改 front matter 列出的檔案：`bible-site/site/app.js`、`bible-site/site/style.css`、`bible-site/site/chapter.html`、`bible-site/site/index.html`。
**重要：請勿呼叫 `AskUserQuestion`，也切勿執行含 `<<'PY'` 多行 heredoc 的 bash 指令（會觸發 Qwen CLI 審批確認視窗而導致 pane 進入 blocked 狀態），只執行單行指令即可。**

請依據 `bible-site/logs/herdr-dispatch/brief-20261113-round3.md` 的「D. 收藏經節（新功能，照 AGY 上輪建議做純前端版）」與 `bible-site/design/sample-2026-11.html` 的「樣本二／樣本四」，實作純前端收藏經節功能並通過全套檢查：

1. **共用儲存模組（`bible-site/site/app.js`）**：
   - `localStorage` 鍵名固定為 `'bible.bookmarks.v1'`。
   - **鐵則：只存座標 `{ book, ch, v, at }`，絕不存經文文字（且 `localStorage.getItem('bible.bookmarks.v1')` 字串中不可含任何中文字元 `[㐀-鿿]`）！**
     - `book` 只接受 `'mat'`、`'mrk'`、`'luk'`、`'jhn'`；`ch` 與 `v` 為正整數；`at` 為純 ASCII 日期／時間字串（如 `'2026-11-13T00:00:00Z'`，不可含中文）。
     - 每個陣列元素的 `Object.keys` 只能是 `book`、`ch`、`v`、`at` 的子集，寫入前一律過濾掉任何其他欄位。
   - **損壞資料與 `localStorage` 不可用時的容錯（極重要：探測器 `noticeText(d)` 檢查）**：
     - 當 `localStorage.getItem('bible.bookmarks.v1')` 拋出例外、內容不是合法 JSON（例如 `"{bad json"`）、不是陣列、或陣列內含有無效座標項目時，不可拋出未捕捉錯誤使頁面崩潰；
     - **頁面初始載入時（`index.html` 與 `chapter.html` 兩頁一載入就要檢查，不必等使用者點經節或展開 details）**，若發現 `bible.bookmarks.v1` 資料損壞或無法讀取，必須在畫面上一個**可見的葉節點元素**（沒有子元素 `!e.querySelector("*")` 且 `visible`，不可藏在預設收合的 `<details>` 裡；若放在 `<details id="bookmarks-box">` 內，當 `corrupted` 為真時必須自動把 `details.open = true`）顯示繁體中文提示，且文字必須同時符合 `/收藏/` 與 `/(損壞|無法|讀取失敗|載入失敗|清除|重新)/`，例如：
       `"收藏資料損壞或無法讀取，已略過異常項目（可重新收藏或清除本機資料）"`。
2. **閱讀頁 `bible-site/site/chapter.html`**：
   - 頁面載入時先檢查 `Bible.bookmarks.read()`：若 `corrupted` 為真，立即在 `#status`（`role="status"`）顯示 `data-state="fix"` 與 `"收藏資料損壞或無法讀取，已略過異常項目（可重新收藏）"`。
   - 點選經文節（如 `#v16`）展開的 `.chips` 操作列中，在「做成經文卡片 →」旁加入收藏按鈕：
     - `<button type="button" class="pill keep" data-bookmark-btn="1" aria-pressed="false">收藏這一節</button>`
     - 若該節已在收藏清單中，展開時即設為 `aria-pressed="true"`、文字為 `"✓ 已收藏"`（不只靠顏色分辨）。
     - 點擊按鈕時切換收藏狀態：
       - 新增收藏：設 `aria-pressed="true"`、文字改為 `"✓ 已收藏"`，並在 `#status`（`role="status"`）以 `Bible.say(status, "ok", "已收藏 " + book.name + " " + chNum + ":" + v.v + "（本機儲存）")` 播報（文字必須同時含 `"已收藏"`、`"約翰福音 3:16"` 格式出處、`"本機儲存"`）。
       - 取消收藏：設 `aria-pressed="false"`、文字改回 `"收藏這一節"`，並在 `#status`（`role="status"`）以 `Bible.say(status, "ok", "已取消收藏 " + book.name + " " + chNum + ":" + v.v + "（本機儲存）")` 播報（文字必須同時含 `"已取消收藏"` 與 `"約翰福音 3:16"` 格式出處）。
     - 重新整理 `chapter.html` 後再點 `#v16`，按鈕必須維持 `aria-pressed="true"` 與 `"✓ 已收藏"`。
3. **目錄頁 `bible-site/site/index.html`**：
   - 在 `<main class="wrap">` 內加入「我的收藏（N 節）」摺疊區 `<details class="panel bookmarks-panel" id="bookmarks-box">`：
     - `<summary id="bookmarks-summary">我的收藏（0 節）</summary>`（當有 N 筆收藏時更新為 `我的收藏（N 節）`，例如 `我的收藏（1 節）`）。
     - 狀態提示 `<p class="status" id="bookmarks-status" role="status" aria-live="polite"></p>`：當 `localStorage` 不可用或資料損壞（如 `"{bad json"`）時，自動將 `details#bookmarks-box` 設為 `open = true`，並讓 `#bookmarks-status` 顯示 `"收藏資料損壞或無法讀取，已略過異常項目（可重新收藏）"`（確保 `#bookmarks-status` 無子元素且可見）。
     - 清單容器 `<ul class="bookmarks-list" id="bookmarks-list"></ul>` 與空狀態說明 `<p class="bookmarks-empty" id="bookmarks-empty">尚未收藏經節。在閱讀頁點選任何一節經文，即可按「收藏這一節」保存在本機。</p>`（注意：空狀態說明必須用 `<p>`，不可放在 `<li>` 內，這樣 0 筆時 `box.querySelectorAll("li").length` 才會是 `0`）。
     - 當有收藏項目時，透過 `Bible.load(item.book)` **動態讀取 JSON 取得經文文字**，每筆 `<li class="bookmark-item">` 列出：
       - 出處（例如 `"約翰福音 3:16"`）與經文全文（與 `data/*.json` 的 `v.text` 完全一致）。
       - 操作連結／按鈕（觸控高皆 ≥ 44px）：
         1. `<a class="pill" href="chapter.html?book=KEY&ch=CH#vV">前往閱讀</a>`（`href` 必須精確為 `"chapter.html?book=" + item.book + "&ch=" + item.ch + "#v" + item.v`）
         2. `<a class="pill" href="card.html?book=KEY&ch=CH&v=V">做成經文卡片</a>`（`href` 必須精確為 `"card.html?book=" + item.book + "&ch=" + item.ch + "&v=" + item.v`）
         3. `<button type="button" class="pill bookmark-remove" data-book="KEY" data-ch="CH" data-v="V">移除</button>`（點擊後從 `localStorage` 移除該筆、重新渲染使 `<li>` 歸零、`<summary>` 更新為 `我的收藏（0 節）`、並顯示 `#bookmarks-empty` 空狀態中文說明）。
   - 底部導覽列維持固定五項（首頁、目錄、禱讀、抽卡、搜尋），且展開 `.chips` 或展開 `#bookmarks-box` 後在 320／375／768／1440px 下皆無水平溢出（`.chips` 與 `.bookmark-item` 的按鈕列請設 `flex-wrap: wrap`）。
