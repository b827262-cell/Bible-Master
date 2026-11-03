---
role: de1050
files: [bible-site/site/blessing.html]
checks:
  - python3 bible-site/tests/site_checks.py blessing
  - python3 bible-site/tests/visual_checks.py --grep blessing
---
只改 bible-site/site/blessing.html 的一個條件判斷（修邏輯寫反）。在 `themeTabs.addEventListener("click", ...)` 裡面，現在是：
`if (!cover.hidden) {`
改成：
`if (cover.hidden) {`
意思：卡片已經顯示（封面已隱藏）時，點主題標籤才在新主題立刻抽一張新卡；還在封面時，點主題標籤只切換主題、不抽卡。
其他內容一律不動。改完只回報改了哪一行。
