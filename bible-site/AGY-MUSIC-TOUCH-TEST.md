# Bible-Master 首頁「第一次觸碰就播音樂」真人 Chrome 手機觸控實測報告

- **實測時間**：2026-11-03 16:33（Asia/Taipei）
- **實測環境**：
  - 作業系統：Linux 6.8.0 x86_64
  - 瀏覽器：Google Chrome 156.0.8078.73（真實 X11 視窗模式，`DISPLAY=:0`）
  - 自動播放政策：**Chrome 預設政策**（未加 `--autoplay-policy=no-user-gesture-required`）
  - 隔離使用者目錄：每次測試均使用全新的獨立 `--user-data-dir` 臨時目錄，杜絕 Media Engagement Index (MEI) 歷史紀錄放行
  - 裝置模擬：Viewport 375×812（iPhone 規格）、`deviceScaleFactor: 3`、`mobile: true`、`Emulation.setTouchEmulationEnabled: true`
  - 觸控模擬方式：真實 CDP `Input.dispatchTouchEvent`（`touchStart` → `touchMove` → `touchEnd`，包含 `isTrusted: true` 之 `pointerdown/up`、`touchstart/end`、`click` 完整事件鏈）
  - 測試站點：隔離複本 `/tmp/agy-music-test/bible-site`，埠號 `18190`（線上 `8090` / `8091` 全程未觸碰、完好在線）
- **實測原則**：只測試、不改程式碼、不提交 commit。

---

## 實測判定總表

| 項目代號 | 測試項目 | 判定結果 | 一句核心證據 |
|---|---|:---:|---|
| **M1** | 觸碰畫面空白處／經文卡起播 | **通過** | 手機模式下觸控點擊經文卡文字，`audio.paused` 變為 `false`，按鈕 `aria-pressed` 變為 `"true"`，`currentTime` 推進至 `1.41s`。 |
| **M2** | 先捲動（維持暫停）再點擊（起播） | **通過** | 手指拖動捲動時呼叫 `play()` 被拒絕（`NotAllowedError`），狀態維持暫停；隨後點擊時已重新掛回監聽，順利觸發起播（`currentTime: 1.41s`）。 |
| **M3** | 點按鈕播/停，之後點其他地方不應再播 | **不通過** | 點按鈕起播後再點暫停成功；但因按鈕點擊未解除全域監聽，隨後點擊經文卡時又自動重新起播（`paused` 變為 `false`，推進至 `2.98s`）。 |
| **M4** | 鍵盤 keydown（Tab）起播 | **通過** | 發出鍵盤 Tab 按鍵事件後，`audio.paused` 變為 `false`，`currentTime` 推進至 `1.41s`，按鈕切換為「 暫停音樂」。 |
| **M5** | 桌機模式滑鼠點擊空白處起播 | **通過** | 關閉觸控模擬之桌機視窗（1440×900）以滑鼠點擊空白處，`audio.paused` 變為 `false`，`currentTime` 推進至 `1.41s`。 |
| **M6** | 對照組：舊版 pointerdown 實測 | **通過** | 對照組 `home-old.html`（commit 2f3e8c7）以相同觸控點擊經文卡，`audio.paused` 始終為 `true`、`currentTime: 0`，證實舊版確實無法起播。 |

---

## 逐項細部客觀數據與分析

### M1. 手機觸控點擊經文卡文字起播
- **測試網址**：`http://127.0.0.1:18190/site/home.html`
- **判定結果**：**通過**
- **客觀數據**：
  - 頁面初始狀態（未觸碰）：
    - `audio.paused === true`
    - `audio.currentTime === 0`
    - `#music-btn.aria-pressed === "false"`
    - `#music-btn.textContent === "♪ 播放音樂"`
  - 觸控點擊經文卡中央文字（座標 `x: 180, y: 380`，避開 `#music-btn`）：
    - 事件觸發放開手指之 `touchend` 與 `pointerup`，由 `onFirstGesture` 觸發 `tryPlay()`。
  - 點擊後 1.5 秒狀態：
    - `audio.paused === false`
    - `audio.currentTime === 1.408035s`（穩定推進）
    - `#music-btn.aria-pressed === "true"`
    - `#music-btn.textContent === " 暫停音樂"`（聲波動畫運作）
- **實測截圖**：[`bible-site/screenshots-music/M1_mobile_tap_play.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-music/M1_mobile_tap_play.png) (810 KB)

---

### M2. 先捲動畫面（保持暫停），隨後點擊觸發播放
- **判定結果**：**通過**
- **客觀數據**：
  - 全新乾淨 Profile 載入頁面。
  - 監控日誌注入 `audio.play`：
    1. **模擬滑動捲動**：手指自 `y: 500` 向上滑動至 `y: 180`（多次 `touchMove` 後 `touchEnd`）：
       - 日誌記錄：`audio.play() called` → `play() rejected: NotAllowedError`。
       - 捲動後檢測：`audio.paused === true`，`currentTime === 0`，`aria-pressed === "false"`。
       - 拒絕處理機制：`tryPlay()` 捕獲 `NotAllowedError` 回傳 `false`，內部邏輯成功執行 `armFirstGesture()` 重新將監聽器掛回 `document`。
    2. **隨後點擊經文卡**（座標 `x: 180, y: 350`）：
       - 日誌記錄：`audio.play() called` → `play() resolved`。
       - 點擊後檢測：`audio.paused === false`，`currentTime === 1.407924s`，`aria-pressed === "true"`，按鈕切換為「 暫停音樂」。
- **實測截圖**：[`bible-site/screenshots-music/M2_scroll_then_tap.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-music/M2_scroll_then_tap.png) (808 KB)

---

### M3. 點按鈕播放與暫停，確認主動暫停後點空白處不重複播放
- **判定結果**：**不通過**
- **客觀數據**：
  - 全新乾淨 Profile 載入頁面。
  - `#music-btn` 中心座標：`x: 293, y: 238`。
  1. **第一次點擊按鈕**：
     - 觸碰點擊 `#music-btn`：`audio.paused === false`，`currentTime === 1.401664s`，`aria-pressed === "true"`（成功起播）。
  2. **第二次點擊按鈕**：
     - 再次觸碰點擊 `#music-btn`：`audio.paused === true`，`currentTime === 1.475686s`，`aria-pressed === "false"`，按鈕恢復「♪ 播放音樂」（成功主動暫停）。
  3. **第三次點擊畫面其他區域（經文卡文字 `x: 180, y: 380`）**：
     - 觸碰經文卡後：`audio.paused === false`，`currentTime === 2.981499s`，`aria-pressed === "true"`，按鈕又變成「 暫停音樂」！
     - **不符預期**：使用者已主動按暫停，但點畫面其他地方卻又自動播起來。
- **根本原因分析**：
  檢視 `bible-site/site/home.html` 第 468–502 行：
  ```javascript
  function armFirstGesture() {
    function onFirstGesture(event) {
      if (event.target && event.target.closest && event.target.closest("#music-btn")) {
        return; // <-- 遇到點擊按鈕，直接 return，因此「沒有呼叫 cleanup()」！
      }
      cleanup();
      tryPlay().then(function (ok) {
        if (!ok) {
          armFirstGesture();
        }
      });
    }
    function cleanup() {
      GESTURES.forEach(function (name) {
        document.removeEventListener(name, onFirstGesture);
      });
    }
    GESTURES.forEach(function (name) {
      document.addEventListener(name, onFirstGesture);
    });
  }

  musicBtn.addEventListener("click", function () {
    if (audio.paused) {
      tryPlay();
    } else {
      audio.pause();
    }
  });
  ```
  1. 使用者若第一次互動就直接點擊 `#music-btn`，`onFirstGesture` 因第 470 行判定 `closest("#music-btn")` 而直接返回，**完全沒有執行 `cleanup()`**。
  2. `musicBtn` 自己的 `click` 事件監聽器內亦無呼叫 `cleanup()` 的權限（`cleanup` 閉包封裝在 `armFirstGesture` 內部）。
  3. 這導致 `document` 上面的 `click/pointerup/touchend/keydown` 第一次手勢監聽**始終沒有被卸載**。
  4. 當使用者主動點擊按鈕暫停音樂後，隨後在頁面任意處閱讀或點擊，依然會觸發尚未解綁的 `onFirstGesture`，執行 `tryPlay()` 將音樂再次強制播放！
- **重現步驟**：
  1. 使用新乾淨 Profile 開啟 `http://127.0.0.1:18190/site/home.html`。
  2. 第一次動作直接點擊右下角「♪ 播放音樂」按鈕，音樂開始播放。
  3. 再次點擊該按鈕，音樂暫停。
  4. 隨後用手指觸碰經文卡文字或畫面任一空白處。
  5. 音樂被未卸載的全域監聽器再次起播（`audio.paused` 變為 `false`）。
- **建議修正方案**（依指示本次實測不改程式）：
  可將 `cleanup` 提升至外層閉包，或在 `audio.addEventListener("play", function once() { cleanup(); audio.removeEventListener("play", once); })` 中，只要音訊真正起播（無論是透過按鈕或全域手勢），就一律卸載全域第一次觸碰監聽。
- **實測截圖**：[`bible-site/screenshots-music/M3_button_toggle_stay_paused.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-music/M3_button_toggle_stay_paused.png) (808 KB)

---

### M4. 鍵盤 keydown（Tab / Enter）起播
- **判定結果**：**通過**
- **客觀數據**：
  - 初始狀態：`audio.paused === true`，`currentTime === 0`。
  - 發送鍵盤 `Tab` 按鍵事件（`rawKeyDown` + `keyUp`）：
    - 鍵盤事件觸發 `GESTURES` 中的 `keydown` 監聽。
  - 經過 1.5 秒後：
    - `audio.paused === false`
    - `audio.currentTime === 1.414353s`
    - `aria-pressed === "true"`
    - 按鈕切換為「 暫停音樂」。
- **實測截圖**：[`bible-site/screenshots-music/M4_keyboard_play.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-music/M4_keyboard_play.png) (813 KB)

---

### M5. 桌機模式（不開觸控模擬）滑鼠點擊空白處起播
- **判定結果**：**通過**
- **客觀數據**：
  - 視窗設為桌機尺寸 `1440×900`，`mobile: false`，停用觸控模擬。
  - 初始狀態：`audio.paused === true`，`currentTime === 0`。
  - 滑鼠左鍵點擊背景空白區域（座標 `x: 200, y: 200`）：
    - 觸發滑鼠 `click` / `pointerup` 事件。
  - 經過 1.5 秒後：
    - `audio.paused === false`
    - `audio.currentTime === 1.412280s`
    - `aria-pressed === "true"`
    - 按鈕切換為「 暫停音樂」。
- **實測截圖**：[`bible-site/screenshots-music/M5_desktop_click_play.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-music/M5_desktop_click_play.png) (681 KB)

---

### M6. 對照組實測（舊版 home-old.html，使用 pointerdown）
- **測試對象**：由 `git show 2f3e8c7:bible-site/site/home.html` 匯出之舊版檔案。
- **判定結果**：**通過**
- **客觀數據**：
  - 舊版程式之監聽宣告：
    ```javascript
    document.addEventListener("pointerdown", onFirstGesture);
    document.addEventListener("keydown", onFirstGesture);
    ```
  - 以手機模擬視窗（375×812）載入 `http://127.0.0.1:18190/site/home-old.html`。
  - 初始狀態：`audio.paused === true`，`currentTime === 0`，`aria-pressed === "false"`。
  - 對經文卡文字進行單次觸控點擊（座標 `x: 180, y: 380`）：
    - 雖然觸發了 `pointerdown`，但手機 Chrome 不認定 `pointerdown` 為有效的使用者啟動手勢（User Activation），`audio.play()` 直接被瀏覽器拒絕（`NotAllowedError`）。
    - 舊版程式在呼叫 `tryPlay()` 前就已執行 `cleanup()`，且沒有捕獲失敗重新掛載的機制。
  - 觸碰後 1.5 秒檢驗：
    - `audio.paused === true`（依舊為暫停狀態）
    - `audio.currentTime === 0`（完全未推進）
    - `aria-pressed === "false"`
    - 按鈕文字維持「`♪ 播放音樂`」。
  - **結論**：證實舊版程式在手機觸控環境下點擊非按鈕區域確實完全無法播音樂，新版改掛 `click/pointerup/touchend` 確實解決了觸控起播的核心機制。
- **實測截圖**：[`bible-site/screenshots-music/M6_old_version_no_play.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-music/M6_old_version_no_play.png) (812 KB)

---

## 隔離清理與正式環境確認

1. **行程停止**：測試結束後已停止測試前台行程（PID 2181991, Port 18190）及所有測試 Chrome 行程。
2. **暫存清理**：已完整刪除 `/tmp/agy-music-test` 複本目錄與 `/tmp/chrome-music-*` 臨時使用者資料目錄。
3. **線上服務保護**：線上生產環境 `8090`（PID 1439868）與 `8091`（PID 2158975）全程保持運行，未受任何干擾。
4. **工作目錄乾淨度**：未修改任何程式碼、未執行 `git commit` 或 `git push`；真實工作目錄僅新增驗收報告 `bible-site/AGY-MUSIC-TOUCH-TEST.md` 與截圖目錄 `bible-site/screenshots-music/`。
