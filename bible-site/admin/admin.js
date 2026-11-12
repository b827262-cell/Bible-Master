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
});
