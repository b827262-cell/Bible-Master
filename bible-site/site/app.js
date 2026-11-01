/* 馬可福音網站共用腳本（和合本）。
   經文一律由 Bible.load() 從 ../data/mark.json 讀取，本檔不寫入任何經文。 */
(function () {
  "use strict";

  var _cache = null;

  /* 用 fetch 讀 ../data/mark.json 並快取結果，回傳 Promise。失敗時清掉快取以便重試。 */
  function load() {
    if (_cache === null) {
      _cache = fetch("../data/mark.json")
        .then(function (res) {
          if (!res.ok) {
            throw new Error("讀取經文資料失敗（HTTP " + res.status + "）");
          }
          return res.json();
        })
        .catch(function (err) {
          _cache = null;
          throw err;
        });
    }
    return _cache;
  }

  /* 讀取網址的查詢參數；沒有就回傳空字串。 */
  function param(name) {
    var value = new URLSearchParams(window.location.search).get(name);
    return value === null ? "" : value;
  }

  /* 回傳「馬可福音 {ch}:{v}」。 */
  function ref(ch, v) {
    return "馬可福音 " + ch + ":" + v;
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
      { href: "card.html", label: "經文卡片" }
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
    load: load,
    param: param,
    ref: ref,
    escape: escape,
    chapterOf: chapterOf,
    nav: nav,
    fail: fail
  };
})();
