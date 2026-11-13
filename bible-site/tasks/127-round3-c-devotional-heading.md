---
pane: w2:p5
role: qwen
files:
  - bible-site/site/style.css
  - bible-site/site/devotional.html
depends:
  - 126-round3-b-heart-blessing
timeout_min: 15
checks:
  - python3 bible-site/tests/site_checks.py devotional
  - python3 bible-site/tests/visual_checks.py p0 p1 p2 --grep "devotional\.html"
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，只能修改 front matter 列出的檔案：`bible-site/site/style.css` 與 `bible-site/site/devotional.html`。
**重要：請勿呼叫 `AskUserQuestion`，也切勿執行含 `<<'PY'` 多行 heredoc 的 bash 指令（會觸發 Qwen CLI 審批確認視窗而導致 pane 進入 blocked 狀態），只執行單行指令即可。**

請依據 `bible-site/logs/herdr-dispatch/brief-20261113-round3.md` 的「C. 每日禱讀頁標題層級」完成修正：

1. **問題原因**：
   - `devotional.js` 渲染 `#reading.dev` 時，當天標題（例「到主面前得安息」）是 `<h2>`，而「經文／默想／反思／禱告」段落標題是 `<h3>`。
   - 先前 `style.css` 沿用樣本三的選擇器寫了 `.dev h3 { font-size: clamp(1.7rem, 1.2rem + 2vw, 2.4rem); }` 與 `.dev h4 { font-size: .8rem; ... }`，導致正式頁的段落標題 `<h3>` 變成超大字，反而比當天標題 `<h2>` 還大，主次顛倒。
2. **修正方式**：
   - 在 `bible-site/site/style.css`（及／或 `devotional.html`）調整 `.dev` 標題樣式：
     - 當天標題 `.dev h2`：使用明體 `font-family: var(--display);`、大字級 `font-size: clamp(1.7rem, 1.2rem + 2vw, 2.4rem); line-height: 1.25; margin: 0;`（全篇最大）。
     - 段落標題 `.dev h3`（保留 `.dev h4` 相容）：使用 `font-family: var(--body); font-size: 1rem; letter-spacing: .14em; color: var(--river); font-weight: 700; margin: 0;`（次之，明顯小於 `.dev h2`）。
   - 確認 41 項 `devotional` 檢查加上新增的「當天標題字級 > 段落標題字級」檢查與 `visual_checks.py` 全數通過。
