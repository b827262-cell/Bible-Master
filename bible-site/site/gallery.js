/* 福音藝廊（音樂與經文圖區）前端腳本。
   嚴守鐵則：所有經文原文均透過 Bible.load(book) 從 ../data/<book>.json 讀取，本檔不寫死任何經文。 */
(function () {
  "use strict";

  Bible.nav("gallery.html");

  var stageEl = document.getElementById("gal-stage");
  var imgEl = document.getElementById("gal-img");
  var badgeEl = document.getElementById("gal-day-badge");
  var themeEl = document.getElementById("gal-theme");
  var refEl = document.getElementById("gal-ref");
  var verseEl = document.getElementById("gal-verse");
  var subtitleEl = document.getElementById("gal-subtitle");
  var trackTitleEl = document.getElementById("gal-track-title");
  var trackSubEl = document.getElementById("gal-track-sub");
  var readLinkEl = document.getElementById("gal-read-link");
  var playBtn = document.getElementById("gal-play");
  var playTextEl = document.getElementById("gal-play-text");
  var prevBtn = document.getElementById("gal-prev");
  var nextBtn = document.getElementById("gal-next");
  var fsBtn = document.getElementById("gal-fs-btn");
  var volEl = document.getElementById("gal-vol");
  var statusEl = document.getElementById("gal-status");
  var stripEl = document.getElementById("gal-strip");
  var audioEl = document.getElementById("gal-audio");

  var items = [];
  var currentIndex = 0;
  var wantPlaying = false;

  function setStatus(msg) {
    if (statusEl) {
      statusEl.textContent = msg || "";
    }
  }

  function setPlayingUI(isPlaying) {
    playBtn.setAttribute("aria-pressed", isPlaying ? "true" : "false");
    playTextEl.textContent = isPlaying ? "暫停配樂" : "播放專屬配樂";
    if (isPlaying) {
      playBtn.classList.add("gal-playing");
    } else {
      playBtn.classList.remove("gal-playing");
    }
  }

  function todayIsoWeekday() {
    var jsDay = new Date().getDay(); // 0=Sun..6=Sat
    return jsDay === 0 ? 7 : jsDay;
  }

  function findVerse(bookData, ch, v) {
    var chapter = Bible.chapterOf(bookData, ch);
    if (!chapter || !Array.isArray(chapter.verses)) {
      return null;
    }
    var target = Number(v);
    for (var i = 0; i < chapter.verses.length; i++) {
      var item = chapter.verses[i];
      if (Number(item.v) === target) {
        return item;
      }
      if (item.end != null && target >= Number(item.v) && target <= Number(item.end)) {
        return item;
      }
    }
    return null;
  }

  function syncAudio(item, autoPlay) {
    var nextSrc = item.audio || "";
    var currentSrc = audioEl.getAttribute("src") || "";
    if (currentSrc !== nextSrc) {
      audioEl.pause();
      audioEl.setAttribute("src", nextSrc);
      audioEl.load();
    }
    audioEl.volume = Number(volEl.value);
    if (autoPlay && nextSrc) {
      var p = audioEl.play();
      if (p && typeof p.then === "function") {
        p.then(function () {
          setPlayingUI(true);
          setStatus("正在播放：" + item.music_title + "（" + item.music_key + "）");
        }).catch(function () {
          wantPlaying = false;
          setPlayingUI(false);
          setStatus("瀏覽器需要您手動點擊「播放專屬配樂」以開始播放。");
        });
      }
    } else {
      setPlayingUI(false);
    }
  }

  function renderStrip() {
    stripEl.innerHTML = "";
    for (var i = 0; i < items.length; i++) {
      (function (idx, item) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "gal-thumb" + (idx === currentIndex ? " active" : "");
        btn.setAttribute("aria-pressed", idx === currentIndex ? "true" : "false");
        btn.setAttribute("aria-label", item.weekday + " " + item.theme);

        var thumbImg = document.createElement("img");
        thumbImg.src = item.image;
        thumbImg.alt = "";
        thumbImg.loading = "lazy";

        var label = document.createElement("span");
        label.className = "gal-thumb-label";

        var daySpan = document.createElement("span");
        daySpan.className = "gal-thumb-day";
        daySpan.textContent = item.weekday;

        var nameSpan = document.createElement("span");
        nameSpan.textContent = item.theme;

        label.appendChild(daySpan);
        label.appendChild(nameSpan);
        btn.appendChild(thumbImg);
        btn.appendChild(label);

        btn.addEventListener("click", function () {
          selectItem(idx, wantPlaying);
        });
        stripEl.appendChild(btn);
      })(i, items[i]);
    }
  }

  function updateStripActive() {
    var btns = stripEl.querySelectorAll(".gal-thumb");
    for (var i = 0; i < btns.length; i++) {
      var active = i === currentIndex;
      btns[i].classList.toggle("active", active);
      btns[i].setAttribute("aria-pressed", active ? "true" : "false");
    }
  }

  function selectItem(idx, keepPlaying) {
    if (!items.length) {
      return;
    }
    currentIndex = ((idx % items.length) + items.length) % items.length;
    var item = items[currentIndex];

    imgEl.src = item.image;
    imgEl.alt = item.alt || item.theme;
    badgeEl.textContent = item.weekday + " · 第 " + item.day + " 幅";
    themeEl.textContent = item.theme;
    if (item.accent) {
      themeEl.style.color = item.accent;
    }
    refEl.textContent = Bible.bookName(item.book) + " " + item.ch + ":" + item.v;
    verseEl.textContent = "正在載入經文…";
    trackTitleEl.textContent = item.music_title || "專屬配樂";
    trackSubEl.textContent = [item.music_key, item.music_bpm ? (item.music_bpm + " BPM") : "", item.music_mood]
      .filter(Boolean).join(" · ");
    readLinkEl.href = "chapter.html?book=" + encodeURIComponent(item.book) +
      "&ch=" + encodeURIComponent(item.ch) + "#v" + encodeURIComponent(item.v);

    updateStripActive();
    syncAudio(item, Boolean(keepPlaying));

    var tokenIndex = currentIndex;
    Bible.load(item.book).then(function (bookData) {
      if (tokenIndex !== currentIndex) {
        return;
      }
      var verse = findVerse(bookData, item.ch, item.v);
      if (verse) {
        refEl.textContent = Bible.ref(item.book, item.ch, verse);
        verseEl.textContent = verse.text;
      } else {
        verseEl.textContent = "找不到對應經節。";
      }
    }).catch(function (err) {
      if (tokenIndex !== currentIndex) {
        return;
      }
      verseEl.textContent = "無法載入經文資料。";
      setStatus("經文讀取失敗：" + String(err));
    });
  }

  function togglePlay() {
    if (!items.length) {
      return;
    }
    if (audioEl.paused) {
      wantPlaying = true;
      syncAudio(items[currentIndex], true);
    } else {
      wantPlaying = false;
      audioEl.pause();
      setPlayingUI(false);
      setStatus("已暫停配樂。");
    }
  }

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      if (stageEl.requestFullscreen) {
        stageEl.requestFullscreen().catch(function () {
          setStatus("目前瀏覽器不支援全螢幕靜賞模式。");
        });
      }
    } else if (document.exitFullscreen) {
      document.exitFullscreen();
    }
  }

  playBtn.addEventListener("click", togglePlay);
  prevBtn.addEventListener("click", function () {
    selectItem(currentIndex - 1, wantPlaying);
  });
  nextBtn.addEventListener("click", function () {
    selectItem(currentIndex + 1, wantPlaying);
  });
  fsBtn.addEventListener("click", toggleFullscreen);

  volEl.addEventListener("input", function () {
    audioEl.volume = Number(volEl.value);
  });

  document.addEventListener("fullscreenchange", function () {
    fsBtn.textContent = document.fullscreenElement ? "✕ 離開全螢幕" : "⛶ 全螢幕靜賞";
  });

  document.addEventListener("keydown", function (ev) {
    var target = ev.target;
    var tag = target && target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (target && target.isContentEditable)) {
      return;
    }
    // 空白鍵是可互動元件的原生啟動鍵；焦點落在按鈕或連結上時交還瀏覽器，避免覆蓋點擊行為。
    var onControl = tag === "BUTTON" || tag === "A" ||
      (target && typeof target.closest === "function" && target.closest("[role='button']"));
    if (ev.key === "ArrowLeft") {
      ev.preventDefault();
      selectItem(currentIndex - 1, wantPlaying);
    } else if (ev.key === "ArrowRight") {
      ev.preventDefault();
      selectItem(currentIndex + 1, wantPlaying);
    } else if (ev.key === " " || ev.code === "Space") {
      if (onControl) {
        return;
      }
      ev.preventDefault();
      togglePlay();
    } else if (ev.key === "f" || ev.key === "F") {
      ev.preventDefault();
      toggleFullscreen();
    }
  });

  audioEl.addEventListener("error", function () {
    wantPlaying = false;
    setPlayingUI(false);
    setStatus("音檔暫時無法播放，請稍後再試。");
  });

  fetch("../data/gospel-gallery.json")
    .then(function (res) {
      if (!res.ok) {
        throw new Error("HTTP " + res.status);
      }
      return res.json();
    })
    .then(function (data) {
      if (data && data.subtitle && subtitleEl) {
        subtitleEl.textContent = data.subtitle;
      }
      items = Array.isArray(data && data.items) ? data.items : [];
      if (!items.length) {
        throw new Error("藝廊資料為空");
      }
      var paramDay = Number(Bible.param("day"));
      var targetDay = (paramDay >= 1 && paramDay <= 7) ? paramDay : todayIsoWeekday();
      var startIdx = 0;
      for (var i = 0; i < items.length; i++) {
        if (Number(items[i].day) === targetDay) {
          startIdx = i;
          break;
        }
      }
      currentIndex = startIdx;
      renderStrip();
      selectItem(startIdx, false);
    })
    .catch(function (err) {
      verseEl.textContent = "無法載入福音藝廊資料。";
      setStatus("載入失敗：" + String(err));
    });
})();
