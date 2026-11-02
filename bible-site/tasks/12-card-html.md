---
role: e500
files: [bible-site/site/card.html]
checks:
  - node --check bible-site/site/app.js
  - python3 bible-site/tests/site_checks.py card
---
修正 bible-site/site/card.html（只改這一個檔案）。測試發現三個問題：(a) 章下拉 #ch-select 完全沒有選項；(b) 書卷下拉 #book-select 的值永遠是 mat，不管網址是 book=luk 還是 book=jhn；(c) 網址不合法（例如 ?book=zzz&ch=99&v=99）時什麼都沒畫，應該退回馬太福音 1:1。請先讀 bible-site/prompts/multibook/SPEC.md 的 Bible 函式表和 card.html 那一段，再讀 bible-site/site/app.js 與目前的 card.html，然後修改 card.html，讓它符合：
1. 三個下拉：#book-select（選項來自 Bible.BOOKS，value=key）、#ch-select（選項 1 到該卷章數，value=章號，文字「第 N 章」）、#v-select（選項是該章每一節，value=verse.v，文字用 Bible.verseLabel(verse)）。
2. 載入時：book = Bible.bookKey(Bible.param("book"))；ch 和 v 若不是該卷合法的值就用 1；然後把三個下拉的 value 都設成目前的 book、ch、v（#book-select.value 必須等於目前這卷），再畫卡片。
3. 換書卷：重新載入該卷資料，章回到 1、節回到 1，重建章與節下拉；換章：節回到 1，重建節下拉；換節：重畫。
4. 每次畫完卡片，執行 canvas.setAttribute("data-ref", 出處字串)，出處字串就是畫在卡片上的那一行，格式 Bible.ref(book, ch, verse) + "（和合本）"（合併節會是「路加福音 1:1-2（和合本）」）。
5. 下載檔名維持 book + "-" + ch + "-" + v + ".png"。
保留 <link rel="icon" href="data:,">、Bible.nav("card.html")、錯誤處理。經文不准寫死、不載入外部資源。
