(function () {
  "use strict";

  // 前台四區（目錄／搜尋／經文卡／抽經文卡）共用的一支背景音樂。
  // 全部封閉在 IIFE 內，不設任何全域變數；元素由本檔自己建立並接到 document.body 尾端。

  const DEFAULT_MUSIC = "assets/home-music.mp3";
  const MUSIC_RE = /^assets\/[A-Za-z0-9._-]+\.mp3$/i;
  const PAUSE_LABEL = "♫ 播放音樂";
  const PLAY_LABEL = '<span class="bars" aria-hidden="true"><i></i><i></i><i></i></span> 暫停音樂';

  // 取 zone-music.json 對應當前頁面的音樂路徑：由 pathname 檔名判斷 index/search/card/blessing，
  // 對應 zones[...]，沒有則用 music，再沒有則回 assets/home-music.mp3。
  function getZoneKey() {
    const m = location.pathname.match(/(\.\/)?(index|search|card|blessing)(\.html)?$/);
    return m ? m[2] : null;
  }

  const btn = document.createElement("button");
  btn.type = "button";
  btn.id = "zone-music-btn";
  btn.setAttribute("aria-pressed", "false");
  btn.textContent = PAUSE_LABEL;

  const audio = document.createElement("audio");
  audio.id = "zone-music";
  audio.loop = true;
  audio.preload = "none";
  audio.volume = 0.6;

  document.body.appendChild(btn);
  document.body.appendChild(audio);

  // aria-pressed 永遠等於「audio 正在播放」，用 play／pause 事件同步；載入時先 render 一次。
  function render() {
    const playing = !audio.paused;
    btn.setAttribute("aria-pressed", playing ? "true" : "false");
    btn.innerHTML = playing ? PLAY_LABEL : PAUSE_LABEL;
  }
  audio.addEventListener("play", render);
  audio.addEventListener("pause", render);

  // sessionStorage 存取：每一次讀寫都包 try/catch（隐私模式可能丢例外）。
  function ssGet(key) {
    try {
      return sessionStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }
  function ssSet(key, value) {
    try {
      sessionStorage.setItem(key, value);
    } catch (e) {}
  }

  // 目前播放秒數：timeupdate、seeked、每秒（播放中）、pagehide／beforeunload 時存。
  // 還在等续播位置套用時（媒體尚未載入），不把 0 秒寫回去蓋掉上一頁存的秒數。
  let pendingSeek = 0;
  function saveT() {
    try {
      const t = audio.currentTime;
      if (!isFinite(t)) return;
      if (pendingSeek && t < pendingSeek - 1) return;
      pendingSeek = 0;
      ssSet("bm.zone.t", String(t));
    } catch (e) {}
  }
  audio.addEventListener("timeupdate", saveT);
  audio.addEventListener("seeked", saveT);
  window.addEventListener("pagehide", saveT);
  window.addEventListener("beforeunload", saveT);
  setInterval(function () {
    if (!audio.paused) saveT();
  }, 1000);

  // 回傳 Promise<boolean>：audio.play() 被拒絕就是 false。
  function tryPlay() {
    const attempt = audio.play();
    if (attempt && typeof attempt.then === "function") {
      return attempt.then(function () {
        return true;
      }, function () {
        return false;
      });
    }
    return Promise.resolve(true);
  }

  // 「第一次觸碰」：只掛 click／pointerup／touchend＋keydown，絕不掛 pointerdown／touchstart／mousedown。
  const GESTURES = ["click", "pointerup", "touchend", "keydown"];
  let firstGestureArmed = false;
  let disarmFirstGesture = function () {};
  function armFirstGesture() {
    if (firstGestureArmed) return;
    firstGestureArmed = true;
    function onFirstGesture(event) {
      // 忽略來自 #zone-music-btn 的事件（那是使用者按按鈕，走 click handler）。
      if (btn && event.target && btn.contains(event.target)) {
        return;
      }
      disarmFirstGesture();
      tryPlay().then(function (ok) {
        if (ok) {
          ssSet("bm.zone.on", "1");
        } else {
          armFirstGesture(); // 那次觸碰只是捲動等：保持掛著，等下一次。
        }
      });
    }
    function cleanup() {
      firstGestureArmed = false;
      GESTURES.forEach(function (name) {
        document.removeEventListener(name, onFirstGesture);
      });
    }
    disarmFirstGesture = cleanup;
    GESTURES.forEach(function (name) {
      document.addEventListener(name, onFirstGesture);
    });
  }

  // 拿到路徑之後：設 src、套用舊秒數（同一路徑才套用）、依使用者選擇播或停。
  function applySrc(src) {
    const savedSrc = ssGet("bm.zone.src");
    const savedT = ssGet("bm.zone.t");
    audio.src = src;
    ssSet("bm.zone.src", src);
    const wantSeek = savedSrc === src && savedT != null && Number(savedT) > 0;
    if (wantSeek) {
      pendingSeek = Number(savedT);
      try {
        audio.currentTime = Number(savedT);
      } catch (e) {}
      // 瀏覽器可能在載入過程中丟掉這次跳轉：載入的每個階段都檢查，還沒到就再跳一次，直到位置生效。
      const ensureSeek = function () {
        if (!pendingSeek) return;
        if (audio.currentTime >= pendingSeek - 1) {
          pendingSeek = 0;
          return;
        }
        try {
          audio.currentTime = pendingSeek;
        } catch (e2) {}
      };
      ["loadedmetadata", "loadeddata", "canplay", "playing", "timeupdate"].forEach(function (name) {
        audio.addEventListener(name, ensureSeek);
      });
    }
    const on = ssGet("bm.zone.on");
    if (on === "0") {
      // 使用者上次選擇暫停：到此為止，不播放、也不掛第一次觸碰監聽。
      render();
      return;
    }
    tryPlay().then(function (ok) {
      if (ok) {
        render();
      } else {
        armFirstGesture();
      }
    });
  }

  // 依頁面 (index/search/card/blessing) 取音樂：由 zone-music.json 的 zones[...] 或 music 或預設。
  function applyMusicForPage() {
    return fetch("../data/zone-music.json")
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (cfg) {
        if (!Object.prototype.hasOwnProperty.call(cfg, "zones") || !cfg.zones) {
          return cfg.music || DEFAULT_MUSIC;
        }
        const key = getZoneKey();
        if (key && Object.prototype.hasOwnProperty.call(cfg.zones, key)) {
          return cfg.zones[key];
        }
        return cfg.music || DEFAULT_MUSIC;
      })
      .then(function (src) {
        applySrc(typeof src === "string" && MUSIC_RE.test(src) ? src : DEFAULT_MUSIC);
      })
      .catch(function () {
        applySrc(DEFAULT_MUSIC);
      });
  }

  // 按鈕 click：先拆掉「第一次觸碰」監聽；暫停中 → 播（寫 on=1），否則 → 停（寫 on=0）。
  btn.addEventListener("click", function () {
    disarmFirstGesture();
    if (audio.paused) {
      ssSet("bm.zone.on", "1");
      tryPlay().then(function (ok) {
        if (ok) render();
      });
    } else {
      ssSet("bm.zone.on", "0");
      audio.pause();
      render();
    }
  });

  // 頁面載入時讀設定
  applyMusicForPage();

  render();
})();
