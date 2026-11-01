(function (global) {
  "use strict";

  var DATA_URL = "../data/mark.json";
  var cache = null;

  function load() {
    if (cache) {
      return Promise.resolve(cache);
    }
    return fetch(DATA_URL)
      .then(function (res) {
        if (!res.ok) {
          throw new Error("無法載入經文資料（" + res.status + "）");
        }
        return res.json();
      })
      .then(function (data) {
        cache = data;
        return data;
      });
  }

  function param(name) {
    return new URLSearchParams(global.location.search).get(name);
  }

  function ref(ch, v) {
    return "馬可福音 " + ch + ":" + v;
  }

  function escape(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function chapterOf(data, ch) {
    return data.chapters.filter(function (c) {
      return c.ch === ch;
    })[0] || null;
  }

  function nav(active) {
    var host = document.getElementById("nav");
    if (!host) {
      return;
    }
    var items = [
      { key: "index", href: "index.html", label: "目錄" },
      { key: "search", href: "search.html", label: "搜尋" },
      { key: "card", href: "card.html", label: "經文卡片" }
    ];
    host.textContent = "";
    var list = document.createElement("ul");
    items.forEach(function (item) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = item.href;
      a.textContent = item.label;
      if (item.key === active) {
        a.className = "current";
        a.setAttribute("aria-current", "page");
      }
      li.appendChild(a);
      list.appendChild(li);
    });
    host.appendChild(list);
  }

  function fail(host, err) {
    if (!host) {
      return;
    }
    host.textContent = "載入失敗：" + (err && err.message ? err.message : String(err)) + "。請確認 data/mark.json 存在。";
    host.className = "error";
  }

  global.Bible = {
    load: load,
    param: param,
    ref: ref,
    escape: escape,
    chapterOf: chapterOf,
    nav: nav,
    fail: fail
  };
})(window);
