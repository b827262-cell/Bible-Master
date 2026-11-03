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

  function homeStatus(text, kind) {
    const el = homeEls.status;
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

  async function uploadFile(kind, file) {
    if (!file) return;
    const limit = kind === "image" ? IMAGE_MAX_BYTES : MUSIC_MAX_BYTES;
    const limitText = kind === "image" ? "5 MB" : "8 MB";
    if (file.size > limit) {
      homeStatus(`檔案太大（${(file.size / 1024 / 1024).toFixed(1)} MB），${kind === "image" ? "圖片" : "音樂"}上限是 ${limitText}`, "error");
      return;
    }

    let widthWarning = "";
    if (kind === "image") {
      const width = await readImageWidth(file);
      if (width > 1600) widthWarning = "圖片寬度超過 1600px，建議先縮小再上傳";
    }

    homeStatus(`正在上傳 ${file.name}…`);
    try {
      const res = await fetch(`/api/upload?kind=${kind}&name=${encodeURIComponent(file.name)}`, {
        method: "POST",
        headers: writeHeaders({ "Content-Type": "application/octet-stream" }),
        body: file
      });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      const path = data.path;
      if (kind === "image") {
        addOption(homeEls.imageSelect, path);
        updateImagePreview(path);
      } else {
        addOption(homeEls.musicSelect, path);
        updateMusicPreview(path);
      }
      homeStatus(widthWarning || `已上傳 ${file.name}（${data.bytes} bytes）`, widthWarning ? "warning" : "success");
    } catch (err) {
      homeStatus(`上傳失敗：${err.message}`, "error");
    } finally {
      if (kind === "image" && homeEls.imageFile) homeEls.imageFile.value = "";
      if (kind === "music" && homeEls.musicFile) homeEls.musicFile.value = "";
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
