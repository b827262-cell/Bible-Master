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
