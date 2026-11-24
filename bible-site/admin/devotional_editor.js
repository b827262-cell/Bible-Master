/* 每日禱讀內容管理（設定／新增修改／審核／上架）
 *
 * 契約來源：tasks/145-devotional-admin-backend.md、tasks/146-devotional-admin-ui.md、
 * tasks/147-devotional-admin-operations.md。
 *
 * 邊界：
 * - 只呼叫 /api/devotional-editor/*，所有請求（含 GET）都自行取得 /api/token，
 *   並帶 X-Bible-Admin:1 與 X-Bible-Token；權杖只存在這個 closure 的記憶體。
 * - 不用 localStorage／sessionStorage，不把 token 或內容寫到瀏覽器儲存。
 * - 所有後端文字都用 textContent 呈現，不組 HTML。
 * - 任何失敗都保留使用者輸入；409 只提示重新讀取，不自動覆蓋。
 * - 本檔獨立註冊 DOMContentLoaded，取 token 失敗不會影響 admin.js 的其他功能。
 */
(function () {
  "use strict";

  var API_BASE = "/api/devotional-editor";
  var REQUEST_TIMEOUT_MS = 15000;
  var PUBLISH_TIMEOUT_MS = 120000;
  var MAX_RANGE_DAYS = 366;
  var APPROVED = "APPROVED";

  var section = document.getElementById("devotional-editor");
  if (!section) return;

  function $(id) {
    return document.getElementById(id);
  }

  var els = {
    settings: {
      reload: $("dev-editor-settings-reload"),
      enabled: $("dev-editor-enabled"),
      start: $("dev-editor-start"),
      end: $("dev-editor-end"),
      time: $("dev-editor-time"),
      today: $("dev-editor-today"),
      service: $("dev-editor-service"),
      busy: $("dev-editor-busy"),
      version: $("dev-editor-version"),
      warning: $("dev-editor-settings-warning"),
      status: $("dev-editor-settings-status"),
      save: $("dev-editor-settings-save")
    },
    list: {
      from: $("dev-editor-list-from"),
      through: $("dev-editor-list-through"),
      refresh: $("dev-editor-list-refresh"),
      newButton: $("dev-editor-new"),
      status: $("dev-editor-list-status"),
      approvedList: $("dev-editor-approved-list"),
      approvedEmpty: $("dev-editor-approved-empty"),
      draftsList: $("dev-editor-drafts-list"),
      draftsEmpty: $("dev-editor-drafts-empty")
    },
    form: {
      mode: $("dev-editor-mode"),
      date: $("dev-editor-date"),
      title: $("dev-editor-title"),
      reference: $("dev-editor-reference"),
      source: $("dev-editor-source"),
      summary: $("dev-editor-summary"),
      reflection: $("dev-editor-reflection"),
      prayer: $("dev-editor-prayer"),
      preview: $("dev-editor-preview"),
      save: $("dev-editor-save"),
      status: $("dev-editor-form-status"),
      scriptureNote: $("dev-editor-scripture-note"),
      ranges: $("dev-editor-ranges"),
      scripture: $("dev-editor-scripture")
    },
    review: {
      reviewer: $("dev-editor-reviewer"),
      source: $("dev-editor-confirm-source"),
      theology: $("dev-editor-confirm-theology"),
      approve: $("dev-editor-approve"),
      status: $("dev-editor-review-status")
    },
    publish: {
      button: $("dev-editor-publish"),
      spinner: $("dev-editor-publish-spinner"),
      label: $("dev-editor-publish-label"),
      reason: $("dev-editor-publish-reason"),
      status: $("dev-editor-publish-status")
    }
  };

  if (!els.settings.save || !els.form.save || !els.publish.button) return;

  var state = {
    token: "",
    tokenPromise: null,
    settings: null,
    settingsBaseVersion: null,
    settingsLoaded: false,
    settingsDirty: false,
    settingsStale: false,
    settingsBusy: false,
    list: { entries: [], drafts: [], loaded: false, busy: false },
    listRangeTouched: false,
    form: null,
    reviewBusy: false,
    publishBusy: false,
    gen: { settings: 0, list: 0, form: 0, preview: 0 }
  };

  // ---------- 小工具 ----------

  function setStatus(el, text, kind) {
    if (!el) return;
    el.textContent = text || "";
    el.className = "dev-editor-status" + (kind ? " is-" + kind : "");
  }

  function make(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function isISODate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return false;
    var date = new Date(value + "T00:00:00Z");
    return !isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
  }

  function addDays(iso, days) {
    var date = new Date(iso + "T00:00:00Z");
    date.setUTCDate(date.getUTCDate() + days);
    return date.toISOString().slice(0, 10);
  }

  function daysInclusive(from, through) {
    var start = new Date(from + "T00:00:00Z").getTime();
    var end = new Date(through + "T00:00:00Z").getTime();
    if (isNaN(start) || isNaN(end)) return NaN;
    return Math.round((end - start) / 86400000) + 1;
  }

  function taipeiToday() {
    try {
      return new Intl.DateTimeFormat("en-CA", {
        timeZone: "Asia/Taipei",
        year: "numeric",
        month: "2-digit",
        day: "2-digit"
      }).format(new Date());
    } catch (err) {
      return new Date().toISOString().slice(0, 10);
    }
  }

  function shortVersion(version) {
    if (version === null || version === undefined || version === "") return "未知";
    var text = String(version);
    return text.length > 16 ? text.slice(0, 16) + "…" : text;
  }

  function statusLabel(value) {
    if (!value) return "未知";
    if (value === APPROVED) return "已核准";
    return String(value);
  }

  function approvalText(source, theology) {
    if (source === APPROVED && theology === APPROVED) return "已核准";
    return "待審（來源：" + statusLabel(source) + "；神學：" + statusLabel(theology) + "）";
  }

  function serviceText(service) {
    if (!service || typeof service !== "object") return "未知";
    var parts = [];
    var active = service.active;
    if (active === true || active === "active" || active === "activating") {
      parts.push("執行中");
    } else if (active === false || active === "inactive") {
      parts.push("閒置");
    } else if (active === "failed") {
      parts.push("失敗");
    } else if (active) {
      parts.push(String(active));
    }
    if (service.result) parts.push("上次結果：" + String(service.result));
    return parts.length ? parts.join("；") : "未知";
  }

  function serviceActive(settings) {
    if (!settings) return false;
    if (settings.busy === true) return true;
    var service = settings.service || {};
    return service.active === true || service.active === "active" || service.active === "activating";
  }

  // ---------- 權杖與 API ----------

  function EditorError(message, status, timeout) {
    this.name = "EditorError";
    this.message = message;
    this.status = typeof status === "number" ? status : 0;
    this.timeout = timeout === true;
  }
  EditorError.prototype = Object.create(Error.prototype);
  EditorError.prototype.constructor = EditorError;

  function ensureToken() {
    if (state.token) return Promise.resolve(state.token);
    if (state.tokenPromise) return state.tokenPromise;
    state.tokenPromise = fetch("/api/token", {
      credentials: "same-origin",
      cache: "no-store"
    }).then(function (res) {
      if (!res.ok) return "";
      return res.json().then(function (data) {
        var token = data && typeof data.token === "string" ? data.token : "";
        if (token) state.token = token;
        return token;
      });
    }).catch(function () {
      return "";
    }).then(function (token) {
      state.tokenPromise = null;
      return token;
    }, function () {
      state.tokenPromise = null;
      return "";
    });
    return state.tokenPromise;
  }

  function apiCall(path, options) {
    var opts = options || {};
    var timeout = typeof opts.timeout === "number" ? opts.timeout : REQUEST_TIMEOUT_MS;
    return ensureToken().then(function (token) {
      if (!token) {
        throw new EditorError("無法取得寫入權杖，請重新整理頁面後再試。", 0);
      }
      var controller = new AbortController();
      var timer = setTimeout(function () {
        controller.abort();
      }, timeout);
      var headers = { "X-Bible-Admin": "1", "X-Bible-Token": token };
      if (opts.body !== undefined) headers["Content-Type"] = "application/json";
      return fetch(API_BASE + path, {
        method: opts.method || "GET",
        headers: headers,
        body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
        credentials: "same-origin",
        cache: "no-store",
        signal: controller.signal
      }).then(function (res) {
        return res.text().then(function (text) {
          var data = null;
          if (text) {
            try {
              data = JSON.parse(text);
            } catch (err) {
              data = null;
            }
          }
          return { res: res, data: data };
        });
      }).then(function (result) {
        clearTimeout(timer);
        if (!result.res.ok) {
          var message = result.data && typeof result.data.error === "string" && result.data.error
            ? result.data.error
            : "後台回傳錯誤（HTTP " + result.res.status + "）。";
          throw new EditorError(message, result.res.status);
        }
        if (!result.data || typeof result.data !== "object") {
          throw new EditorError("後台回應格式不正確。", 0);
        }
        return result.data;
      }, function (err) {
        clearTimeout(timer);
        if (err && err.name === "AbortError") {
          throw new EditorError("請求逾時，無法確認結果。", 0, true);
        }
        if (err instanceof EditorError) throw err;
        throw new EditorError("無法連線到後台服務，請確認服務是否運行。", 0);
      });
    });
  }

  function describeError(err) {
    if (err instanceof EditorError) return err.message;
    if (err && typeof err.message === "string" && err.message) return err.message;
    return "發生未預期的錯誤。";
  }

  function handleActionError(err, statusEl, prefix, conflictHint) {
    if (err instanceof EditorError && err.status === 409) {
      setStatus(statusEl, prefix + " 版本衝突（409）：" + conflictHint + " 你的輸入已保留，系統不會自動覆蓋。", "error");
      return;
    }
    if (err instanceof EditorError && err.timeout) {
      setStatus(statusEl, prefix + " 請求逾時，無法確認結果；請重新讀取狀態後再試。", "warning");
      return;
    }
    if (err instanceof EditorError && err.status === 403) {
      setStatus(statusEl, prefix + " 沒有寫入權限（403）：" + describeError(err) + " 請重新整理頁面再試。", "error");
      return;
    }
    if (err instanceof EditorError && err.status === 503) {
      setStatus(statusEl, prefix + " 服務暫時無法使用（503）：" + describeError(err), "error");
      return;
    }
    setStatus(statusEl, prefix + " " + describeError(err), "error");
  }

  // ---------- 表單狀態 ----------

  function emptyContent() {
    return {
      date: "",
      reference: "",
      title: "",
      source_url: "",
      summary: "",
      reflection: "",
      prayer: ""
    };
  }

  function newForm(overrides) {
    var base = {
      mode: "new",
      draftId: null,
      draftVersion: 0,
      entryId: null,
      baseVersion: null,
      savedVersion: null,
      status: "NEW",
      dirty: false,
      locked: false,
      busy: false,
      previewing: false,
      previewRef: "",
      content: emptyContent(),
      scripture: []
    };
    if (overrides) {
      Object.keys(overrides).forEach(function (key) {
        base[key] = overrides[key];
      });
    }
    return base;
  }

  function readContent() {
    return {
      date: els.form.date.value.trim(),
      reference: els.form.reference.value.trim(),
      title: els.form.title.value.trim(),
      source_url: els.form.source.value.trim(),
      summary: els.form.summary.value,
      reflection: els.form.reflection.value,
      prayer: els.form.prayer.value
    };
  }

  function writeContent(content) {
    var c = content || {};
    els.form.date.value = typeof c.date === "string" ? c.date : "";
    els.form.reference.value = typeof c.reference === "string" ? c.reference : "";
    els.form.title.value = typeof c.title === "string" ? c.title : "";
    els.form.source.value = typeof c.source_url === "string" ? c.source_url : "";
    els.form.summary.value = typeof c.summary === "string" ? c.summary : "";
    els.form.reflection.value = typeof c.reflection === "string" ? c.reflection : "";
    els.form.prayer.value = typeof c.prayer === "string" ? c.prayer : "";
  }

  function formLocked() {
    var form = state.form;
    return !form || form.locked || form.busy || form.previewing || state.reviewBusy;
  }

  function validateContent(content) {
    if (!content.date) return "請填寫日期。";
    if (!isISODate(content.date)) return "日期格式不正確，請使用西元 YYYY-MM-DD。";
    if (!content.title) return "請填寫主題。";
    if (content.title.length > 80) return "主題最多 80 字。";
    if (!content.reference) return "請填寫經文出處。";
    if (content.reference.length > 240) return "經文出處最多 240 字。";
    if (content.source_url.length > 2048) return "來源網址最多 2048 字。";
    if (content.source_url && !/^https?:\/\//i.test(content.source_url)) {
      return "來源網址需以 http:// 或 https:// 開頭；留空則使用本站經文頁面。";
    }
    if (!content.summary) return "請填寫默想。";
    if (content.summary.length > 6000) return "默想最多 6000 字。";
    if (!content.reflection) return "請填寫反思。";
    if (content.reflection.length > 2000) return "反思最多 2000 字。";
    if (!content.prayer) return "請填寫禱告。";
    if (content.prayer.length > 6000) return "禱告最多 6000 字。";
    return null;
  }

  function validateSettings(values) {
    if (!isISODate(values.start_date)) return "請填寫正確的開始日期。";
    if (!isISODate(values.end_date)) return "請填寫正確的截止日期。";
    if (values.start_date > values.end_date) return "開始日期不可晚於截止日期。";
    var days = daysInclusive(values.start_date, values.end_date);
    if (!isFinite(days) || days > 730) return "上架期間最多 730 天。";
    if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(values.time)) return "執行時間格式需為 HH:MM（24 小時制）。";
    return null;
  }

  // ---------- 畫面更新 ----------

  function modeText() {
    var form = state.form;
    var base;
    if (form.mode === "entry") {
      base = "修改既有文章（儲存後產生修訂草稿）";
      if (!form.dirty && form.baseVersion) base += "・文章版本 " + shortVersion(form.baseVersion);
    } else if (form.mode === "draft") {
      base = "修改草稿（尚未核准）";
      if (!form.dirty && form.savedVersion !== null) base += "・草稿版本 " + shortVersion(form.savedVersion);
    } else {
      base = "新增內容";
    }
    if (form.dirty) base += "・尚未儲存";
    return base;
  }

  function reviewBlockedReason() {
    var form = state.form;
    if (!form) return "尚未載入。";
    if (form.locked || form.busy || form.previewing || state.reviewBusy) return "目前有操作進行中，請稍候。";
    if (form.savedVersion === null) return "請先儲存草稿，才能審核。";
    if (form.dirty) return "內容已修改，請重新儲存草稿後再審核。";
    if (!els.review.reviewer.value.trim()) return "請填寫審核者姓名。";
    if (els.review.source.checked !== true || els.review.theology.checked !== true) return "請勾選兩項確認。";
    return null;
  }

  function updateSettingsUi() {
    var locked = !state.settingsLoaded || state.settingsBusy || state.publishBusy;
    [els.settings.enabled, els.settings.start, els.settings.end, els.settings.time].forEach(function (el) {
      el.disabled = locked;
    });
    els.settings.save.disabled = locked || !state.settingsDirty;
    els.settings.reload.disabled = state.settingsBusy || state.publishBusy;
  }

  function updateFormUi() {
    var form = state.form;
    if (!form) return;
    var locked = formLocked();
    [els.form.date, els.form.title, els.form.reference, els.form.source,
      els.form.summary, els.form.reflection, els.form.prayer].forEach(function (el) {
      el.disabled = locked;
    });
    els.form.preview.disabled = locked || !els.form.reference.value.trim();
    els.form.save.disabled = locked;
    els.review.reviewer.disabled = locked;
    els.review.source.disabled = locked;
    els.review.theology.disabled = locked;
    els.review.approve.disabled = reviewBlockedReason() !== null;
    els.form.mode.textContent = modeText();

    if (form.dirty) {
      setStatus(els.review.status,
        form.savedVersion === null
          ? "內容尚未儲存：請先按「儲存草稿」，才能審核。"
          : "內容已修改：確認勾選已清除，請重新儲存草稿後再審核。",
        "warning");
    }
  }

  function publishState() {
    if (state.publishBusy) return { blocked: true, text: "上架請求處理中，請稍候…" };
    if (!state.settingsLoaded || !state.settings) {
      return { blocked: true, text: "設定尚未載入，無法上架。" };
    }
    var settings = state.settings;
    if (serviceActive(settings)) {
      return { blocked: true, text: "上架服務正在執行，請等完成並重新整理狀態。" };
    }
    if (!settings.start_date || !settings.end_date || !settings.today) {
      return { blocked: true, text: "無法確認上架期間（設定缺少日期），請重新載入設定。" };
    }
    if (settings.today < settings.start_date) {
      return { blocked: true, text: "今天尚未進入上架期間（" + settings.start_date + " 起）。" };
    }
    if (settings.today > settings.end_date) {
      return { blocked: true, text: "已超過上架截止日（" + settings.end_date + "），手動上架不開放。" };
    }
    if (!settings.version) {
      return { blocked: true, text: "無法確認設定版本，請重新載入設定。" };
    }
    if (settings.enabled === false) {
      return { blocked: false, text: "自動排程已暫停；手動上架仍可使用。" };
    }
    return { blocked: false, text: "今天在設定的上架期間內，可以手動上架已核准內容。" };
  }

  function updatePublishUi() {
    var st = publishState();
    els.publish.button.disabled = state.publishBusy || st.blocked;
    els.publish.spinner.hidden = !state.publishBusy;
    els.publish.label.textContent = state.publishBusy ? "上架中，請稍候…" : "立即上架已核准內容";
    els.publish.reason.textContent = st.text;
    els.publish.reason.className = "dev-editor-status" + (st.blocked ? " is-warning" : "");
  }

  function updateAll() {
    updateSettingsUi();
    updateFormUi();
    updatePublishUi();
    var form = state.form || {};
    var busy = state.settingsBusy || state.list.busy || state.reviewBusy || state.publishBusy ||
      form.locked || form.busy || form.previewing;
    section.setAttribute("aria-busy", busy ? "true" : "false");
  }

  function renderSettingsMeta(settings) {
    var s = settings || {};
    els.settings.today.textContent = s.today ? String(s.today) : "未知";
    els.settings.service.textContent = serviceText(s.service);
    els.settings.busy.textContent = s.busy === true ? "是（服務執行中）" : (s.busy === false ? "否" : "未知");
    els.settings.version.textContent = s.version ? shortVersion(s.version) : "未知";

    var parts = [];
    if (s.warning) parts.push(String(s.warning));
    if (state.settingsStale) {
      parts.push("設定已在其他頁面更新；目前輸入已保留，儲存前請先按「重新載入設定」。");
    }
    setStatus(els.settings.warning, parts.join(" "), parts.length ? "warning" : "");
  }

  function applyListRangeDefaults(settings) {
    if (state.listRangeTouched) return;
    var s = settings || {};
    var from = s.start_date || s.today || taipeiToday();
    var through = s.end_date || addDays(from, 30);
    els.list.from.value = from;
    els.list.through.value = through;
  }

  // ---------- 經文預覽 ----------

  function firstValue() {
    for (var i = 0; i < arguments.length; i += 1) {
      var value = arguments[i];
      if (value !== undefined && value !== null && value !== "") return value;
    }
    return undefined;
  }

  // 依後端 ranges 的實際欄位（chapter／start_chapter／end_chapter…）輸出
  // canonical 形式，例如 MAT 4:23–5:12；不假設只有單一節或單一章。
  function formatRange(range) {
    if (typeof range === "string") return range;
    if (Array.isArray(range)) {
      return range.map(formatRange).filter(Boolean).join("、");
    }
    if (!range || typeof range !== "object") return "";

    var book = firstValue(range.book, range.book_code, range.book_id, range.book_name);
    if (book && typeof book === "object") {
      book = firstValue(book.code, book.abbr, book.id, book.name);
    }

    var start = range.start && typeof range.start === "object" ? range.start : null;
    var end = range.end && typeof range.end === "object" ? range.end : null;

    var startChapter = firstValue(range.start_chapter, range.startChapter,
      range.chapter, start && start.chapter);
    var endChapter = firstValue(range.end_chapter, range.endChapter,
      end && end.chapter, range.chapter, start && start.chapter);
    var startVerse = firstValue(range.start_verse, range.startVerse,
      range.verse, start && start.verse);
    var endVerse = firstValue(range.end_verse, range.endVerse, end && end.verse,
      (typeof range.end === "number" || typeof range.end === "string") ? range.end : undefined);

    var ref = "";
    if (startChapter !== undefined) {
      var chapterText = String(startChapter);
      var endChapterText = endChapter !== undefined ? String(endChapter) : chapterText;
      ref = chapterText;
      if (startVerse !== undefined) ref += ":" + String(startVerse);
      if (endVerse !== undefined) {
        if (endChapterText !== chapterText) {
          ref += "–" + endChapterText + ":" + String(endVerse);
        } else if (String(endVerse) !== String(startVerse)) {
          ref += "–" + String(endVerse);
        }
      } else if (endChapterText !== chapterText) {
        ref += "–" + endChapterText;
      }
    } else if (startVerse !== undefined) {
      ref = String(startVerse);
      if (endVerse !== undefined && String(endVerse) !== ref) ref += "–" + String(endVerse);
    }

    return [book === undefined ? "" : String(book), ref].filter(Boolean).join(" ");
  }

  function clearScripture(note) {
    state.form.scripture = [];
    state.form.previewRef = "";
    els.form.scripture.replaceChildren();
    els.form.ranges.textContent = "";
    els.form.scriptureNote.textContent = note || "尚未取得經文。";
  }

  function renderScripture(scripture, ranges, reference) {
    var items = Array.isArray(scripture) ? scripture : [];
    state.form.scripture = items;
    state.form.previewRef = reference || "";

    els.form.scripture.replaceChildren();
    els.form.ranges.textContent = "";

    var rangeText = Array.isArray(ranges) ? ranges.map(formatRange).filter(Boolean).join("、") : "";
    if (rangeText) els.form.ranges.textContent = "解析範圍：" + rangeText;

    if (!items.length) {
      els.form.scriptureNote.textContent = "查無經文，請確認經文出處是否為本站四福音的有效範圍。";
      return;
    }

    els.form.scriptureNote.textContent = "共 " + items.length + " 節，唯讀，來自本站經文資料。";
    items.forEach(function (item) {
      var verse = item && typeof item === "object" ? item : {};
      var li = document.createElement("li");
      var ref = make("span", "dev-editor-verse-ref");
      ref.textContent = formatRange(verse) || "經文";
      var text = make("span", "dev-editor-verse-text", verse.text || "");
      li.append(ref, text);
      els.form.scripture.append(li);
    });
  }

  function previewScripture() {
    var form = state.form;
    if (!form || formLocked()) return;
    var reference = els.form.reference.value.trim();
    if (!reference) {
      setStatus(els.form.status, "請先填寫經文出處。", "error");
      return;
    }
    var gen = ++state.gen.preview;
    form.previewing = true;
    updateAll();
    setStatus(els.form.status, "正在讀取經文…", "info");

    apiCall("/preview", { method: "POST", body: { reference: reference } }).then(function (data) {
      if (gen !== state.gen.preview) return;
      form.previewing = false;
      renderScripture(data.scripture, data.ranges, reference);
      setStatus(els.form.status,
        Array.isArray(data.scripture) && data.scripture.length
          ? "已取得 " + data.scripture.length + " 節經文（唯讀）。"
          : "查無經文，請確認經文出處。",
        Array.isArray(data.scripture) && data.scripture.length ? "success" : "warning");
      updateAll();
    }, function (err) {
      if (gen !== state.gen.preview) return;
      form.previewing = false;
      handleActionError(err, els.form.status, "預覽經文失敗。", "請重新讀取後再試。");
      updateAll();
    });
  }

  // ---------- 設定 ----------

  function readSettingsForm() {
    return {
      enabled: els.settings.enabled.checked === true,
      start_date: els.settings.start.value.trim(),
      end_date: els.settings.end.value.trim(),
      time: els.settings.time.value.trim()
    };
  }

  function writeSettingsForm(settings) {
    var s = settings || {};
    els.settings.enabled.checked = s.enabled === true;
    els.settings.start.value = s.start_date || "";
    els.settings.end.value = s.end_date || "";
    els.settings.time.value = s.time || "";
  }

  function loadSettings(force) {
    var gen = ++state.gen.settings;
    state.settingsBusy = true;
    updateAll();
    if (!state.settingsLoaded) setStatus(els.settings.status, "正在載入設定…", "info");

    return apiCall("/settings").then(function (data) {
      if (gen !== state.gen.settings) return;
      var wasDirty = state.settingsDirty && force !== true;
      var previousBase = state.settingsBaseVersion;
      state.settings = data;
      state.settingsLoaded = true;

      if (!wasDirty) {
        state.settingsBaseVersion = data.version || null;
        state.settingsStale = false;
        writeSettingsForm(data);
        state.settingsDirty = false;
        setStatus(els.settings.status, "", "");
      } else {
        state.settingsStale = previousBase !== (data.version || null);
      }

      applyListRangeDefaults(data);
      renderSettingsMeta(data);
      state.settingsBusy = false;
      updateAll();
    }, function (err) {
      if (gen !== state.gen.settings) return;
      state.settingsBusy = false;
      if (!state.settingsLoaded) {
        state.settingsLoaded = false;
        setStatus(els.settings.status,
          "無法載入設定：" + describeError(err) + " 請按「重新載入設定」再試。", "error");
      } else {
        setStatus(els.settings.status,
          "重新載入設定失敗：" + describeError(err) + " 目前顯示的是上次載入的值。", "error");
      }
      updateAll();
    });
  }

  function saveSettings() {
    if (state.settingsBusy || state.publishBusy) return;
    if (!state.settingsLoaded || !state.settingsBaseVersion) {
      setStatus(els.settings.status, "設定尚未載入，無法儲存；請先重新載入設定。", "error");
      return;
    }
    var values = readSettingsForm();
    var problem = validateSettings(values);
    if (problem) {
      setStatus(els.settings.status, problem, "error");
      return;
    }

    var gen = ++state.gen.settings;
    state.settingsBusy = true;
    updateAll();
    setStatus(els.settings.status, "正在儲存設定…", "info");

    var payload = {
      version: state.settingsBaseVersion,
      enabled: values.enabled,
      start_date: values.start_date,
      end_date: values.end_date,
      time: values.time
    };

    apiCall("/settings", { method: "POST", body: payload }).then(function (data) {
      if (gen !== state.gen.settings) return;
      state.settings = data;
      state.settingsLoaded = true;
      state.settingsBaseVersion = data.version || payload.version;
      state.settingsStale = false;
      state.settingsDirty = false;
      state.settingsBusy = false;
      writeSettingsForm(data);
      applyListRangeDefaults(data);
      renderSettingsMeta(data);
      setStatus(els.settings.status, "設定已儲存；排程與手動上架依新設定生效。", "success");
      updateAll();
    }, function (err) {
      if (gen !== state.gen.settings) return;
      state.settingsBusy = false;
      if (err instanceof EditorError && err.status === 409) {
        state.settingsStale = true;
        renderSettingsMeta(state.settings);
      }
      handleActionError(err, els.settings.status, "儲存設定失敗。",
        "設定已在其他地方更新，請按「重新載入設定」查看最新值後再儲存。");
      updateAll();
    });
  }

  function onSettingsInput() {
    if (!state.settingsLoaded || state.settingsBusy || state.publishBusy) return;
    state.settingsDirty = true;
    updateSettingsUi();
  }

  // ---------- 列表 ----------

  function renderLists() {
    els.list.approvedList.replaceChildren();
    els.list.draftsList.replaceChildren();

    if (!state.list.loaded) {
      els.list.approvedEmpty.hidden = false;
      els.list.approvedEmpty.textContent = "尚未讀取。";
      els.list.draftsEmpty.hidden = false;
      els.list.draftsEmpty.textContent = "尚未讀取。";
      return;
    }

    var entries = state.list.entries;
    var drafts = state.list.drafts;

    els.list.approvedEmpty.hidden = entries.length > 0;
    els.list.approvedEmpty.textContent = "此範圍沒有文章。";
    entries.forEach(function (entry) {
      var item = make("li", "dev-editor-item");
      var main = make("div", "dev-editor-item-main");
      main.append(
        make("span", "dev-editor-item-title", entry.title || "（未命名）"),
        make("span", "dev-editor-item-meta",
          [entry.date, entry.reference, approvalText(entry.source_status, entry.theology_status)]
            .filter(Boolean).join("・"))
      );
      var button = make("button", "btn btn-outline", "編輯");
      button.type = "button";
      button.addEventListener("click", function () {
        openEntry(entry.id);
      });
      item.append(main, button);
      els.list.approvedList.append(item);
    });

    els.list.draftsEmpty.hidden = drafts.length > 0;
    els.list.draftsEmpty.textContent = "此範圍沒有待審草稿。";
    drafts.forEach(function (draft) {
      var item = make("li", "dev-editor-item");
      var main = make("div", "dev-editor-item-main");
      var meta = [
        draft.date,
        "草稿版本 " + (draft.version !== undefined ? draft.version : "未知"),
        "未核准"
      ].filter(Boolean).join("・");
      if (draft.updated_at) meta += "・更新 " + String(draft.updated_at);
      main.append(
        make("span", "dev-editor-item-title", draft.title || "（未命名草稿）"),
        make("span", "dev-editor-item-meta", meta)
      );
      var button = make("button", "btn btn-outline", "編輯");
      button.type = "button";
      button.addEventListener("click", function () {
        openDraft(draft.id);
      });
      item.append(main, button);
      els.list.draftsList.append(item);
    });
  }

  function loadList() {
    var from = els.list.from.value.trim();
    var through = els.list.through.value.trim();
    if (!isISODate(from) || !isISODate(through)) {
      setStatus(els.list.status, "請選擇有效的日期範圍（起、迄）。", "error");
      return Promise.resolve();
    }
    if (from > through) {
      setStatus(els.list.status, "開始日期不可晚於結束日期。", "error");
      return Promise.resolve();
    }
    var days = daysInclusive(from, through);
    if (!isFinite(days) || days > MAX_RANGE_DAYS) {
      setStatus(els.list.status, "日期範圍最多 " + MAX_RANGE_DAYS + " 天，請縮小範圍。", "error");
      return Promise.resolve();
    }

    var gen = ++state.gen.list;
    state.list.busy = true;
    updateAll();
    setStatus(els.list.status, "正在讀取內容列表…", "info");

    var query = "?from=" + encodeURIComponent(from) + "&through=" + encodeURIComponent(through);
    return apiCall("/list" + query).then(function (data) {
      if (gen !== state.gen.list) return;
      state.list.entries = Array.isArray(data.entries) ? data.entries : [];
      state.list.drafts = Array.isArray(data.drafts) ? data.drafts : [];
      state.list.loaded = true;
      state.list.busy = false;
      renderLists();
      var total = state.list.entries.length + state.list.drafts.length;
      var approvedCount = state.list.entries.filter(function (entry) {
        return entry.source_status === APPROVED && entry.theology_status === APPROVED;
      }).length;
      setStatus(els.list.status,
        "共 " + state.list.entries.length + " 篇文章（已核准 " + approvedCount + " 篇）、" +
          state.list.drafts.length + " 份待審草稿。" +
          (total >= 500 ? " 已達 500 筆上限，請縮小日期範圍。" : ""),
        total >= 500 ? "warning" : "");
      updateAll();
    }, function (err) {
      if (gen !== state.gen.list) return;
      state.list.busy = false;
      handleActionError(err, els.list.status, "讀取列表失敗。", "請重新讀取。");
      updateAll();
    });
  }

  // ---------- 開啟／新增 ----------

  function confirmDiscard(action) {
    if (!state.form || !state.form.dirty) return true;
    return window.confirm("目前表單有尚未儲存的變更，" + action + "會放棄這些修改。要繼續嗎？");
  }

  function beginForm(overrides, content, scripture, ranges) {
    state.form = newForm(overrides);
    writeContent(content || emptyContent());
    if (Array.isArray(scripture)) {
      renderScripture(scripture, ranges, content && content.reference);
    } else {
      clearScripture("尚未取得經文。");
    }
    els.review.source.checked = false;
    els.review.theology.checked = false;
    setStatus(els.review.status, "", "");
    updateAll();
  }

  function openEntry(id) {
    if (formLocked()) {
      setStatus(els.list.status, "目前有操作進行中，請稍候再切換文章。", "warning");
      return;
    }
    if (!confirmDiscard("切換到另一篇文章")) return;

    var gen = ++state.gen.form;
    state.form.locked = true;
    updateAll();
    setStatus(els.form.status, "正在載入文章…", "info");

    apiCall("/entry?id=" + encodeURIComponent(String(id))).then(function (data) {
      if (gen !== state.gen.form) return;
      var entry = data.entry || {};
      beginForm({
        mode: "entry",
        entryId: entry.id !== undefined ? entry.id : id,
        baseVersion: entry.version !== undefined ? entry.version : null,
        savedVersion: null,
        draftId: null,
        draftVersion: 0,
        dirty: false
      }, entry.content || {}, data.scripture, data.ranges);
      setStatus(els.form.status,
        "已載入既有文章（審核狀態：" + approvalText(entry.source_status, entry.theology_status) +
          "）；修改後儲存會產生修訂草稿，原文章保留到重新核准。", "");
    }, function (err) {
      if (gen !== state.gen.form) return;
      state.form.locked = false;
      handleActionError(err, els.form.status, "載入文章失敗。", "請重新讀取列表後再試。");
      updateAll();
    });
  }

  function openDraft(id) {
    if (formLocked()) {
      setStatus(els.list.status, "目前有操作進行中，請稍候再切換草稿。", "warning");
      return;
    }
    if (!confirmDiscard("切換到另一份草稿")) return;

    var gen = ++state.gen.form;
    state.form.locked = true;
    updateAll();
    setStatus(els.form.status, "正在載入草稿…", "info");

    apiCall("/draft?id=" + encodeURIComponent(String(id))).then(function (data) {
      if (gen !== state.gen.form) return;
      var draft = data.draft || {};
      beginForm({
        mode: "draft",
        draftId: draft.id !== undefined ? draft.id : id,
        draftVersion: typeof draft.version === "number" ? draft.version : 0,
        entryId: draft.entry_id !== undefined ? draft.entry_id : null,
        baseVersion: draft.base_version !== undefined ? draft.base_version : null,
        savedVersion: typeof draft.version === "number" ? draft.version : 0,
        status: draft.status || "DRAFT",
        dirty: false
      }, draft.content || {}, data.scripture, data.ranges);
      setStatus(els.form.status, "已載入未核准草稿；修改後請重新儲存再審核。", "");
    }, function (err) {
      if (gen !== state.gen.form) return;
      state.form.locked = false;
      handleActionError(err, els.form.status, "載入草稿失敗。", "請重新讀取列表後再試。");
      updateAll();
    });
  }

  function startNew() {
    if (formLocked()) {
      setStatus(els.list.status, "目前有操作進行中，請稍候再新增。", "warning");
      return;
    }
    if (!confirmDiscard("新增內容")) return;

    ++state.gen.form;
    ++state.gen.preview;
    var content = emptyContent();
    content.date = (state.settings && state.settings.today) || taipeiToday();
    beginForm({ mode: "new", dirty: false }, content, null);
    setStatus(els.form.status, "已建立空白表單；填寫後請先預覽經文，再儲存草稿。", "");
    els.form.title.focus();
  }

  // ---------- 儲存草稿 ----------

  function onContentInput() {
    var form = state.form;
    if (!form || form.locked || form.busy || form.previewing) return;
    form.dirty = true;
    form.content = readContent();

    if (form.previewRef && form.content.reference !== form.previewRef) {
      ++state.gen.preview;
      clearScripture("經文出處已變更，請重新按「預覽經文」。");
    }

    els.review.source.checked = false;
    els.review.theology.checked = false;
    updateAll();
  }

  function saveDraft() {
    var form = state.form;
    if (!form || formLocked()) return;
    var content = readContent();
    var problem = validateContent(content);
    if (problem) {
      setStatus(els.form.status, problem, "error");
      return;
    }

    var gen = ++state.gen.form;
    form.busy = true;
    form.content = content;
    updateAll();
    setStatus(els.form.status, "正在儲存草稿…", "info");

    var payload = {
      draft_id: form.draftId,
      version: form.draftId ? form.draftVersion : 0,
      entry_id: form.entryId,
      base_version: form.baseVersion,
      content: content
    };

    apiCall("/save", { method: "POST", body: payload }).then(function (data) {
      if (gen !== state.gen.form) return;
      var draft = data.draft || {};
      form.draftId = draft.id !== undefined ? draft.id : form.draftId;
      form.draftVersion = typeof draft.version === "number" ? draft.version : form.draftVersion;
      form.entryId = draft.entry_id !== undefined ? draft.entry_id : form.entryId;
      form.baseVersion = draft.base_version !== undefined ? draft.base_version : form.baseVersion;
      form.savedVersion = form.draftVersion;
      form.status = draft.status || "DRAFT";
      form.mode = "draft";
      form.dirty = false;
      form.busy = false;
      els.review.source.checked = false;
      els.review.theology.checked = false;
      // 以後端回傳的正規化內容為準（trim、source_url 補值），避免畫面上的內容
      // 與實際存進草稿的內容不一致。
      if (draft.content && typeof draft.content === "object") {
        writeContent(draft.content);
        form.content = readContent();
      }
      if (Array.isArray(data.scripture)) {
        renderScripture(data.scripture, data.ranges, form.content.reference);
      }
      setStatus(els.form.status, "草稿已儲存（尚未核准、尚未公開）；確認內容後再審核。", "success");
      updateAll();
      loadList();
    }, function (err) {
      if (gen !== state.gen.form) return;
      form.busy = false;
      handleActionError(err, els.form.status, "儲存草稿失敗。",
        "這篇內容已在其他地方更新，請按「重新讀取」查看最新列表後重新開啟；");
      updateAll();
    });
  }

  // ---------- 審核 ----------

  function approveDraft() {
    var form = state.form;
    if (!form || reviewBlockedReason() !== null) return;

    var gen = ++state.gen.form;
    state.reviewBusy = true;
    updateAll();
    setStatus(els.review.status, "正在送出審核…", "info");

    var payload = {
      draft_id: form.draftId,
      version: form.draftVersion,
      reviewer: els.review.reviewer.value.trim(),
      source_confirmed: els.review.source.checked === true,
      theology_confirmed: els.review.theology.checked === true
    };

    apiCall("/approve", { method: "POST", body: payload }).then(function (data) {
      if (gen !== state.gen.form) return;
      var entry = data.entry || {};
      state.reviewBusy = false;
      if (entry.content) writeContent(entry.content);
      form.content = readContent();
      form.mode = "entry";
      form.entryId = entry.id !== undefined ? entry.id : form.entryId;
      form.baseVersion = entry.version !== undefined ? entry.version : null;
      form.draftId = null;
      form.draftVersion = 0;
      form.savedVersion = null;
      form.status = "APPROVED";
      form.dirty = false;
      els.review.source.checked = false;
      els.review.theology.checked = false;

      var date = (entry.content && entry.content.date) || form.content.date || els.form.date.value;
      var today = state.settings && state.settings.today;
      var message = data.message ? String(data.message) : "審核完成。";
      var schedule = state.settings || {};
      if (date && schedule.start_date && schedule.end_date &&
          (date < schedule.start_date || date > schedule.end_date)) {
        message += " 文章日期 " + date + " 不在目前的上架期間內；請先調整每日上架設定，這篇才會隨排程上架。";
      } else if (today && date && date > today) {
        message += " 已排入 " + date + " 的逐日上架；該日期尚未到，現在不會公開。";
      } else if (today && date === today) {
        message += " 已排入今天的逐日上架；正式站是否更新請看上方狀態卡片。";
      } else {
        message += " 已排入逐日上架；正式站是否更新請看上方狀態卡片。";
      }
      setStatus(els.form.status, "已核准；之後的修改會另存為新修訂草稿。", "success");
      updateAll();
      setStatus(els.review.status, message, "success");
      loadList();
    }, function (err) {
      if (gen !== state.gen.form) return;
      state.reviewBusy = false;
      handleActionError(err, els.review.status, "審核失敗。",
        "草稿已在其他地方更新，請重新讀取列表並重新開啟草稿；");
      updateAll();
    });
  }

  // ---------- 立即上架 ----------

  function publishNow() {
    if (state.publishBusy) return;
    var st = publishState();
    if (st.blocked) {
      setStatus(els.publish.status, st.text, "warning");
      return;
    }

    state.publishBusy = true;
    updateAll();
    setStatus(els.publish.status, "已送出上架請求，等待上架服務完成（最多約 100 秒）…", "info");

    apiCall("/publish", {
      method: "POST",
      timeout: PUBLISH_TIMEOUT_MS,
      body: { confirm: true, schedule_version: state.settings.version }
    }).then(function () {
      state.publishBusy = false;
      setStatus(els.publish.status, "上架服務完成，正式站更新請重新整理確認。", "success");
      updateAll();
      var refresh = document.getElementById("devotional-status-refresh");
      if (refresh && typeof refresh.click === "function") refresh.click();
      loadSettings();
      loadList();
    }, function (err) {
      state.publishBusy = false;
      if (err instanceof EditorError && err.timeout) {
        setStatus(els.publish.status,
          "等待超過 100 秒，無法確認上架結果；上架服務可能仍在執行，請重新讀取狀態確認，不要重複送出。",
          "warning");
        updateAll();
        loadSettings();
        return;
      }
      if (err instanceof EditorError && err.status === 409) {
        setStatus(els.publish.status,
          "無法上架（409）：" + describeError(err) + " 請重新載入設定確認最新狀態。", "error");
        updateAll();
        loadSettings();
        return;
      }
      setStatus(els.publish.status, "上架未完成：" + describeError(err), "error");
      updateAll();
      // 503／連線中斷等情況服務可能仍在執行或狀態已變，一律重新讀取設定。
      loadSettings();
    });
  }

  // ---------- 事件 ----------

  function bind() {
    [els.settings.enabled, els.settings.start, els.settings.end, els.settings.time].forEach(function (el) {
      el.addEventListener("input", onSettingsInput);
      el.addEventListener("change", onSettingsInput);
    });
    els.settings.save.addEventListener("click", saveSettings);
    els.settings.reload.addEventListener("click", function () {
      if (state.settingsBusy || state.publishBusy) return;
      if (state.settingsDirty &&
          !window.confirm("設定有尚未儲存的變更，重新載入會放棄這些修改。要繼續嗎？")) return;
      loadSettings(true);
    });

    els.list.from.addEventListener("change", function () {
      state.listRangeTouched = true;
    });
    els.list.through.addEventListener("change", function () {
      state.listRangeTouched = true;
    });
    els.list.refresh.addEventListener("click", loadList);
    els.list.newButton.addEventListener("click", startNew);

    [els.form.date, els.form.title, els.form.reference, els.form.source,
      els.form.summary, els.form.reflection, els.form.prayer].forEach(function (el) {
      el.addEventListener("input", onContentInput);
      el.addEventListener("change", onContentInput);
    });
    els.form.preview.addEventListener("click", previewScripture);
    els.form.save.addEventListener("click", saveDraft);

    els.review.reviewer.addEventListener("input", updateFormUi);
    els.review.source.addEventListener("change", updateFormUi);
    els.review.theology.addEventListener("change", updateFormUi);
    els.review.approve.addEventListener("click", approveDraft);

    els.publish.button.addEventListener("click", publishNow);

    window.addEventListener("beforeunload", function (event) {
      if ((state.form && state.form.dirty) || state.settingsDirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    });
  }

  function init() {
    var initial = emptyContent();
    initial.date = taipeiToday();
    state.form = newForm({ content: initial });
    writeContent(state.form.content);
    clearScripture("尚未取得經文。");
    var today = taipeiToday();
    els.list.from.value = today;
    els.list.through.value = addDays(today, 30);
    bind();
    updateAll();
    loadSettings().then(function () {
      loadList();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
