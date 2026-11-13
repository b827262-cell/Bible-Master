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

  /* 經文卡的飛鷹圖檔：頁面一律讀這兩個路徑，不要各自寫死檔名。
     back＝抽經文卡抽卡前的卡背；face＝經文卡片的卡面。 */
  var CARD_ART = { back: "assets/eagle-A.jpg", face: "assets/eagle-B.jpg" };

  /* 底部膠囊導覽列只有五項，閱讀與卡片頁要對到它們所屬的入口，
     這樣每個前台頁面都恰好有一項被標成目前頁。 */
  var NAV_KEYS = {
    "": "home.html",
    "home.html": "home.html",
    "index.html": "index.html",
    "chapter.html": "index.html",
    "devotional.html": "devotional.html",
    "blessing.html": "blessing.html",
    "card.html": "blessing.html",
    "search.html": "search.html"
  };

  /* 元素或 id 都可傳的共用取法。 */
  function pick(node) {
    if (node instanceof Element) {
      return node;
    }
    return typeof node === "string" ? document.getElementById(node) : null;
  }

  /* 處理中：轉圈圖示＋「…中」文字，aria-busy 並鎖住按鈕免於重複送出。 */
  function busy(btn, label) {
    var node = pick(btn);
    if (!node) {
      return null;
    }
    if (!node.getAttribute("data-label")) {
      node.setAttribute("data-label", node.textContent.trim());
    }
    node.setAttribute("aria-busy", "true");
    if ("disabled" in node) {
      node.disabled = true;
    } else {
      node.setAttribute("aria-disabled", "true");
    }
    node.textContent = "";
    var spin = document.createElement("span");
    spin.className = "spin";
    spin.setAttribute("aria-hidden", "true");
    node.appendChild(spin);
    node.appendChild(document.createTextNode(" " + (label || "處理中…")));
    return node;
  }

  /* 結束處理中：還原成可按的按鈕；文字沒給就用原本那句話。 */
  function settle(btn, label) {
    var node = pick(btn);
    if (!node) {
      return null;
    }
    node.removeAttribute("aria-busy");
    node.removeAttribute("aria-disabled");
    if ("disabled" in node) {
      node.disabled = false;
    }
    node.textContent = label || node.getAttribute("data-label") || "";
    return node;
  }

  /* 把結果寫進狀態列：state 是 busy／ok／fix，圖示由 style.css 的 data-state 畫，
     這裡只保證它是 live 區（WCAG 2.2 4.1.3：不必取得焦點也讀得到）。 */
  function say(statusEl, state, text) {
    var node = pick(statusEl);
    if (!node) {
      return null;
    }
    if (state) {
      node.setAttribute("data-state", state);
    } else {
      node.removeAttribute("data-state");
    }
    if (!node.getAttribute("role")) {
      node.setAttribute("role", "status");
    }
    if (!node.getAttribute("aria-live")) {
      node.setAttribute("aria-live", "polite");
    }
    node.textContent = text || "";
    return node;
  }

  /* 全網站共用的短訊息膠囊；2.6 秒後淡出。內容同時寫進 live 區。 */
  var _toastTimer = null;
  function toast(text) {
    var node = document.querySelector(".toast");
    if (!node) {
      node = document.createElement("div");
      node.className = "toast";
      node.setAttribute("role", "status");
      node.setAttribute("aria-live", "polite");
      document.body.appendChild(node);
    }
    node.textContent = text || "";
    node.classList.add("show");
    if (_toastTimer) {
      clearTimeout(_toastTimer);
    }
    _toastTimer = setTimeout(function () {
      node.classList.remove("show");
    }, 2600);
    return node;
  }

  /* 在 <nav id="nav"> 內畫五項底部浮動膠囊導覽列；active 是呼叫端頁面的檔名。 */
  function nav(active) {
    var links = [
      { href: "home.html", label: "首頁" },
      { href: "index.html", label: "目錄" },
      { href: "devotional.html", label: "禱讀" },
      { href: "blessing.html", label: "抽卡" },
      { href: "search.html", label: "搜尋" }
    ];
    var current = NAV_KEYS[active || ""] || "home.html";
    var navEl = document.getElementById("nav");
    if (!navEl) {
      return;
    }
    navEl.classList.add("dock");
    navEl.setAttribute("aria-label", "主要導覽");
    navEl.innerHTML = "";
    var ul = document.createElement("ul");
    ul.className = "nav-list";
    for (var i = 0; i < links.length; i++) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = links[i].href;
      a.textContent = links[i].label;
      if (links[i].href === current) {
        /* 目前頁：aria-current 讓螢幕閱讀器聽得到，粗體＋實心底色讓它不只靠顏色分辨。 */
        a.className = "active";
        a.setAttribute("aria-current", "page");
      }
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

  /* 把錯誤訊息顯示到 host（可傳 DOM 元素或 id）上，並當成「待修正」的狀態列。 */
  function fail(host, err) {
    var el = pick(host);
    if (!el) {
      return;
    }
    el.textContent = "發生錯誤，無法載入資料：" + String(err || "未知錯誤");
    el.classList.add("error");
    el.setAttribute("role", "status");
    el.setAttribute("aria-live", "polite");
    el.setAttribute("data-state", "fix");
  }

  window.Bible = {
    BOOKS: BOOKS,
    CARD_ART: CARD_ART,
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
    busy: busy,
    settle: settle,
    say: say,
    toast: toast,
    fail: fail
  };
})();
