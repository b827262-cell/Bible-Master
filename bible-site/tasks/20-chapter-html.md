---
role: e500
files: [bible-site/site/chapter.html]
checks:
  - node --check bible-site/site/app.js
  - python3 bible-site/tests/site_checks.py chapter
---
四福音版網站：把 bible-site/site/chapter.html 改成支援四卷。請先讀 bible-site/prompts/multibook/SPEC.md（看「app.js 提供的 Bible 物件」那張表和「chapter.html」那一段），再讀已經改好的 bible-site/site/app.js（它已有 BOOKS、bookKey、bookName、load(key)、verseLabel、bookTabs、ref），再讀現有的 chapter.html，然後直接修改它：
1. 網址 chapter.html?book=KEY&ch=N；key = Bible.bookKey(Bible.param("book"))；ch 不合法（不是 1 到該卷章數的整數）時用 1。
2. 標題「書名 第 N 章」（書名用 Bible.bookName(key)），頁面標題 <title> 也要同樣更新。
3. 在 h1 附近放 <div id="book-tabs"></div>，呼叫 Bible.bookTabs("book-tabs", key, "chapter.html")。
4. 用 Bible.load(key) 讀資料；每節一列，節號用 Bible.verseLabel(verse)，每節 id="v"+verse.v；節有 end（合併節，例如路加 1:1–2）時，另外放一個空的 <span id="v"+verse.end> 當錨點。
5. notes 照舊顯示在「參照」區；上一章、下一章（第 1 章無上一章、最後一章無下一章，章數用 data.chapters.length）、回目錄連到 index.html?book=KEY；連結都要帶 book=KEY。
6. 畫完所有節之後讀 location.hash，有對應元素就 scrollIntoView()。
保留現有的 <link rel="icon" href="data:,">、Bible.nav("chapter.html") 和錯誤處理 Bible.fail。經文不准寫死、不載入外部資源、全繁體中文。
