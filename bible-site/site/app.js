/* 四福音版網站共用腳本（和合本）。
   經文一律由 Bible.load(key) 從 ../data/<key>.json 讀取，本檔不寫入任何經文。 */
(function () {
  "use strict";

  /* 書卷清單：key 與書名。KEY 只能是 mat、mrk、luk、jhn。 */
  var BOOKS = [
    { key: "mat", name: "馬太福音" },
    { key: "mrk", name: "馬可福音" },
    { key: "luk", name: "路加福音" },
    { key: "jhn", name: "約翰福音" }
  ];

  /* 每卷各自快取：key → Promise（資料物件）。 */
  var _cache = {};

  /* 用 fetch 讀 ../data/<key>.json，每卷各自快取；回傳 Promise（資料物件）。
     失敗時清掉該卷的快取以便重試。 */
  function load(key) {
    key = bookKey(key);
    if (_cache[key] !== undefined) {
      return _cache[key];
    }
    _cache[key] = fetch("../data/" + key + ".json")
      .then(function (res) {
        if (!res.ok) {
          throw new Error("讀取經文資料失敗（HTTP " + res.status + "）");
        }
        return res.json();
      })
      .catch(function (err) {
        delete _cache[key];
        throw err;
      });
    return _cache[key];
  }

  /* 回傳 Promise，依 BOOKS 順序的四個資料物件陣列。 */
  function loadAll() {
    return Promise.all(BOOKS.map(function (book) {
      return load(book.key);
    }));
  }

  /* raw 是 BOOKS 裡的 key 就回傳它，否則回傳 "mat"。 */
  function bookKey(raw) {
    for (var i = 0; i < BOOKS.length; i++) {
      if (BOOKS[i].key === raw) {
        return BOOKS[i].key;
      }
    }
    return "mat";
  }

  /* 書名。 */
  function bookName(key) {
    key = bookKey(key);
    for (var i = 0; i < BOOKS.length; i++) {
      if (BOOKS[i].key === key) {
        return BOOKS[i].name;
      }
    }
    return "馬太福音";
  }

  /* verse 物件 → "5"；有 end 時 "1-2"。 */
  function verseLabel(verse) {
    if (typeof verse === "object" && verse !== null) {
      var v = verse.v;
      if (verse.end != null) {
        return String(v) + "-" + verse.end;
      }
      return String(v);
    }
    return String(verse);
  }

  /* 回傳「書名 {ch}:{v}」；verse 是節物件。合併節 → "路加福音 1:1-2"。 */
  function ref(key, ch, verse) {
    return bookName(key) + " " + ch + ":" + verseLabel(verse);
  }

  /* 讀取網址的查詢參數；沒有就回傳空字串。 */
  function param(name) {
    var value = new URLSearchParams(window.location.search).get(name);
    return value === null ? "" : value;
  }

  /* HTML 跳脫；所有插入頁面的文字都要經過它或用 textContent。 */
  function escape(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  /* 從資料中找出第 ch 章的物件；找不到回傳 null。 */
  function chapterOf(data, ch) {
    if (!data || !Array.isArray(data.chapters)) {
      return null;
    }
    var target = Number(ch);
    for (var i = 0; i < data.chapters.length; i++) {
      if (Number(data.chapters[i].ch) === target) {
        return data.chapters[i];
      }
    }
    return null;
  }

  /* 在 <nav id="nav"> 內產生導覽列；active 為目前頁面對應的連結。 */
  function nav(active) {
    var links = [
      { href: "index.html", label: "目錄" },
      { href: "search.html", label: "搜尋" },
      { href: "card.html", label: "經文卡片" },
      { href: "blessing.html", label: "抽經文卡" }
    ];
    var navEl = document.getElementById("nav");
    if (!navEl) {
      return;
    }
    navEl.innerHTML = "";
    var ul = document.createElement("ul");
    ul.className = "nav-list";
    for (var i = 0; i < links.length; i++) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = links[i].href;
      if (links[i].href === active) {
        a.className = "active";
      }
      a.textContent = links[i].label;
      li.appendChild(a);
      ul.appendChild(li);
    }
    navEl.appendChild(ul);
  }

  /* 在 id 為 hostId 的元素內畫四個書卷連結（page?book=key）；
     目前這卷加 aria-current="page" 與 .active。 */
  function bookTabs(hostId, activeKey, page) {
    var host = document.getElementById(hostId);
    if (!host) {
      return;
    }
    host.innerHTML = "";
    var ul = document.createElement("ul");
    ul.className = "book-tabs";
    for (var i = 0; i < BOOKS.length; i++) {
      var book = BOOKS[i];
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = page + (page.indexOf("?") === -1 ? "?" : "&") + "book=" + book.key;
      if (book.key === activeKey) {
        a.className = "active";
        a.setAttribute("aria-current", "page");
      }
      a.textContent = book.name;
      li.appendChild(a);
      ul.appendChild(li);
    }
    host.appendChild(ul);
  }

  /* 把錯誤訊息顯示到 host（可傳 DOM 元素或 id）上，並加上 .error 樣式。 */
  function fail(host, err) {
    var el = host instanceof Element ? host : document.getElementById(host);
    if (!el) {
      return;
    }
    el.textContent = "發生錯誤，無法載入資料：" + String(err || "未知錯誤");
    el.classList.add("error");
  }

  window.Bible = {
    BOOKS: BOOKS,
    load: load,
    loadAll: loadAll,
    bookKey: bookKey,
    bookName: bookName,
    verseLabel: verseLabel,
    ref: ref,
    param: param,
    escape: escape,
    chapterOf: chapterOf,
    nav: nav,
    bookTabs: bookTabs,
    fail: fail
  };
})();
