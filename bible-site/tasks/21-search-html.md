---
role: e500
files: [bible-site/site/search.html]
depends: [20-chapter-html]
checks:
  - node --check bible-site/site/app.js
  - python3 bible-site/tests/site_checks.py search
---
四福音版網站：把 bible-site/site/search.html 改成可搜尋四卷。請先讀 bible-site/prompts/multibook/SPEC.md（看「app.js 提供的 Bible 物件」那張表和「search.html」那一段），再讀已經改好的 bible-site/site/app.js（它已有 BOOKS、bookKey、bookName、load(key)、loadAll、verseLabel、ref），再讀現有的 search.html，然後直接修改它：
1. 網址 search.html?q=關鍵字&book=KEY；book 是 all、mat、mrk、luk、jhn 之一，沒帶或不合法就是 all（搜全部四卷）。
2. 表單：輸入框 name="q"、下拉 name="book"（選項 all＝「全部四卷」，加上用 Bible.BOOKS 迴圈產生的四卷）、送出鈕；網址有 q 時自動搜尋並把 q、book 填回表單。
3. 搜尋用 Bible.loadAll()（搜全部）或 Bible.load(key)（搜單卷），在每一節的 text 找包含關鍵字的節（單純子字串比對）；結果依書卷順序、章節順序，全部列出、不可截斷、不分頁。
4. 每一筆：出處文字用 Bible.ref(key, ch, verse)（例如「馬太福音 5:3」；合併節「路加福音 1:1-2」），做成連到 chapter.html?book=KEY&ch=章#v節 的連結，後面接經文；經文中的關鍵字用 <mark> 標出，要先用 Bible.escape 跳脫經文和關鍵字再標。
5. 顯示「共 N 筆」；沒有關鍵字顯示提示；沒有結果顯示「找不到符合的經文」。
驗收：搜尋「耶穌」單卷：馬太 274、馬可 274、路加 326、約翰 309；全部四卷 1183 筆。
保留現有的 <link rel="icon" href="data:,">、Bible.nav("search.html") 和錯誤處理 Bible.fail。經文不准寫死、不載入外部資源、全繁體中文。
