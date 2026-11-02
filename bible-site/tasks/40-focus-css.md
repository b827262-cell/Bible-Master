---
role: a16
files: [bible-site/site/style.css]
checks:
  - python3 bible-site/tests/visual_checks.py p0 --grep '焦點外框|每條規則'
  - python3 bible-site/tests/site_checks.py index
---
只改 bible-site/site/style.css（視覺優化 P0：鍵盤焦點）。目前下拉選單 select 和搜尋結果的連結，鍵盤聚焦時只有瀏覽器預設的 1px 外框。請在檔案「最後面」新增下面這一條規則，一字不改照抄（不要加行號、不要加任何其他文字）：

a:focus-visible,
button:focus-visible,
input:focus-visible,
select:focus-visible,
[tabindex]:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: 2px;
}

其他規則都不要改、不要刪。改完只回報改了哪裡。
