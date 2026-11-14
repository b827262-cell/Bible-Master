document.addEventListener("DOMContentLoaded", () => {
  const terminal = document.getElementById("terminal-output");
  const terminalStatus = document.getElementById("terminal-status");

  function log(text) {
    if (!terminal) return;
    terminal.textContent = text;
    terminal.scrollTop = terminal.scrollHeight;
  }

  function appendLog(text) {
    if (!terminal) return;
    terminal.textContent += "\n" + text;
    terminal.scrollTop = terminal.scrollHeight;
  }

  // 1. 取得全站狀態
  async function loadStatus() {
    try {
      const res = await fetch("/api/status");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // 前台狀態
      const feEl = document.getElementById("status-frontend");
      if (feEl) {
        if (data.frontend.online) {
          feEl.className = "pill pill-success";
          feEl.textContent = `在線 (Port ${data.frontend.port})`;
        } else {
          feEl.className = "pill pill-error";
          feEl.textContent = "未運行";
        }
      }

      // 經文總數
      const verseEl = document.getElementById("status-verses");
      if (verseEl) {
        verseEl.textContent = `${data.total_verses} / ${data.expected_total_verses} 節`;
      }

      // 資料庫狀態
      const dbEl = document.getElementById("status-db");
      if (dbEl) {
        if (data.database_ok) {
          dbEl.className = "pill pill-success";
          dbEl.textContent = "100% 完整相符";
        } else {
          dbEl.className = "pill pill-warning";
          dbEl.textContent = "異常或缺節";
        }
      }

      // 檢查報告狀態
      const failsEl = document.getElementById("status-fails");
      if (failsEl) {
        if (data.fails_pass) {
          failsEl.className = "pill pill-success";
          failsEl.textContent = "全部通過";
        } else {
          failsEl.className = "pill pill-error";
          failsEl.textContent = "有待修項目";
        }
      }

      // 渲染書卷表格
      const tbody = document.getElementById("books-tbody");
      if (tbody && data.books) {
        tbody.innerHTML = data.books.map(b => `
          <tr>
            <td><strong>${b.name}</strong> (${b.key})</td>
            <td>${b.chapters} 章</td>
            <td>${b.verses} 節</td>
            <td>${b.match ? '<span class="pill pill-success">精準相符</span>' : '<span class="pill pill-error">不符</span>'}</td>
            <td>
              <a href="${location.protocol}//${location.hostname}:8090/site/chapter.html?book=${b.key}&ch=1" target="_blank" class="book-link">閱讀第 1 章 ↗</a>
            </td>
          </tr>
        `).join("");
      }

    } catch (err) {
      console.error("無法取得全站狀態:", err);
    }
  }

  // 2. 取得地端模型節點
  async function loadModels() {
    try {
      const res = await fetch("/api/models");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const listEl = document.getElementById("model-node-list");
      if (!listEl || !data.models) return;

      listEl.innerHTML = data.models.map(m => `
        <div class="node-item">
          <div class="node-info">
            <div class="node-name">${m.name}</div>
            <div class="node-sub">${m.host}:${m.port} ${m.latency_ms ? `· ${m.latency_ms}ms` : ''}</div>
          </div>
          <div>
            ${m.online 
              ? `<span class="pill pill-success">在線運行 (${m.latency_ms}ms)</span>` 
              : `<span class="pill pill-error" title="${m.hint}">離線未啟動</span>`}
          </div>
        </div>
      `).join("");
      const timeEl = document.getElementById("model-probe-time");
      if (timeEl && data.timestamp) timeEl.textContent = ` · 上次探測 ${data.timestamp.slice(11, 16)}`;
    } catch (err) {
      console.error("無法取得模型節點狀態:", err);
    }
  }

  // 3. 測試執行端點
  async function runAction(endpoint, btnEl, actionName) {
    if (!terminal) return;
    terminalStatus.textContent = `[執行中] 正在執行 ${actionName}...`;
    log(`>>> 開始執行：${actionName}...\n---------------------------------------------`);
    
    const origText = btnEl ? btnEl.textContent : "";
    if (btnEl) {
      btnEl.disabled = true;
      btnEl.textContent = "⏳ 執行中...";
    }

    try {
      const res = await fetch(endpoint, { method: "POST", headers: { "X-Bible-Admin": "1" } });

      if (res.status === 409) {
        terminalStatus.textContent = `[執行中] 已有動作執行中，請稍候`;
        appendLog("已有動作執行中，請稍候");
        return;
      }

      const data = await res.json();

      if (data.success) {
        terminalStatus.textContent = `[完成] ${actionName} 成功 (耗時 ${data.elapsed_seconds}s)`;
        appendLog(data.output || "（無輸出）");
        appendLog(`\n---------------------------------------------\n[OK] 結束代碼 0，耗時 ${data.elapsed_seconds} 秒`);
      } else {
        terminalStatus.textContent = `[未通過] ${actionName} (結束碼 ${data.exit_code})`;
        appendLog(data.output || "（無輸出）");
        appendLog(`\n---------------------------------------------\n[FAIL] 結束代碼 ${data.exit_code}`);
      }

      // 重載狀態
      loadStatus();
    } catch (err) {
      terminalStatus.textContent = `[錯誤] ${err.message}`;
      appendLog(`無法連接後台服務：${err.message}`);
    } finally {
      if (btnEl) {
        btnEl.disabled = false;
        btnEl.textContent = origText;
      }
    }
  }

  // 4. 報告檢視
  async function loadReport(reportName) {
    const reportViewer = document.getElementById("report-content");
    if (!reportViewer) return;
    reportViewer.textContent = "載入中...";
    try {
      const res = await fetch(`/api/report/${reportName}`);
      const data = await res.json();
      if (data.content) {
        reportViewer.textContent = data.content;
      } else {
        reportViewer.textContent = "（查無內容）";
      }
    } catch (err) {
      reportViewer.textContent = `載入報告失敗: ${err.message}`;
    }
  }

  // 依 location.hostname 組出前台／後台實際網址
  function setLinks() {
    const proto = location.protocol;
    const host = location.hostname;
    const feUrl = `${proto}//${host}:8090/site/index.html`;
    const beUrl = `${proto}//${host}:${location.port}/`;

    const feLink = document.getElementById("frontend-link");
    if (feLink) {
      feLink.href = feUrl;
    }

    const feUrlEl = document.getElementById("frontend-url");
    if (feUrlEl) {
      feUrlEl.href = feUrl;
      feUrlEl.textContent = feUrl;
    }

    const beUrlEl = document.getElementById("backend-url");
    if (beUrlEl) {
      beUrlEl.href = beUrl;
      beUrlEl.textContent = beUrl;
    }
  }

  // 5. 主頁設定
  const BOOK_NAMES = { mat: "馬太福音", mrk: "馬可福音", luk: "路加福音", jhn: "約翰福音" };
  const IMAGE_MAX_BYTES = 5 * 1024 * 1024;
  const MUSIC_MAX_BYTES = 8 * 1024 * 1024;

  let adminToken = "";      // 只放在記憶體，不寫入 localStorage
  let bookCache = {};       // 書卷 JSON 快取
  let homeDefaults = null;

  const homeEls = {
    section: document.getElementById("home-settings"),
    book: document.getElementById("home-book"),
    ch: document.getElementById("home-ch"),
    v: document.getElementById("home-v"),
    verse: document.getElementById("home-verse-preview"),
    imageFile: document.getElementById("home-image-file"),
    imageSelect: document.getElementById("home-image-select"),
    imagePreview: document.getElementById("home-image-preview"),
    alt: document.getElementById("home-alt"),
    musicFile: document.getElementById("home-music-file"),
    musicSelect: document.getElementById("home-music-select"),
    musicPreview: document.getElementById("home-music-preview"),
    save: document.getElementById("home-save"),
    reset: document.getElementById("home-reset"),
    open: document.getElementById("home-open"),
    status: document.getElementById("home-status")
  };

  // 前台四區（目錄、搜尋、經文卡片、抽經文卡）：共用一首，各區可另選一首（選單留空＝沿用共用曲）
  const ZONE_AREAS = [
    { id: "index", title: "目錄" },
    { id: "search", title: "搜尋" },
    { id: "card", title: "經文卡片" },
    { id: "blessing", title: "抽經文卡" }
  ];

  const zoneEls = {
    section: document.getElementById("zone-music-settings"),
    file: document.getElementById("zone-music-file"),
    select: document.getElementById("zone-music-select"),
    preview: document.getElementById("zone-music-preview"),
    save: document.getElementById("zone-music-save"),
    reset: document.getElementById("zone-music-reset"),
    status: document.getElementById("zone-music-status"),
    areas: {}
  };

  ZONE_AREAS.forEach(area => {
    zoneEls.areas[area.id] = {
      select: document.getElementById(`zone-${area.id}-select`),
      preview: document.getElementById(`zone-${area.id}-preview`)
    };
  });

  function homeStatus(text, kind) {
    const el = homeEls.status;
    if (!el) return;
    el.textContent = text;
    el.className = "home-status" + (kind ? " is-" + kind : "");
  }

  function zoneStatus(text, kind) {
    const el = zoneEls.status;
    if (!el) return;
    el.textContent = text;
    el.className = "home-status" + (kind ? " is-" + kind : "");
  }

  function writeHeaders(extra) {
    const headers = { "X-Bible-Admin": "1" };
    if (adminToken) headers["X-Bible-Token"] = adminToken;
    return Object.assign(headers, extra || {});
  }

  // 把伺服器回的錯誤轉成繁中訊息
  async function readError(res) {
    try {
      const data = await res.json();
      return data.error || `HTTP ${res.status}`;
    } catch (err) {
      return `HTTP ${res.status}`;
    }
  }

  function fillSelect(select, values, current) {
    if (!select) return;
    select.innerHTML = "";
    values.forEach(value => {
      const opt = document.createElement("option");
      opt.value = String(value.value);
      opt.textContent = value.label;
      select.appendChild(opt);
    });
    if (current !== undefined && current !== null) select.value = String(current);
  }

  async function loadBook(key) {
    if (bookCache[key]) return bookCache[key];
    const res = await fetch(`/api/book/${encodeURIComponent(key)}`);
    if (!res.ok) throw new Error(await readError(res));
    const data = await res.json();
    bookCache[key] = data;
    return data;
  }

  function chapterOf(data, ch) {
    return (data.chapters || []).find(c => Number(c.ch) === Number(ch)) || null;
  }

  function verseOf(chapter, v) {
    if (!chapter) return null;
    return (chapter.verses || []).find(x => Number(x.v) === Number(v)) || null;
  }

  function renderVersePreview() {
    const el = homeEls.verse;
    if (!el) return;
    const book = homeEls.book ? homeEls.book.value : "";
    const ch = homeEls.ch ? homeEls.ch.value : "";
    const v = homeEls.v ? homeEls.v.value : "";
    const data = bookCache[book];
    const chapter = data ? chapterOf(data, ch) : null;
    const verse = verseOf(chapter, v);
    if (!verse) {
      el.textContent = "載入中…";
      return;
    }
    el.innerHTML = "";
    const ref = document.createElement("span");
    ref.className = "verse-ref";
    ref.textContent = `${BOOK_NAMES[book] || book} ${ch}:${v}`;
    const text = document.createElement("span");
    text.textContent = verse.text;
    el.appendChild(ref);
    el.appendChild(text);
  }

  // 依書卷重建章下拉，再依章重建節下拉
  async function rebuildChapters(preferCh, preferV) {
    if (!homeEls.book) return;
    const book = homeEls.book.value;
    let data;
    try {
      data = await loadBook(book);
    } catch (err) {
      homeStatus(`無法讀取${BOOK_NAMES[book] || book}：${err.message}`, "error");
      return;
    }
    const chapters = (data.chapters || []).map(c => ({ value: c.ch, label: `第 ${c.ch} 章` }));
    fillSelect(homeEls.ch, chapters, preferCh !== undefined ? preferCh : (chapters[0] || {}).value);
    await rebuildVerses(preferV);
  }

  async function rebuildVerses(preferV) {
    const book = homeEls.book ? homeEls.book.value : "";
    const ch = homeEls.ch ? homeEls.ch.value : "";
    const data = bookCache[book];
    const chapter = data ? chapterOf(data, ch) : null;
    const verses = chapter ? (chapter.verses || []).map(x => ({ value: x.v, label: `第 ${x.v} 節` })) : [];
    fillSelect(homeEls.v, verses, preferV !== undefined ? preferV : (verses[0] || {}).value);
    renderVersePreview();
  }

  // 圖片與音樂的預覽由後台自己的 /site-assets/ 唯讀提供（同源，測試埠與正式埠都能用）
  function assetUrl(path) {
    return `/site-assets/${encodeURIComponent(String(path).replace(/^assets\//, ""))}`;
  }

  function updateImagePreview(path) {
    const el = homeEls.imagePreview;
    if (!el) return;
    if (!path) {
      el.hidden = true;
      el.removeAttribute("src");
      return;
    }
    el.src = assetUrl(path);
    el.hidden = false;
  }

  function updateMusicPreview(path) {
    const el = homeEls.musicPreview;
    if (!el) return;
    if (!path) {
      el.removeAttribute("src");
      return;
    }
    el.src = assetUrl(path);
  }

  function updateZoneMusicPreview(path) {
    const el = zoneEls.preview;
    if (!el) return;
    if (!path) {
      el.removeAttribute("src");
      return;
    }
    el.src = assetUrl(path);
  }

  // 分區選單留空時，實際播放的就是共用曲
  function zoneAreaPath(areaId) {
    const sel = zoneEls.areas[areaId] ? zoneEls.areas[areaId].select : null;
    const value = sel ? sel.value : "";
    return value || (zoneEls.select ? zoneEls.select.value : "");
  }

  function updateZoneAreaPreview(areaId) {
    const els = zoneEls.areas[areaId];
    if (!els || !els.preview) return;
    const path = zoneAreaPath(areaId);
    if (!path) {
      els.preview.removeAttribute("src");
      return;
    }
    const url = assetUrl(path);
    // 同一首不重載，避免換共用曲時打斷各區正在試聽的音訊
    if (els.preview.getAttribute("src") !== url) els.preview.src = url;
  }

  function fillZoneAreaSelect(areaId, paths, value) {
    const sel = zoneEls.areas[areaId] ? zoneEls.areas[areaId].select : null;
    if (!sel) return;
    const options = [{ value: "", label: "沿用共用音樂" }].concat(
      paths.map(p => ({ value: p, label: p.replace(/^assets\//, "") }))
    );
    fillSelect(sel, options, value || "");
    updateZoneAreaPreview(areaId);
  }

  // 上傳新曲子後四區也要選得到，但不動各區目前的選擇
  function addZoneAreaOption(path) {
    ZONE_AREAS.forEach(area => {
      const sel = zoneEls.areas[area.id] ? zoneEls.areas[area.id].select : null;
      if (!sel || [...sel.options].some(o => o.value === path)) return;
      const opt = document.createElement("option");
      opt.value = path;
      opt.textContent = path.replace(/^assets\//, "");
      sel.appendChild(opt);
    });
  }

  function zoneAssetPaths() {
    const seen = [];
    const selects = [zoneEls.select].concat(ZONE_AREAS.map(area => (zoneEls.areas[area.id] ? zoneEls.areas[area.id].select : null)));
    selects.forEach(sel => {
      [...(sel ? sel.options : [])].forEach(o => {
        if (o.value && seen.indexOf(o.value) === -1) seen.push(o.value);
      });
    });
    return seen;
  }

  // 目前表單狀態：四區全留空時不帶 zones 欄位
  function currentZoneConfig() {
    const music = zoneEls.select ? zoneEls.select.value : "";
    const zones = {};
    ZONE_AREAS.forEach(area => {
      const sel = zoneEls.areas[area.id] ? zoneEls.areas[area.id].select : null;
      if (sel && sel.value) zones[area.id] = sel.value;
    });
    return Object.keys(zones).length ? { music, zones } : { music };
  }

  // GET 回傳（或儲存後伺服器回的 config）→ 一次重繪共用曲與四區的選單、試聽
  function applyZonePayload(data) {
    const cfg = (data && data.config) || {};
    const current = cfg.music || (data && data.default && data.default.music) || "assets/home-music.mp3";
    const list = Array.isArray(data && data.music) ? data.music.slice() : [];
    if (list.indexOf(current) === -1) list.push(current);
    fillSelect(
      zoneEls.select,
      list.map(p => ({ value: p, label: p.replace(/^assets\//, "") })),
      current
    );
    updateZoneMusicPreview(current);
    const zones = cfg.zones && typeof cfg.zones === "object" ? cfg.zones : {};
    ZONE_AREAS.forEach(area => {
      const value = typeof zones[area.id] === "string" ? zones[area.id] : "";
      const paths = value && list.indexOf(value) === -1 ? [value].concat(list) : list;
      fillZoneAreaSelect(area.id, paths, value);
    });
  }

  function addOption(select, value) {
    if (!select) return;
    const exists = [...select.options].some(o => o.value === value);
    if (!exists) {
      const opt = document.createElement("option");
      opt.value = value;
      opt.textContent = value.replace(/^assets\//, "");
      select.appendChild(opt);
    }
    select.value = value;
  }

  function applyConfig(config) {
    if (!config) return;
    if (homeEls.book) homeEls.book.value = config.book;
    fillSelect(homeEls.imageSelect, (config._images || []).map(p => ({ value: p, label: p.replace(/^assets\//, "") })), config.image);
    fillSelect(homeEls.musicSelect, (config._music || []).map(p => ({ value: p, label: p.replace(/^assets\//, "") })), config.music);
    if (homeEls.alt) homeEls.alt.value = config.alt || "";
    updateImagePreview(config.image);
    updateMusicPreview(config.music);
    return rebuildChapters(config.ch, config.v);
  }

  async function loadHomeSettings() {
    if (!homeEls.section) return;
    try {
      const tokenRes = await fetch("/api/token");
      if (tokenRes.ok) {
        const tokenData = await tokenRes.json();
        adminToken = tokenData.token || "";
      } else {
        homeStatus(`無法取得寫入權杖（${await readError(tokenRes)}），只能檢視`, "warning");
      }

      const res = await fetch("/api/home");
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      homeDefaults = data.defaults || null;
      const config = Object.assign({}, data.defaults || {}, data.config || {});
      config._images = data.images || [];
      config._music = data.music || [];
      await applyConfig(config);
      homeStatus("已載入目前設定。", "success");
    } catch (err) {
      homeStatus(`載入主頁設定失敗：${err.message}`, "error");
    }
  }

  function readImageWidth(file) {
    return new Promise(resolve => {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        const width = img.naturalWidth;
        URL.revokeObjectURL(url);
        resolve(width);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        resolve(0);
      };
      img.src = url;
    });
  }

  async function uploadFile(kind, file, context) {
    if (!file) return;
    const ctx = context || {};
    const status = ctx.status || homeStatus;
    const limit = kind === "image" ? IMAGE_MAX_BYTES : MUSIC_MAX_BYTES;
    const limitText = kind === "image" ? "5 MB" : "8 MB";
    if (file.size > limit) {
      status(`檔案太大（${(file.size / 1024 / 1024).toFixed(1)} MB），${kind === "image" ? "圖片" : "音樂"}上限是 ${limitText}`, "error");
      return;
    }

    let widthWarning = "";
    if (kind === "image") {
      const width = await readImageWidth(file);
      if (width > 1600) widthWarning = "圖片寬度超過 1600px，建議先縮小再上傳";
    }

    status(`正在上傳 ${file.name}…`);
    try {
      const res = await fetch(`/api/upload?kind=${kind}&name=${encodeURIComponent(file.name)}`, {
        method: "POST",
        headers: writeHeaders({ "Content-Type": "application/octet-stream" }),
        body: file
      });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      const path = data.path;
      const select = ctx.select !== undefined
        ? ctx.select
        : (kind === "image" ? homeEls.imageSelect : homeEls.musicSelect);
      const updatePreview = ctx.updatePreview || (kind === "image" ? updateImagePreview : updateMusicPreview);
      if (select) addOption(select, path);
      updatePreview(path);
      if (ctx.uploadedMessage) {
        status(widthWarning || ctx.uploadedMessage, widthWarning ? "warning" : "success");
      } else {
        status(widthWarning || `已上傳 ${file.name}（${data.bytes} bytes）`, widthWarning ? "warning" : "success");
      }
      return path;
    } catch (err) {
      status(`上傳失敗：${err.message}`, "error");
    } finally {
      const fileInput = ctx.fileInput || (kind === "image" ? homeEls.imageFile : homeEls.musicFile);
      if (fileInput) fileInput.value = "";
    }
  }

  function currentConfig() {
    return {
      book: homeEls.book ? homeEls.book.value : "",
      ch: Number(homeEls.ch ? homeEls.ch.value : 0),
      v: Number(homeEls.v ? homeEls.v.value : 0),
      image: homeEls.imageSelect ? homeEls.imageSelect.value : "",
      alt: homeEls.alt ? homeEls.alt.value.trim() : "",
      music: homeEls.musicSelect ? homeEls.musicSelect.value : ""
    };
  }

  async function saveHomeSettings() {
    const btn = homeEls.save;
    if (btn) btn.disabled = true;
    homeStatus("儲存中…");
    try {
      const res = await fetch("/api/home", {
        method: "POST",
        headers: writeHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(currentConfig())
      });
      if (!res.ok) throw new Error(await readError(res));
      homeStatus("已儲存到本機。要更新線上網站，請記得執行發佈。", "success");
    } catch (err) {
      homeStatus(`儲存失敗：${err.message}`, "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function resetHomeSettings() {
    if (!window.confirm("確定要還原成預設的主頁設定嗎？")) return;
    const btn = homeEls.reset;
    if (btn) btn.disabled = true;
    homeStatus("還原中…");
    try {
      const res = await fetch("/api/home/reset", {
        method: "POST",
        headers: writeHeaders({ "Content-Type": "application/json" }),
        body: "{}"
      });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      const config = Object.assign({}, homeDefaults || {}, data.config || {});
      config._images = [...(homeEls.imageSelect ? homeEls.imageSelect.options : [])].map(o => o.value);
      config._music = [...(homeEls.musicSelect ? homeEls.musicSelect.options : [])].map(o => o.value);
      await applyConfig(config);
      homeStatus("已還原成預設的主頁設定。", "success");
    } catch (err) {
      homeStatus(`還原失敗：${err.message}`, "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function openHomePreview() {
    const url = `${location.protocol}//${location.hostname}:8090/`;
    window.open(url, "_blank");
  }

  async function loadZoneMusicSettings() {
    if (!zoneEls.section) return;
    try {
      if (!adminToken) {
        const tokenRes = await fetch("/api/token");
        if (tokenRes.ok) {
          const tokenData = await tokenRes.json();
          adminToken = tokenData.token || "";
        } else {
          zoneStatus(`無法取得寫入權杖（${await readError(tokenRes)}），只能檢視`, "warning");
        }
      }

      const res = await fetch("/api/zone-music");
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      applyZonePayload(data);
      zoneStatus("已載入目前設定。", "success");
    } catch (err) {
      zoneStatus(`載入前台音樂設定失敗：${err.message}`, "error");
    }
  }

  async function saveZoneMusicSettings() {
    const btn = zoneEls.save;
    const payload = currentZoneConfig();
    const areaCount = Object.keys(payload.zones || {}).length;
    if (btn) btn.disabled = true;
    zoneStatus("儲存中…");
    try {
      const res = await fetch("/api/zone-music", {
        method: "POST",
        headers: writeHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      applyZonePayload({ config: data.config || payload, music: zoneAssetPaths() });
      zoneStatus(areaCount ? `已儲存共用曲與 ${areaCount} 區的獨立音樂。記得執行發佈。` : "已儲存。記得執行發佈。", "success");
    } catch (err) {
      zoneStatus(`儲存失敗：${err.message}`, "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function resetZoneMusicSettings() {
    if (!window.confirm("確定要還原成預設的前台音樂嗎？四區的獨立選擇也會一起改回共用曲。")) return;
    const btn = zoneEls.reset;
    if (btn) btn.disabled = true;
    zoneStatus("還原中…");
    try {
      const res = await fetch("/api/zone-music/reset", {
        method: "POST",
        headers: writeHeaders({ "Content-Type": "application/json" }),
        body: "{}"
      });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      applyZonePayload({ config: data.config || {}, music: zoneAssetPaths(), default: data.default || {} });
      zoneStatus("已還原成預設音樂，四區也改回共用曲。", "success");
    } catch (err) {
      zoneStatus(`還原失敗：${err.message}`, "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  // 5.5 一週封面（data/home-week.json）：七張 details 編輯卡，草稿只放記憶體，按「儲存整週」一次寫回
  const WEEK_NAMES = { 1: "星期一", 2: "星期二", 3: "星期三", 4: "星期四", 5: "星期五", 6: "星期六", 7: "星期日" };
  const WEEK_DAYS = [1, 2, 3, 4, 5, 6, 7];
  const WEEK_LIGHT_BG = "#06140f";
  const WEEK_FOCUS_FALLBACK = { x: 35, y: 50 };   // 省略 focus 時，滑桿先停在 35／50，與前台預設裁切一致
  const WEEK_IMAGE_TIP_BYTES = 600 * 1024;
  const WEEK_LIGHT_MIN_LUMINANCE = 0.72;
  const WEEK_LIGHT_MIN_CONTRAST = 7;

  const weekEls = {
    section: document.getElementById("home-week-settings"),
    toggle: document.getElementById("home-week-enabled"),
    days: document.getElementById("home-week-days"),
    reload: document.getElementById("home-week-reload"),
    save: document.getElementById("home-week-save"),
    status: document.getElementById("home-week-status")
  };

  const weekState = {
    base: null,        // 最後一次由伺服器確認的乾淨設定
    draft: null,       // 目前草稿（只存在記憶體，連 enabled 也不立即寫回）
    images: [],
    ready: false,      // 是否已載入完整七天（沒有就不准儲存，避免舊草稿覆蓋）
    loadError: false,  // 最近一次載入失敗／資料不完整：保留草稿但禁止儲存
    loading: false,
    saving: false,
    uploading: 0,
    els: {}            // day -> 卡片元素
  };

  function weekStatus(text, kind) {
    const el = weekEls.status;
    if (!el) return;
    el.textContent = text;
    el.className = "home-status" + (kind ? " is-" + kind : "");
  }

  function weekLocked() {
    return weekState.loading || weekState.saving || weekState.uploading > 0;
  }

  // ---- 草稿 ↔ 設定檔的形狀 ----
  function weekSerializeOne(day) {
    const row = {
      day: Number(day.day),
      theme: String(day.theme || "").trim(),
      book: day.book,
      ch: Number(day.ch),
      v: Number(day.v),
      image: day.image,
      alt: String(day.alt || "").trim(),
      light: String(day.light || "")
    };
    const focus = String(day.focus || "").trim();
    if (focus) row.focus = focus;   // 沒動過滑桿就維持省略
    return row;
  }

  function weekPayload() {
    return {
      enabled: weekState.draft.enabled === true,
      days: weekState.draft.days.slice().sort((a, b) => a.day - b.day).map(weekSerializeOne)
    };
  }

  function weekBasePayload() {
    return {
      enabled: weekState.base.enabled === true,
      days: weekState.base.days.slice().sort((a, b) => a.day - b.day).map(weekSerializeOne)
    };
  }

  function weekDirty() {
    if (!weekState.base || !weekState.draft) return false;
    return JSON.stringify(weekPayload()) !== JSON.stringify(weekBasePayload());
  }

  function weekDayDirty(day) {
    if (!weekState.base) return false;
    const base = weekState.base.days.find(entry => Number(entry.day) === Number(day.day));
    if (!base) return true;
    return JSON.stringify(weekSerializeOne(day)) !== JSON.stringify(weekSerializeOne(base));
  }

  function weekDayFromEntry(entry) {
    return {
      day: Number(entry.day),
      theme: String(entry.theme || ""),
      book: String(entry.book || ""),
      ch: Number(entry.ch) || 0,
      v: Number(entry.v) || 0,
      image: String(entry.image || ""),
      alt: String(entry.alt || ""),
      light: String(entry.light || ""),
      focus: typeof entry.focus === "string" ? entry.focus : "",
      loadSeq: 0            // 連動載入的序號，防止舊回應蓋掉新選擇
    };
  }

  function weekFocusParts(focus) {
    const m = /^([0-9]{1,3})% ([0-9]{1,3})%$/.exec(String(focus || ""));
    if (m && Number(m[1]) <= 100 && Number(m[2]) <= 100) return { x: Number(m[1]), y: Number(m[2]) };
    return { x: WEEK_FOCUS_FALLBACK.x, y: WEEK_FOCUS_FALLBACK.y };
  }

  // ---- 驗證（與伺服器同一組規則，先在畫面上講清楚）----
  function weekLuminance(hex) {
    const channel = index => {
      const c = parseInt(hex.slice(index, index + 2), 16) / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
  }

  function weekContrast(a, b) {
    const hi = Math.max(a, b);
    const lo = Math.min(a, b);
    return (hi + 0.05) / (lo + 0.05);
  }

  function weekValidateDay(day) {
    const errors = {};
    const theme = String(day.theme || "").trim();
    if (!theme) errors.theme = "請填主題（1–40 字）。";
    else if (theme.length > 40) errors.theme = "主題最多 40 字。";
    const alt = String(day.alt || "").trim();
    if (!alt) errors.alt = "請填圖片說明（1–120 字）。";
    else if (alt.length > 120) errors.alt = "圖片說明最多 120 字。";
    const light = String(day.light || "");
    if (!/^#[0-9a-fA-F]{6}$/.test(light)) {
      errors.light = "請填 #rrggbb 六位色碼。";
    } else {
      const lum = weekLuminance(light);
      if (lum < WEEK_LIGHT_MIN_LUMINANCE) {
        errors.light = `光色太暗（相對亮度 ${lum.toFixed(2)}，需 ≥ 0.72）。`;
      } else if (weekContrast(lum, weekLuminance(WEEK_LIGHT_BG)) < WEEK_LIGHT_MIN_CONTRAST) {
        errors.light = "光色與深底 #06140f 的對比需 ≥ 7:1。";
      }
    }
    if (day.focus) {
      const m = /^([0-9]{1,3})% ([0-9]{1,3})%$/.exec(String(day.focus));
      if (!m || Number(m[1]) > 100 || Number(m[2]) > 100) {
        errors.focus = "裁切位置需為 0–100 的整數百分比。";
      }
    }
    return errors;
  }

  function weekFieldTargets(els, field) {
    if (!els) return [];
    if (field === "theme") return [els.theme];
    if (field === "alt") return [els.alt];
    if (field === "light") return [els.lightText, els.light];
    if (field === "focus") return [els.focusX, els.focusY];
    return [];
  }

  function weekSetError(day, field, message) {
    const els = weekState.els[day];
    if (!els) return;
    const box = document.getElementById(`week-d${day}-${field}-error`);
    if (box) {
      box.hidden = !message;
      box.textContent = message || "";
    }
    weekFieldTargets(els, field).forEach(el => {
      if (!el) return;
      if (message) el.setAttribute("aria-invalid", "true");
      else el.removeAttribute("aria-invalid");
    });
  }

  function weekValidateField(day, field) {
    const errors = weekValidateDay(day);
    weekSetError(day.day, field, errors[field]);
    return !errors[field];
  }

  function weekValidateAll() {
    const problems = [];
    weekState.draft.days.forEach(day => {
      const errors = weekValidateDay(day);
      ["theme", "alt", "light", "focus"].forEach(field => {
        weekSetError(day.day, field, errors[field]);
        if (errors[field]) problems.push({ day: day.day, field, message: errors[field] });
      });
    });
    return problems;
  }

  // ---- 畫面 ----
  function weekCardTemplate(day) {
    const n = String(day);
    const bookOptions = Object.keys(BOOK_NAMES)
      .map(key => `<option value="${key}">${BOOK_NAMES[key]}</option>`)
      .join("");
    return `
      <summary class="week-summary">
        <span class="dow">${WEEK_NAMES[day] || "第 " + n + " 天"}</span>
        <span class="week-sum-theme" data-week-sum-theme></span>
        <span class="week-dirty" id="week-d${n}-dirty" data-week-dirty hidden>未儲存</span>
      </summary>
      <div class="week-body">
        <div class="week-fields">
          <div class="home-field week-field-wide">
            <label for="week-d${n}-theme">主題（1–40 字）</label>
            <input type="text" id="week-d${n}-theme" data-field="theme" maxlength="40" autocomplete="off" aria-describedby="week-d${n}-theme-error">
            <p class="week-error" id="week-d${n}-theme-error" hidden></p>
          </div>
          <div class="home-field">
            <label for="week-d${n}-book">書卷</label>
            <select id="week-d${n}-book" data-field="book">${bookOptions}</select>
          </div>
          <div class="home-field">
            <label for="week-d${n}-ch">章</label>
            <select id="week-d${n}-ch" data-field="ch"></select>
          </div>
          <div class="home-field">
            <label for="week-d${n}-v">節</label>
            <select id="week-d${n}-v" data-field="v"></select>
          </div>
        </div>

        <p class="home-verse-preview week-verse" id="week-d${n}-verse">載入中…</p>

        <div class="week-preview" id="week-d${n}-preview">
          <img id="week-d${n}-preview-img" alt="" hidden>
          <div class="week-preview-caption">
            <span class="week-preview-ref" id="week-d${n}-preview-ref"></span>
            <span class="week-preview-text" id="week-d${n}-preview-text"></span>
          </div>
        </div>

        <div class="week-fields">
          <div class="home-field week-field-wide">
            <label for="week-d${n}-image-file">上傳封面圖（JPG／PNG／WebP，5 MB 以內）</label>
            <input type="file" id="week-d${n}-image-file" accept="image/jpeg,image/png,image/webp">
          </div>
          <div class="home-field">
            <label for="week-d${n}-image">封面圖</label>
            <select id="week-d${n}-image" data-field="image"></select>
          </div>
          <div class="home-field week-field-wide">
            <label for="week-d${n}-alt">圖片說明（1–120 字）</label>
            <input type="text" id="week-d${n}-alt" data-field="alt" maxlength="120" autocomplete="off" aria-describedby="week-d${n}-alt-error">
            <p class="week-error" id="week-d${n}-alt-error" hidden></p>
          </div>
        </div>

        <div class="week-fields">
          <div class="home-field">
            <label for="week-d${n}-light-text">經文光色（#rrggbb）</label>
            <div class="week-color-row">
              <input type="color" id="week-d${n}-light" aria-label="經文光色色票" value="#ffffff">
              <input type="text" id="week-d${n}-light-text" data-field="light" maxlength="7" autocomplete="off" spellcheck="false" aria-describedby="week-d${n}-light-error">
            </div>
            <p class="week-error" id="week-d${n}-light-error" hidden></p>
          </div>
          <div class="home-field week-field-wide">
            <label for="week-d${n}-focus-x">裁切位置（水平／垂直 %）</label>
            <div class="week-focus-row">
              <input type="range" id="week-d${n}-focus-x" min="0" max="100" step="1" value="35" aria-label="裁切水平位置" aria-describedby="week-d${n}-focus-hint week-d${n}-focus-error">
              <output id="week-d${n}-focus-x-val" for="week-d${n}-focus-x">35%</output>
              <input type="range" id="week-d${n}-focus-y" min="0" max="100" step="1" value="50" aria-label="裁切垂直位置" aria-describedby="week-d${n}-focus-hint week-d${n}-focus-error">
              <output id="week-d${n}-focus-y-val" for="week-d${n}-focus-y">50%</output>
            </div>
            <p class="week-hint" id="week-d${n}-focus-hint">0–100 的整數百分比；沒動過就不寫入設定檔，前台沿用預設裁切（35%／50%）。</p>
            <p class="week-error" id="week-d${n}-focus-error" hidden></p>
          </div>
        </div>
      </div>`;
  }

  function weekFillImageSelect(select, images, current) {
    if (!select) return;
    const list = (images || []).slice();
    if (current && list.indexOf(current) === -1) list.push(current);
    fillSelect(select, list.map(path => ({ value: path, label: path.replace(/^assets\//, "") })), current);
  }

  function weekCardEls(card, day) {
    const byId = suffix => document.getElementById(`week-d${day}-${suffix}`);
    return {
      card,
      summaryTheme: card.querySelector("[data-week-sum-theme]"),
      dirty: card.querySelector("[data-week-dirty]"),
      theme: byId("theme"),
      book: byId("book"),
      ch: byId("ch"),
      v: byId("v"),
      verse: byId("verse"),
      preview: byId("preview"),
      previewImg: byId("preview-img"),
      previewRef: byId("preview-ref"),
      previewText: byId("preview-text"),
      image: byId("image"),
      imageFile: byId("image-file"),
      alt: byId("alt"),
      light: byId("light"),
      lightText: byId("light-text"),
      focusX: byId("focus-x"),
      focusY: byId("focus-y"),
      focusXVal: byId("focus-x-val"),
      focusYVal: byId("focus-y-val")
    };
  }

  function weekRenderDay(day) {
    const els = weekState.els[day.day];
    if (!els) return;
    const data = bookCache[day.book];
    const chapter = data ? chapterOf(data, day.ch) : null;
    const verse = verseOf(chapter, day.v);
    const refText = `${BOOK_NAMES[day.book] || day.book} ${day.ch}:${day.v}`;

    if (els.verse) {
      els.verse.textContent = "";
      if (!verse) {
        els.verse.textContent = "載入中…";
      } else {
        const ref = document.createElement("span");
        ref.className = "verse-ref";
        ref.textContent = refText;
        const text = document.createElement("span");
        text.textContent = verse.text;   // 只顯示，不寫進設定檔
        els.verse.appendChild(ref);
        els.verse.appendChild(text);
      }
    }
    if (els.previewRef) els.previewRef.textContent = refText;
    if (els.previewText) els.previewText.textContent = verse ? verse.text : "（經文載入中…）";
    if (els.previewImg) {
      if (day.image) {
        if (els.previewImg.getAttribute("src") !== assetUrl(day.image)) els.previewImg.src = assetUrl(day.image);
        els.previewImg.alt = day.alt || "";
        els.previewImg.hidden = false;
      } else {
        els.previewImg.hidden = true;
        els.previewImg.removeAttribute("src");
        els.previewImg.alt = "";
      }
      const parts = weekFocusParts(day.focus);
      els.previewImg.style.objectPosition = `${parts.x}% ${parts.y}%`;
    }
    if (els.preview) els.preview.style.color = /^#[0-9a-fA-F]{6}$/.test(day.light) ? day.light : "";
  }

  function weekSetFormLocked(locked) {
    // 儲存／載入／上傳（含解碼）期間把七天表單整個鎖住，避免回應蓋掉等待期間的新輸入
    Object.keys(weekState.els).forEach(day => {
      const els = weekState.els[day];
      ["theme", "book", "ch", "v", "image", "imageFile", "alt", "light", "lightText", "focusX", "focusY"]
        .forEach(key => {
          if (els[key]) els[key].disabled = locked;
        });
    });
  }

  function weekRefresh() {
    const locked = weekLocked();
    weekSetFormLocked(locked);
    if (weekEls.save) weekEls.save.disabled = !weekState.ready || weekState.loadError || locked;
    if (weekEls.reload) weekEls.reload.disabled = locked;
    if (weekEls.toggle) weekEls.toggle.disabled = locked || !weekState.ready || weekState.loadError;
    if (!weekState.draft) return;
    weekState.draft.days.forEach(day => {
      const els = weekState.els[day.day];
      if (!els) return;
      if (els.summaryTheme) els.summaryTheme.textContent = String(day.theme || "").trim() || "（尚未命名）";
      if (els.dirty) els.dirty.hidden = !weekDayDirty(day);
    });
  }

  function weekBuildCards() {
    const host = weekEls.days;
    if (!host) return;
    host.textContent = "";
    weekState.els = {};
    weekState.draft.days.forEach(day => {
      const card = document.createElement("details");
      card.className = "week-card";
      card.dataset.day = String(day.day);
      card.open = day.day === 1;          // 星期一預設展開
      card.innerHTML = weekCardTemplate(day.day);
      host.appendChild(card);

      const els = weekCardEls(card, day.day);
      weekState.els[day.day] = els;
      els.theme.value = day.theme;
      els.book.value = day.book;
      els.alt.value = day.alt;
      els.lightText.value = day.light;
      els.light.value = /^#[0-9a-fA-F]{6}$/.test(day.light) ? day.light : "#ffffff";
      const parts = weekFocusParts(day.focus);
      els.focusX.value = String(parts.x);
      els.focusY.value = String(parts.y);
      els.focusXVal.textContent = parts.x + "%";
      els.focusYVal.textContent = parts.y + "%";
      weekFillImageSelect(els.image, weekState.images, day.image);
      weekBindDay(day, els);
    });
  }

  function weekBindDay(day, els) {
    els.theme.addEventListener("input", () => {
      day.theme = els.theme.value;
      weekValidateField(day, "theme");
      weekRefresh();
    });
    els.book.addEventListener("change", () => {
      day.book = els.book.value;
      weekLoadDayBook(day);
      weekRefresh();
    });
    els.ch.addEventListener("change", () => {
      day.ch = Number(els.ch.value);
      weekFillVerses(day, els);
      weekRenderDay(day);
      weekRefresh();
    });
    els.v.addEventListener("change", () => {
      day.v = Number(els.v.value);
      weekRenderDay(day);
      weekRefresh();
    });
    els.image.addEventListener("change", () => {
      day.image = els.image.value;
      weekRenderDay(day);
      weekRefresh();
    });
    els.imageFile.addEventListener("change", () => {
      const file = els.imageFile.files && els.imageFile.files[0];
      if (file) weekUploadImage(day, file);
    });
    els.alt.addEventListener("input", () => {
      day.alt = els.alt.value;
      weekValidateField(day, "alt");
      weekRenderDay(day);
      weekRefresh();
    });
    els.lightText.addEventListener("input", () => {
      day.light = els.lightText.value.trim();
      if (/^#[0-9a-fA-F]{6}$/.test(day.light)) els.light.value = day.light.toLowerCase();
      weekValidateField(day, "light");
      weekRenderDay(day);
      weekRefresh();
    });
    els.light.addEventListener("input", () => {
      day.light = els.light.value;
      els.lightText.value = day.light;
      weekValidateField(day, "light");
      weekRenderDay(day);
      weekRefresh();
    });
    const onFocusInput = () => {
      day.focus = `${els.focusX.value}% ${els.focusY.value}%`;
      els.focusXVal.textContent = els.focusX.value + "%";
      els.focusYVal.textContent = els.focusY.value + "%";
      weekValidateField(day, "focus");
      weekRenderDay(day);
      weekRefresh();
    };
    els.focusX.addEventListener("input", onFocusInput);
    els.focusY.addEventListener("input", onFocusInput);
  }

  function weekFillVerses(day, els) {
    const data = bookCache[day.book];
    const chapter = data ? chapterOf(data, day.ch) : null;
    const verses = chapter ? (chapter.verses || []) : [];
    const keepV = verses.some(item => Number(item.v) === Number(day.v)) ? day.v : (verses[0] || {}).v;
    fillSelect(els.v, verses.map(item => ({ value: item.v, label: `第 ${item.v} 節` })), keepV);
    day.v = Number(els.v.value);
  }

  // 換書卷／換章時才連動載入；用序號擋掉比較慢的舊回應
  async function weekLoadDayBook(day) {
    const els = weekState.els[day.day];
    if (!els) return;
    const seq = ++day.loadSeq;
    try {
      const data = await loadBook(day.book);
      if (seq !== day.loadSeq || weekState.els[day.day] !== els) return;
      const chapters = Array.isArray(data.chapters) ? data.chapters : [];
      const keepCh = chapters.some(item => Number(item.ch) === Number(day.ch)) ? day.ch : (chapters[0] || {}).ch;
      fillSelect(els.ch, chapters.map(item => ({ value: item.ch, label: `第 ${item.ch} 章` })), keepCh);
      day.ch = Number(els.ch.value);
      weekFillVerses(day, els);
      weekRenderDay(day);
      weekRefresh();
    } catch (err) {
      if (seq !== day.loadSeq) return;
      if (els.verse) els.verse.textContent = `讀不到${BOOK_NAMES[day.book] || day.book}的經文：${err.message}`;
      weekStatus(`無法讀取${BOOK_NAMES[day.book] || day.book}：${err.message}`, "error");
    }
  }

  function weekSyncInputs() {
    weekState.draft.days.forEach(day => {
      const els = weekState.els[day.day];
      if (!els) return;
      const setIfIdle = (el, value) => {
        if (el && document.activeElement !== el && el.value !== value) el.value = value;
      };
      setIfIdle(els.theme, day.theme);
      setIfIdle(els.alt, day.alt);
      setIfIdle(els.lightText, day.light);
      if (els.light && els.light.value !== day.light.toLowerCase()) els.light.value = day.light;
      if (els.book) els.book.value = day.book;
      const parts = weekFocusParts(day.focus);
      if (els.focusX) els.focusX.value = String(parts.x);
      if (els.focusY) els.focusY.value = String(parts.y);
      if (els.focusXVal) els.focusXVal.textContent = parts.x + "%";
      if (els.focusYVal) els.focusYVal.textContent = parts.y + "%";
      weekFillImageSelect(els.image, weekState.images, day.image);
      weekRenderDay(day);
    });
  }

  function weekShowEmpty() {
    if (!weekEls.days) return;
    weekEls.days.textContent = "";
    const p = document.createElement("p");
    p.className = "week-empty";
    p.textContent = "讀不到完整的七天設定（data/home-week.json 缺失或損壞）。修好設定檔後按「重新載入」；在載入成功前不開放儲存，以免舊草稿覆蓋。";
    weekEls.days.appendChild(p);
  }

  function weekApplyPayload(data, rebuild) {
    const seen = new Set();
    const days = (Array.isArray(data && data.days) ? data.days : []).filter(entry => {
      const day = Number(entry && entry.day);
      if (WEEK_DAYS.indexOf(day) === -1 || seen.has(day)) return false;
      seen.add(day);
      return true;
    });
    const complete = days.length === 7;
    if (!complete && weekState.draft) {
      // 載入到的資料不完整：已存在的草稿、基準與畫面一律保留，只把儲存鎖起來
      weekState.ready = false;
      return;
    }
    weekState.ready = complete;
    weekState.base = { enabled: Boolean(data && data.enabled), days: days.map(weekSerializeOne) };
    if (weekEls.toggle) weekEls.toggle.checked = weekState.base.enabled;

    if (!complete) {
      weekState.els = {};
      weekShowEmpty();
      weekRefresh();
      return;
    }

    weekState.draft = {
      enabled: weekState.base.enabled,
      days: days.slice().sort((a, b) => a.day - b.day).map(weekDayFromEntry)
    };
    if (rebuild) weekBuildCards();
    else weekSyncInputs();
    weekState.draft.days.forEach(day => {
      weekLoadDayBook(day);
      weekRenderDay(day);
    });
    weekRefresh();
  }

  async function weekEnsureToken() {
    if (adminToken) return true;
    try {
      const res = await fetch("/api/token");
      if (!res.ok) {
        weekStatus(`無法取得寫入權杖（${await readError(res)}），只能檢視`, "warning");
        return false;
      }
      const data = await res.json();
      adminToken = data.token || "";
      return Boolean(adminToken);
    } catch (err) {
      weekStatus(`無法取得寫入權杖（${err.message}），只能檢視`, "warning");
      return false;
    }
  }

  async function loadHomeWeekSettings() {
    if (!weekEls.section || weekState.loading) return;
    weekState.loading = true;
    weekRefresh();
    weekStatus("載入中…");
    try {
      await weekEnsureToken();
      const res = await fetch("/api/home-week");
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      weekState.images = Array.isArray(data.images) ? data.images : [];
      weekApplyPayload(data, true);
      if (weekState.ready) {
        weekState.loadError = false;
        weekStatus("已載入一週封面設定。", "success");
      } else {
        weekState.loadError = true;
        weekStatus("載入到的七天資料不完整；" + (weekState.draft
          ? "目前草稿保留，修好設定檔並重新載入前不開放儲存。"
          : "修好 data/home-week.json 後請重新載入。"), "error");
      }
    } catch (err) {
      // 載入失敗不清掉草稿，但先鎖住儲存，避免拿舊草稿去覆蓋伺服器上的資料
      weekState.loadError = true;
      if (!weekState.draft) weekShowEmpty();
      weekStatus(`載入一週封面設定失敗：${err.message}` + (weekState.draft ? "（目前草稿保留，尚未儲存）" : ""), "error");
    } finally {
      weekState.loading = false;
      weekRefresh();
    }
  }

  async function weekReadImage(file) {
    return new Promise(resolve => {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        const width = img.naturalWidth;
        const height = img.naturalHeight;
        URL.revokeObjectURL(url);
        resolve(width && height ? { width, height } : null);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        resolve(null);
      };
      img.src = url;
    });
  }

  async function weekUploadImage(day, file) {
    if (!file || weekLocked()) return;
    const els = weekState.els[day.day];
    const resetInput = () => { if (els && els.imageFile) els.imageFile.value = ""; };
    if (!/\.(jpe?g|png|webp)$/i.test(file.name)) {
      weekStatus("只接受 JPG、PNG、WebP 圖檔。", "error");
      resetInput();
      return;
    }
    if (file.size > IMAGE_MAX_BYTES) {
      weekStatus(`檔案太大（${(file.size / 1024 / 1024).toFixed(1)} MB），封面上限 5 MB。`, "error");
      resetInput();
      return;
    }
    weekState.uploading += 1;
    weekRefresh();                     // 解碼前就先鎖住表單，避免重複上傳或解碼期間儲存
    weekStatus(`正在檢查 ${file.name}…`);
    try {
      const info = await weekReadImage(file);
      if (!info) {
        weekStatus("這個檔案無法解碼成圖片，請換一張 JPG、PNG 或 WebP。", "error");
        return;
      }
      const tips = [];
      const ratio = info.width / info.height;
      if (Math.abs(ratio - 16 / 9) > 0.08) tips.push(`目前比例約 ${ratio.toFixed(2)}:1，封面建議 16:9`);
      if (info.width < 1600 || info.height < 900) tips.push(`目前 ${info.width}×${info.height}，建議至少 1600×900`);
      if (file.size > WEEK_IMAGE_TIP_BYTES) tips.push(`檔案 ${Math.round(file.size / 1024)} KiB，建議 600 KiB 以內`);

      weekStatus(`正在上傳 ${file.name}…`);
      const res = await fetch(`/api/upload?kind=image&name=${encodeURIComponent(file.name)}`, {
        method: "POST",
        headers: writeHeaders({ "Content-Type": "application/octet-stream" }),
        body: file
      });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      const path = data.path;
      day.image = path;
      if (els) {
        addOption(els.image, path);
        els.image.value = path;
      }
      weekRenderDay(day);
      weekRefresh();
      const note = tips.length ? "建議：" + tips.join("；") + "。" : "";
      weekStatus("已上傳封面圖（尚未儲存）。" + note, tips.length ? "warning" : "success");
    } catch (err) {
      weekStatus(`上傳失敗：${err.message}`, "error");
    } finally {
      weekState.uploading -= 1;
      resetInput();
      weekRefresh();
    }
  }

  async function saveHomeWeek() {
    if (!weekState.ready || weekState.loadError || weekLocked()) return;
    const problems = weekValidateAll();
    if (problems.length) {
      const first = problems[0];
      const els = weekState.els[first.day];
      if (els && els.card) els.card.open = true;
      const target = weekFieldTargets(els, first.field)[0];
      if (target) target.focus();
      weekStatus(`有欄位需要修正，尚未儲存：${WEEK_NAMES[first.day] || "第 " + first.day + " 天"}${first.message}`, "error");
      return;
    }
    weekState.saving = true;
    weekRefresh();
    weekStatus("儲存中…");
    try {
      const res = await fetch("/api/home-week", {
        method: "POST",
        headers: writeHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(weekPayload())
      });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      weekApplyPayload({ enabled: data.enabled, days: data.days }, false);
      if (weekState.ready) {
        weekStatus("已儲存整週封面。要更新線上網站，請記得執行發佈。", "success");
      } else {
        weekState.loadError = true;
        weekStatus("伺服器回覆的七天資料不完整，已保留草稿但先鎖住儲存；請重新載入確認。", "error");
      }
    } catch (err) {
      weekStatus(`儲存失敗：${err.message}（輸入內容都保留，可修正後再試）`, "error");
    } finally {
      weekState.saving = false;
      weekRefresh();
    }
  }

  // 6. 收藏卡圖片（抽經文卡四個主題，每月更換）
  const ART_THEMES = [
    { id: "work", title: "天父賜福你的工作" },
    { id: "peace", title: "天父賜你平安" },
    { id: "rest", title: "天父給你安息" },
    { id: "faith", title: "在神凡事都能" }
  ];

  const artEls = {
    section: document.getElementById("blessing-art-settings"),
    status: document.getElementById("art-status")
  };
  const artState = {};

  ART_THEMES.forEach(theme => {
    artEls[theme.id] = {
      file: document.getElementById(`art-${theme.id}-file`),
      alt: document.getElementById(`art-${theme.id}-alt`),
      edition: document.getElementById(`art-${theme.id}-edition`),
      preview: document.getElementById(`art-${theme.id}-preview`),
      save: document.getElementById(`art-${theme.id}-save`),
      clear: document.getElementById(`art-${theme.id}-clear`)
    };
    artState[theme.id] = { image: "", alt: "", edition: "" };
  });

  // 單張卡片（37 張）：沒有自己圖片的卡沿用所屬主題圖
  const artCardEls = {};
  const artCardState = {};

  [...document.querySelectorAll("#blessing-art-cards [data-art-card]")].forEach(node => {
    const cardId = node.dataset.artCard;
    if (!cardId || artCardEls[cardId]) return;
    const base = `art-card-${cardId}`;
    artCardEls[cardId] = {
      file: document.getElementById(`${base}-file`),
      alt: document.getElementById(`${base}-alt`),
      edition: document.getElementById(`${base}-edition`),
      preview: document.getElementById(`${base}-preview`),
      save: document.getElementById(`${base}-save`),
      clear: document.getElementById(`${base}-clear`)
    };
    // 卡片 ID 的前綴就是主題代號（work-01 → work）；GET 的 cards 列表載入後會再確認
    artCardState[cardId] = { image: "", alt: "", edition: "", theme: String(cardId).split("-")[0] };
  });

  function artStatus(text, kind) {
    const el = artEls.status;
    if (!el) return;
    el.textContent = text;
    el.className = "home-status" + (kind ? " is-" + kind : "");
  }

  function artThemeById(themeId) {
    return ART_THEMES.find(theme => theme.id === themeId) || null;
  }

  function renderArtThemeInfo(info) {
    if (!info || typeof info.id !== "string") return;
    const count = Number(info.count) || 0;
    const countEl = document.querySelector(`[data-art-count="${info.id}"]`);
    if (countEl) countEl.textContent = `${count} 張`;
    const refsCountEl = document.querySelector(`[data-art-refs-count="${info.id}"]`);
    if (refsCountEl) refsCountEl.textContent = `（${count} 張）`;

    const list = document.querySelector(`[data-art-refs="${info.id}"]`);
    if (!list) return;
    list.replaceChildren();
    (Array.isArray(info.refs) ? info.refs : []).forEach(ref => {
      if (!ref || typeof ref !== "object") return;
      const li = document.createElement("li");
      const book = BOOK_NAMES[ref.book] || String(ref.book || "");
      li.textContent = `${book} ${ref.ch}:${ref.v}`;
      list.appendChild(li);
    });
  }

  function updateArtPreview(themeId, path) {
    const els = artEls[themeId];
    if (!els || !els.preview) return;
    if (!path) {
      els.preview.hidden = true;
      els.preview.removeAttribute("src");
      return;
    }
    els.preview.src = assetUrl(path);
    els.preview.hidden = false;
  }

  function artCardTheme(cardId) {
    return artThemeById(artCardState[cardId] ? artCardState[cardId].theme : "");
  }

  function artCardAltDefault(cardId) {
    const theme = artCardTheme(cardId);
    return `${theme ? theme.title : "收藏卡"} ${cardId} 收藏卡`;
  }

  // 卡片自己的圖優先，沒有就顯示所屬主題圖（前台也是這個回退順序）
  function updateArtCardPreview(cardId) {
    const els = artCardEls[cardId];
    if (!els || !els.preview) return;
    const state = artCardState[cardId];
    const theme = artCardTheme(cardId);
    const path = (state && state.image) || (theme ? artState[theme.id].image : "");
    if (!path) {
      els.preview.hidden = true;
      els.preview.removeAttribute("src");
      return;
    }
    els.preview.src = assetUrl(path);
    els.preview.hidden = false;
  }

  function refreshCardPreviews(themeId) {
    Object.keys(artCardEls).forEach(cardId => {
      if (!themeId || artCardState[cardId].theme === themeId) updateArtCardPreview(cardId);
    });
  }

  // GET 的 cards 只含 id／主題／出處（不含經文正文），用來確認每張卡的主題歸屬
  function applyArtCardList(cards) {
    (Array.isArray(cards) ? cards : []).forEach(item => {
      if (!item || typeof item !== "object" || !artCardState[item.id]) return;
      if (typeof item.theme === "string" && artThemeById(item.theme)) artCardState[item.id].theme = item.theme;
    });
    refreshCardPreviews();
  }

  function applyArtConfig(config) {
    const safe = config && typeof config === "object" ? config : {};
    ART_THEMES.forEach(theme => {
      const ent = safe[theme.id] && typeof safe[theme.id] === "object" ? safe[theme.id] : {};
      const state = artState[theme.id];
      state.image = typeof ent.image === "string" ? ent.image : "";
      state.alt = typeof ent.alt === "string" ? ent.alt : "";
      state.edition = typeof ent.edition === "string" ? ent.edition : "";
      const els = artEls[theme.id];
      if (els.alt) els.alt.value = state.alt;
      if (els.edition) els.edition.value = state.edition;
      updateArtPreview(theme.id, state.image);
    });
    const cards = safe.cards && typeof safe.cards === "object" ? safe.cards : {};
    Object.keys(artCardEls).forEach(cardId => {
      const ent = cards[cardId] && typeof cards[cardId] === "object" ? cards[cardId] : {};
      const state = artCardState[cardId];
      state.image = typeof ent.image === "string" ? ent.image : "";
      state.alt = typeof ent.alt === "string" ? ent.alt : "";
      state.edition = typeof ent.edition === "string" ? ent.edition : "";
      const els = artCardEls[cardId];
      if (els.alt) els.alt.value = state.alt;
      if (els.edition) els.edition.value = state.edition;
      updateArtCardPreview(cardId);
    });
  }

  // 整份設定：四個主題各自的最新值；沒有圖的主題不放入
  function currentArtConfig(excludeThemeId) {
    const config = {};
    ART_THEMES.forEach(theme => {
      if (theme.id === excludeThemeId) return;
      const image = artState[theme.id].image;
      if (!image) return;
      const els = artEls[theme.id];
      let alt = (els.alt ? els.alt.value : artState[theme.id].alt).trim();
      if (!alt) alt = `${theme.title}收藏卡`;
      if (alt.length > 120) alt = alt.slice(0, 120);
      const edition = (els.edition ? els.edition.value : artState[theme.id].edition).trim().slice(0, 20);
      config[theme.id] = { image, alt, edition };
    });
    return config;
  }

  // 單張卡片：只收有自己的圖片的卡；沒設定的卡不寫進設定，前台自動沿用主題圖
  function currentArtCards(excludeCardId) {
    const cards = {};
    Object.keys(artCardEls).forEach(cardId => {
      if (cardId === excludeCardId) return;
      const image = artCardState[cardId].image;
      if (!image) return;
      const els = artCardEls[cardId];
      let alt = (els.alt ? els.alt.value : artCardState[cardId].alt).trim();
      if (!alt) alt = artCardAltDefault(cardId);
      if (alt.length > 120) alt = alt.slice(0, 120);
      const edition = (els.edition ? els.edition.value : artCardState[cardId].edition).trim().slice(0, 20);
      cards[cardId] = { image, alt, edition };
    });
    return cards;
  }

  // 每一次 POST 都送完整物件（四個主題 + 單張卡），不會蓋掉沒動到的設定
  function currentArtPayload(excludeThemeId, excludeCardId) {
    const config = currentArtConfig(excludeThemeId);
    const cards = currentArtCards(excludeCardId);
    if (Object.keys(cards).length) config.cards = cards;
    return config;
  }

  function defaultArtEdition() {
    const now = new Date();
    return `${now.getFullYear()} 年 ${now.getMonth() + 1} 月版`;
  }

  function ensureArtAlt(theme) {
    const els = artEls[theme.id];
    if (els.alt && !els.alt.value.trim()) els.alt.value = `${theme.title}收藏卡`;
  }

  function ensureArtCardAlt(cardId) {
    const els = artCardEls[cardId];
    if (els.alt && !els.alt.value.trim()) els.alt.value = artCardAltDefault(cardId);
  }

  async function uploadArtFile(themeId, file) {
    const theme = artThemeById(themeId);
    const els = artEls[themeId];
    if (!theme || !els || !file) return;
    const path = await uploadFile("image", file, {
      select: null,
      updatePreview: newPath => updateArtPreview(themeId, newPath),
      status: artStatus,
      fileInput: els.file,
      uploadedMessage: "已上傳，尚未儲存"
    });
    if (!path) return;
    artState[themeId].image = path;
    ensureArtAlt(theme);
    if (els.edition && !els.edition.value.trim()) els.edition.value = defaultArtEdition();
    artStatus("已上傳，尚未儲存", "success");
  }

  async function saveArtTheme(themeId) {
    const theme = artThemeById(themeId);
    const els = artEls[themeId];
    if (!theme || !els) return;
    if (!artState[themeId].image) {
      artStatus("請先上傳圖片，再儲存。", "warning");
      return;
    }
    ensureArtAlt(theme);
    const btn = els.save;
    if (btn) btn.disabled = true;
    artStatus("儲存中…");
    try {
      const res = await fetch("/api/blessing-art", {
        method: "POST",
        headers: writeHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(currentArtPayload())
      });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      applyArtConfig(data.config || currentArtPayload());
      artStatus("已儲存。記得執行發佈。", "success");
    } catch (err) {
      artStatus(`儲存失敗：${err.message}`, "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function clearArtTheme(themeId) {
    const theme = artThemeById(themeId);
    const els = artEls[themeId];
    if (!theme || !els) return;
    const btn = els.clear;
    if (btn) btn.disabled = true;
    artStatus("清除中…");
    try {
      const res = await fetch("/api/blessing-art", {
        method: "POST",
        headers: writeHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(currentArtPayload(themeId))
      });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      artState[themeId].image = "";
      if (els.alt) els.alt.value = "";
      if (els.edition) els.edition.value = "";
      updateArtPreview(themeId, "");
      if (data.config) applyArtConfig(data.config);
      artStatus("已清除。記得執行發佈。", "success");
    } catch (err) {
      artStatus(`清除失敗：${err.message}`, "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function uploadArtCardFile(cardId, file) {
    const els = artCardEls[cardId];
    const state = artCardState[cardId];
    if (!els || !state || !file) return;
    const path = await uploadFile("image", file, {
      select: null,
      updatePreview: newPath => {
        state.image = newPath;
        updateArtCardPreview(cardId);
      },
      status: artStatus,
      fileInput: els.file,
      uploadedMessage: "已上傳，尚未儲存"
    });
    if (!path) return;
    ensureArtCardAlt(cardId);
    if (els.edition && !els.edition.value.trim()) els.edition.value = defaultArtEdition();
    artStatus(`${cardId} 已上傳，尚未儲存`, "success");
  }

  async function saveArtCard(cardId) {
    const els = artCardEls[cardId];
    if (!els || !artCardState[cardId]) return;
    if (!artCardState[cardId].image) {
      artStatus(`${cardId}：請先上傳圖片，再儲存。`, "warning");
      return;
    }
    ensureArtCardAlt(cardId);
    const btn = els.save;
    if (btn) btn.disabled = true;
    artStatus(`${cardId} 儲存中…`);
    try {
      const res = await fetch("/api/blessing-art", {
        method: "POST",
        headers: writeHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(currentArtPayload())
      });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      applyArtConfig(data.config || currentArtPayload());
      artStatus(`${cardId} 已儲存。記得執行發佈。`, "success");
    } catch (err) {
      artStatus(`${cardId} 儲存失敗：${err.message}`, "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  // 清除一張卡＝送出刪掉該 card key 的完整設定；其他卡全空時連 cards 一起不帶
  async function clearArtCard(cardId) {
    const els = artCardEls[cardId];
    if (!els || !artCardState[cardId]) return;
    const btn = els.clear;
    if (btn) btn.disabled = true;
    artStatus(`${cardId} 清除中…`);
    try {
      const res = await fetch("/api/blessing-art", {
        method: "POST",
        headers: writeHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(currentArtPayload(null, cardId))
      });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      artCardState[cardId].image = "";
      if (els.alt) els.alt.value = "";
      if (els.edition) els.edition.value = "";
      updateArtCardPreview(cardId);
      if (data.config) applyArtConfig(data.config);
      artStatus(`${cardId} 已清除，改回主題圖。記得執行發佈。`, "success");
    } catch (err) {
      artStatus(`${cardId} 清除失敗：${err.message}`, "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function resetAllArt() {
    if (!window.confirm("確定要清除全部主題與單張卡片的收藏卡圖片嗎？")) return;
    const btn = document.querySelector("[data-art-reset]");
    if (btn) btn.disabled = true;
    artStatus("清除中…");
    try {
      const res = await fetch("/api/blessing-art/reset", {
        method: "POST",
        headers: writeHeaders({ "Content-Type": "application/json" }),
        body: "{}"
      });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      applyArtConfig(data.config || {});
      artStatus("已清除全部收藏卡圖片。記得執行發佈。", "success");
    } catch (err) {
      artStatus(`清除失敗：${err.message}`, "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function loadBlessingArtSettings() {
    if (!artEls.section) return;
    try {
      if (!adminToken) {
        const tokenRes = await fetch("/api/token");
        if (tokenRes.ok) {
          const tokenData = await tokenRes.json();
          adminToken = tokenData.token || "";
        } else {
          artStatus(`無法取得寫入權杖（${await readError(tokenRes)}），只能檢視`, "warning");
        }
      }

      const res = await fetch("/api/blessing-art");
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      const infos = Array.isArray(data.themes) ? data.themes : [];
      ART_THEMES.forEach(theme => {
        const info = infos.find(item => item && item.id === theme.id);
        renderArtThemeInfo(info || { id: theme.id, count: 0, refs: [] });
      });
      applyArtCardList(data.cards);
      applyArtConfig(data.config || {});
      artStatus("已載入目前設定。", "success");
    } catch (err) {
      artStatus(`載入收藏卡圖片設定失敗：${err.message}`, "error");
    }
  }

  if (homeEls.section) {
    if (homeEls.book) {
      homeEls.book.addEventListener("change", () => { rebuildChapters(); });
    }
    if (homeEls.ch) {
      homeEls.ch.addEventListener("change", () => { rebuildVerses(); });
    }
    if (homeEls.v) {
      homeEls.v.addEventListener("change", renderVersePreview);
    }
    if (homeEls.imageSelect) {
      homeEls.imageSelect.addEventListener("change", () => updateImagePreview(homeEls.imageSelect.value));
    }
    if (homeEls.musicSelect) {
      homeEls.musicSelect.addEventListener("change", () => updateMusicPreview(homeEls.musicSelect.value));
    }
    if (homeEls.imageFile) {
      homeEls.imageFile.addEventListener("change", () => uploadFile("image", homeEls.imageFile.files[0]));
    }
    if (homeEls.musicFile) {
      homeEls.musicFile.addEventListener("change", () => uploadFile("music", homeEls.musicFile.files[0]));
    }
    if (homeEls.save) homeEls.save.addEventListener("click", saveHomeSettings);
    if (homeEls.reset) homeEls.reset.addEventListener("click", resetHomeSettings);
    if (homeEls.open) homeEls.open.addEventListener("click", openHomePreview);

    loadHomeSettings();
  }

  if (zoneEls.section) {
    if (zoneEls.select) {
      // 換共用曲時，留空（沿用共用曲）的區塊試聽跟著換
      zoneEls.select.addEventListener("change", () => {
        updateZoneMusicPreview(zoneEls.select.value);
        ZONE_AREAS.forEach(area => updateZoneAreaPreview(area.id));
      });
    }
    ZONE_AREAS.forEach(area => {
      const els = zoneEls.areas[area.id];
      if (els.select) {
        els.select.addEventListener("change", () => updateZoneAreaPreview(area.id));
      }
    });
    if (zoneEls.file) {
      zoneEls.file.addEventListener("change", async () => {
        const path = await uploadFile("music", zoneEls.file.files[0], {
          select: zoneEls.select,
          updatePreview: updateZoneMusicPreview,
          status: zoneStatus,
          fileInput: zoneEls.file,
          uploadedMessage: "已上傳，尚未儲存"
        });
        if (path) {
          addZoneAreaOption(path);
          ZONE_AREAS.forEach(area => updateZoneAreaPreview(area.id));
        }
      });
    }
    if (zoneEls.save) zoneEls.save.addEventListener("click", saveZoneMusicSettings);
    if (zoneEls.reset) zoneEls.reset.addEventListener("click", resetZoneMusicSettings);

    loadZoneMusicSettings();
  }

  if (weekEls.section) {
    if (weekEls.toggle) {
      // 開關也只改草稿，等「儲存整週」才寫回
      weekEls.toggle.addEventListener("change", () => {
        if (!weekState.draft || weekLocked()) return;
        weekState.draft.enabled = weekEls.toggle.checked;
        weekRefresh();
      });
    }
    if (weekEls.save) weekEls.save.addEventListener("click", saveHomeWeek);
    if (weekEls.reload) {
      weekEls.reload.addEventListener("click", () => {
        if (weekDirty() && !window.confirm("有尚未儲存的變更，重新載入會放棄這些修改。要繼續嗎？")) return;
        loadHomeWeekSettings();
      });
    }
    window.addEventListener("beforeunload", event => {
      if (weekDirty() || weekState.uploading > 0) {
        event.preventDefault();
        event.returnValue = "";
      }
    });
    loadHomeWeekSettings();
  }

  if (artEls.section) {
    ART_THEMES.forEach(theme => {
      const els = artEls[theme.id];
      if (!els) return;
      if (els.file) {
        els.file.addEventListener("change", () => {
          const file = els.file.files && els.file.files[0];
          if (file) uploadArtFile(theme.id, file);
        });
      }
      if (els.save) els.save.addEventListener("click", () => saveArtTheme(theme.id));
      if (els.clear) els.clear.addEventListener("click", () => clearArtTheme(theme.id));
    });

    Object.keys(artCardEls).forEach(cardId => {
      const els = artCardEls[cardId];
      if (els.file) {
        els.file.addEventListener("change", () => {
          const file = els.file.files && els.file.files[0];
          if (file) uploadArtCardFile(cardId, file);
        });
      }
      if (els.save) els.save.addEventListener("click", () => saveArtCard(cardId));
      if (els.clear) els.clear.addEventListener("click", () => clearArtCard(cardId));
    });

    const artResetBtn = document.querySelector("[data-art-reset]");
    if (artResetBtn) artResetBtn.addEventListener("click", resetAllArt);

    loadBlessingArtSettings();
  }

  // 5.6 每日禱讀上架狀態（唯讀）：GET /api/devotional-status，只在載入與手動重新整理時查詢
  const DEV_STATUS_TIMEOUT_MS = 12000;
  const DEV_STATUS_UNKNOWN = "未知";

  const devStatusEls = {
    section: document.getElementById("devotional-status"),
    refresh: document.getElementById("devotional-status-refresh"),
    live: document.getElementById("devotional-status-live"),
    release: document.getElementById("dev-status-release"),
    observed: document.getElementById("devotional-status-observed"),
    warnings: document.getElementById("dev-status-warnings"),
    warningList: document.getElementById("dev-status-warning-list"),
    public: {
      state: document.getElementById("dev-status-public-state"),
      count: document.getElementById("dev-status-public-count"),
      latest: document.getElementById("dev-status-public-latest"),
      detail: document.getElementById("dev-status-public-detail")
    },
    local: {
      state: document.getElementById("dev-status-local-state"),
      count: document.getElementById("dev-status-local-count"),
      latest: document.getElementById("dev-status-local-latest"),
      detail: document.getElementById("dev-status-local-detail")
    },
    schedule: {
      state: document.getElementById("dev-status-schedule-state"),
      enabled: document.getElementById("dev-status-schedule-enabled"),
      active: document.getElementById("dev-status-schedule-active"),
      next: document.getElementById("dev-status-schedule-next"),
      cutoff: document.getElementById("dev-status-schedule-cutoff"),
      detail: document.getElementById("dev-status-schedule-detail")
    },
    last: {
      state: document.getElementById("dev-status-last-state"),
      started: document.getElementById("dev-status-last-started"),
      finished: document.getElementById("dev-status-last-finished"),
      exit: document.getElementById("dev-status-last-exit"),
      detail: document.getElementById("dev-status-last-detail")
    }
  };

  let devStatusBusy = false;
  let devStatusSeq = 0;

  function devStatusSet(el, text, kind) {
    if (!el) return;
    el.textContent = text;
    if (kind !== undefined) el.className = kind;
  }

  function devStatusValue(value) {
    if (value === null || value === undefined) return DEV_STATUS_UNKNOWN;
    const text = String(value).trim();
    return text || DEV_STATUS_UNKNOWN;
  }

  function devStatusSourceState(state) {
    const map = {
      ok: { text: "正常", cls: "dev-status-value is-ok" },
      unavailable: { text: "無法取得", cls: "dev-status-value is-warning" },
      invalid: { text: "資料異常", cls: "dev-status-value is-error" }
    };
    return map[state] || { text: DEV_STATUS_UNKNOWN, cls: "dev-status-value is-unknown" };
  }

  function devStatusSourceCount(source) {
    if (!source || source.state !== "ok") return DEV_STATUS_UNKNOWN;
    if (typeof source.count !== "number" || !Number.isFinite(source.count)) return DEV_STATUS_UNKNOWN;
    return `${source.count} 篇`;
  }

  function devStatusSourceLatest(source) {
    if (!source || source.state !== "ok") return DEV_STATUS_UNKNOWN;
    if (source.latest_date) return String(source.latest_date);
    return source.count === 0 ? "尚無資料" : DEV_STATUS_UNKNOWN;
  }

  function devStatusSourceDetail(source) {
    if (!source || typeof source !== "object") return "";
    const parts = [];
    if (source.source) parts.push(`來源：${String(source.source)}`);
    if (source.state !== "ok" && source.error) parts.push(`原因：${String(source.error)}`);
    return parts.join("；");
  }

  function devStatusEnabled(value) {
    if (value === true) return "已啟用";
    if (value === false) return "未啟用";
    return DEV_STATUS_UNKNOWN;
  }

  function devStatusActive(value) {
    if (value === null || value === undefined || value === "") return DEV_STATUS_UNKNOWN;
    const text = String(value);
    const map = {
      active: "active（運作中）",
      inactive: "inactive（未運作）",
      failed: "failed（失敗）",
      activating: "activating（啟動中）",
      deactivating: "deactivating（停止中）"
    };
    return map[text] || text;
  }

  function devStatusNext(schedule) {
    if (!schedule || schedule.state !== "ok") return DEV_STATUS_UNKNOWN;
    if (schedule.next_run) return String(schedule.next_run);
    if (schedule.expired === true) return "已無下一次（已截止）";
    return "尚無資料";
  }

  function devStatusScheduleDetail(schedule) {
    if (!schedule || typeof schedule !== "object") return "";
    const parts = [];
    if (schedule.calendar) parts.push(`排程規則：${String(schedule.calendar)}`);
    if (schedule.state !== "ok" && schedule.error) parts.push(`原因：${String(schedule.error)}`);
    return parts.join("；");
  }

  function devStatusLastState(state) {
    const map = {
      success: { text: "成功", cls: "dev-status-value is-ok" },
      failed: { text: "失敗", cls: "dev-status-value is-error" },
      never: { text: "尚未執行", cls: "dev-status-value is-neutral" },
      skipped: { text: "已跳過", cls: "dev-status-value is-neutral" },
      unknown: { text: DEV_STATUS_UNKNOWN, cls: "dev-status-value is-unknown" }
    };
    return map[state] || map.unknown;
  }

  function devStatusLastDetail(last) {
    if (!last || typeof last !== "object") return "";
    if (last.state !== "success" && last.error) return `原因：${String(last.error)}`;
    return "";
  }

  function devStatusReleaseMeta(state) {
    const map = {
      scheduled: { text: "已排程", cls: "dev-status-badge is-info" },
      cutoff: { text: "已依設定截止", cls: "dev-status-badge is-neutral" },
      attention: { text: "需要留意", cls: "dev-status-badge is-warning" },
      unknown: { text: "狀態未知", cls: "dev-status-badge is-unknown" }
    };
    return map[state] || map.unknown;
  }

  function devStatusTime(value, timezone) {
    if (value === null || value === undefined || value === "") return DEV_STATUS_UNKNOWN;
    const text = String(value);
    const date = new Date(text);
    if (Number.isNaN(date.getTime())) return text;
    const zone = (typeof timezone === "string" && timezone.trim()) ? timezone.trim() : "Asia/Taipei";
    try {
      return new Intl.DateTimeFormat("zh-TW", {
        timeZone: zone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hourCycle: "h23"
      }).format(date);
    } catch (err) {
      return text;
    }
  }

  function devStatusRenderWarnings(warnings) {
    const list = devStatusEls.warningList;
    if (!list) return;
    list.textContent = "";
    const items = Array.isArray(warnings)
      ? warnings.filter(item => typeof item === "string" && item.trim())
      : [];
    if (!items.length) {
      if (devStatusEls.warnings) devStatusEls.warnings.hidden = true;
      return;
    }
    items.forEach(item => {
      const li = document.createElement("li");
      li.textContent = item;
      list.appendChild(li);
    });
    if (devStatusEls.warnings) devStatusEls.warnings.hidden = false;
  }

  function devStatusRender(data) {
    const pub = (data.public && typeof data.public === "object") ? data.public : {};
    const local = (data.local && typeof data.local === "object") ? data.local : {};
    const schedule = (data.schedule && typeof data.schedule === "object") ? data.schedule : {};
    const last = (data.last_run && typeof data.last_run === "object") ? data.last_run : {};

    const pubState = devStatusSourceState(pub.state);
    devStatusSet(devStatusEls.public.state, pubState.text, pubState.cls);
    devStatusSet(devStatusEls.public.count, devStatusSourceCount(pub));
    devStatusSet(devStatusEls.public.latest, devStatusSourceLatest(pub));
    devStatusSet(devStatusEls.public.detail, devStatusSourceDetail(pub));

    const localState = devStatusSourceState(local.state);
    devStatusSet(devStatusEls.local.state, localState.text, localState.cls);
    devStatusSet(devStatusEls.local.count, devStatusSourceCount(local));
    devStatusSet(devStatusEls.local.latest, devStatusSourceLatest(local));
    devStatusSet(devStatusEls.local.detail, devStatusSourceDetail(local));

    const scheduleState = devStatusSourceState(schedule.state);
    devStatusSet(devStatusEls.schedule.state, scheduleState.text, scheduleState.cls);
    devStatusSet(devStatusEls.schedule.enabled, devStatusEnabled(schedule.enabled));
    devStatusSet(devStatusEls.schedule.active, devStatusActive(schedule.active));
    devStatusSet(devStatusEls.schedule.next, devStatusNext(schedule));
    devStatusSet(devStatusEls.schedule.cutoff, devStatusValue(schedule.cutoff_date));
    devStatusSet(devStatusEls.schedule.detail, devStatusScheduleDetail(schedule));

    const lastState = devStatusLastState(last.state);
    devStatusSet(devStatusEls.last.state, lastState.text, lastState.cls);
    devStatusSet(devStatusEls.last.started, devStatusValue(last.started_at));
    devStatusSet(devStatusEls.last.finished, devStatusValue(last.finished_at));
    devStatusSet(devStatusEls.last.exit,
      (last.exit_code === null || last.exit_code === undefined) ? DEV_STATUS_UNKNOWN : String(last.exit_code));
    devStatusSet(devStatusEls.last.detail, devStatusLastDetail(last));

    const zone = devStatusValue(data.timezone);
    const observed = devStatusTime(data.observed_at, data.timezone);
    if (devStatusEls.observed) {
      devStatusEls.observed.textContent = `觀測時間：${observed}（時區：${zone}）`;
    }

    const release = devStatusReleaseMeta(data.release_state);
    if (devStatusEls.release) {
      devStatusEls.release.textContent = release.text;
      devStatusEls.release.className = release.cls;
    }

    const badSource = [pub, local, schedule].some(src => src.state !== "ok");
    let liveKind = "dev-status-live";
    if (data.release_state === "cutoff") liveKind += " is-neutral";
    else if (data.release_state === "attention") liveKind += " is-warning";
    else if (badSource) liveKind += " is-warning";
    else if (data.release_state === "scheduled") liveKind += " is-ok";
    else liveKind += " is-unknown";
    if (devStatusEls.live) devStatusEls.live.className = liveKind;

    devStatusRenderWarnings(data.warnings);
    if (devStatusEls.section) devStatusEls.section.setAttribute("aria-busy", "false");
  }

  function devStatusRenderLoading() {
    if (devStatusEls.release) {
      devStatusEls.release.textContent = "載入中";
      devStatusEls.release.className = "dev-status-badge is-loading";
    }
    if (devStatusEls.observed) devStatusEls.observed.textContent = "正在取得上架狀態…";
    if (devStatusEls.live) devStatusEls.live.className = "dev-status-live is-loading";
    if (devStatusEls.section) devStatusEls.section.setAttribute("aria-busy", "true");
  }

  function devStatusRenderFailure(message) {
    const unknownState = { text: DEV_STATUS_UNKNOWN, cls: "dev-status-value is-unknown" };
    ["public", "local"].forEach(key => {
      const els = devStatusEls[key];
      devStatusSet(els.state, unknownState.text, unknownState.cls);
      devStatusSet(els.count, DEV_STATUS_UNKNOWN);
      devStatusSet(els.latest, DEV_STATUS_UNKNOWN);
      devStatusSet(els.detail, "");
    });

    devStatusSet(devStatusEls.schedule.state, unknownState.text, unknownState.cls);
    devStatusSet(devStatusEls.schedule.enabled, DEV_STATUS_UNKNOWN);
    devStatusSet(devStatusEls.schedule.active, DEV_STATUS_UNKNOWN);
    devStatusSet(devStatusEls.schedule.next, DEV_STATUS_UNKNOWN);
    devStatusSet(devStatusEls.schedule.cutoff, DEV_STATUS_UNKNOWN);
    devStatusSet(devStatusEls.schedule.detail, "");

    const lastState = devStatusLastState("unknown");
    devStatusSet(devStatusEls.last.state, lastState.text, lastState.cls);
    devStatusSet(devStatusEls.last.started, DEV_STATUS_UNKNOWN);
    devStatusSet(devStatusEls.last.finished, DEV_STATUS_UNKNOWN);
    devStatusSet(devStatusEls.last.exit, DEV_STATUS_UNKNOWN);
    devStatusSet(devStatusEls.last.detail, "");

    if (devStatusEls.release) {
      devStatusEls.release.textContent = "資料未更新";
      devStatusEls.release.className = "dev-status-badge is-error";
    }
    if (devStatusEls.observed) devStatusEls.observed.textContent = message;
    if (devStatusEls.live) devStatusEls.live.className = "dev-status-live is-error";
    devStatusRenderWarnings([]);
    if (devStatusEls.section) devStatusEls.section.setAttribute("aria-busy", "false");
  }

  async function loadDevotionalStatus() {
    if (devStatusBusy) return;
    devStatusBusy = true;
    const seq = ++devStatusSeq;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), DEV_STATUS_TIMEOUT_MS);

    if (devStatusEls.refresh) devStatusEls.refresh.disabled = true;
    devStatusRenderLoading();

    try {
      const res = await fetch("/api/devotional-status", {
        method: "GET",
        headers: { "Accept": "application/json" },
        cache: "no-store",
        signal: controller.signal
      });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      if (seq !== devStatusSeq) return;
      if (!data || typeof data !== "object" || Array.isArray(data)) {
        throw new Error("後台回應格式錯誤");
      }
      devStatusRender(data);
    } catch (err) {
      if (seq !== devStatusSeq) return;
      let message;
      if (err && err.name === "AbortError") {
        message = "請求逾時（12 秒），資料未更新。";
      } else if (err instanceof TypeError) {
        message = "無法連線後台，資料未更新。";
      } else {
        message = `資料未更新：${err && err.message ? err.message : "未知錯誤"}`;
      }
      devStatusRenderFailure(message);
    } finally {
      clearTimeout(timeout);
      if (seq === devStatusSeq) {
        devStatusBusy = false;
        if (devStatusEls.refresh) devStatusEls.refresh.disabled = false;
      }
    }
  }

  if (devStatusEls.section) {
    if (devStatusEls.refresh) {
      devStatusEls.refresh.addEventListener("click", loadDevotionalStatus);
    }
    loadDevotionalStatus();
  }

  // 事件監聽綁定
  const btnCheckAll = document.getElementById("btn-check-all");
  if (btnCheckAll) {
    btnCheckAll.addEventListener("click", () => runAction("/api/action/check_all", btnCheckAll, "全自動檢驗 (check_all.py)"));
  }

  const btnVisual = document.getElementById("btn-visual-checks");
  if (btnVisual) {
    btnVisual.addEventListener("click", () => runAction("/api/action/visual_checks", btnVisual, "視覺與無障礙檢驗 (visual_checks.py)"));
  }

  const btnVerifyText = document.getElementById("btn-verify-text");
  if (btnVerifyText) {
    btnVerifyText.addEventListener("click", () => runAction("/api/action/verify_text", btnVerifyText, "經文比對 (verify_text.py)"));
  }

  const btnSmoke = document.getElementById("btn-smoke");
  if (btnSmoke) {
    btnSmoke.addEventListener("click", () => runAction("/api/action/smoke_test", btnSmoke, "冒煙測試 (smoke.js)"));
  }

  const btnRefreshModels = document.getElementById("btn-refresh-models");
  if (btnRefreshModels) {
    btnRefreshModels.addEventListener("click", () => {
      loadModels();
      loadStatus();
    });
  }

  // 報告標籤頁切換
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      e.target.classList.add("active");
      const report = e.target.dataset.report;
      loadReport(report);
    });
  });

  // 初始載入
  loadStatus();
  loadModels();
  setLinks();
  loadReport("TEST-REPORT.md");

  // 每 15 秒更新一次狀態
  setInterval(() => {
    loadStatus();
  }, 15000);

  // 地端模型叢集每 20 分鐘探測一次
  setInterval(() => {
    loadModels();
  }, 20 * 60 * 1000);
});
