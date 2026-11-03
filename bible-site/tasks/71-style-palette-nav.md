---
role: a16
files: [bible-site/site/style.css]
checks:
  - python3 bible-site/tests/site_checks.py blessstyle --grep "style.css"
  - python3 bible-site/tests/visual_checks.py p0 p1 --grep "導覽列|對比|焦點|style.css|觸控|粗體"
---
只改 bible-site/site/style.css 三個地方，其他規則一律不動。

1. 檔案最上面的 `:root { ... }`（淺色）改成以下變數（`--focus` 保留原值 #b35400）：
   --bg: #f7f5ef; --surface: #ffffff; --card-bg: #fffcf5; --fg: #2c2b28; --muted: #635f56;
   --border: #ded8cc; --accent: #7a4a1f; --accent-fg: #ffffff; --accent-soft: #f3ead8;
   `@media (prefers-color-scheme: dark) { :root { ... } }`（深色）改成（`--focus` 保留原值 #e0a45c）：
   --bg: #161513; --surface: #22201c; --card-bg: #28251f; --fg: #ede9df; --muted: #aba69b;
   --border: #3d3932; --accent: #deb068; --accent-fg: #171614; --accent-soft: #352c1e;

2. `.nav-list a.active` 整條規則換成（目前頁不再是實心色塊，改用底部指示線）：
```css
.nav-list a.active {
  background: transparent;
  color: var(--accent);
  font-weight: 700;
  text-decoration: none;
  border-bottom: 3px solid var(--accent);
  border-radius: 0;
}
```

3. 在 `/* ===== 按鈕與表單 ===== */` 那段的 `button:focus, ...` 規則之後，新增次要按鈕樣式：
```css
.btn-secondary {
  background: var(--surface);
  color: var(--fg);
  border: 1px solid var(--border);
}

.btn-secondary:hover {
  background: var(--accent-soft);
  border-color: var(--accent);
  filter: none;
}
```
改完只回報改了哪幾行。
