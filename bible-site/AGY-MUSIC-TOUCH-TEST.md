# Bible-Master 首頁「第一次觸碰就播音樂」真人 Chrome 手機觸控實測報告

- **實測時間**：2026-11-03 16:37（Asia/Taipei）
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
| **M2** | 先捲動（維持暫停）再點擊（起播） | **通過** | 手指拖動捲動時呼叫 `play()` 被拒絕（`NotAllowedError`），狀態維持暫停；隨後點擊時已重新掛回監聽，順利觸發起播（`currentTime: 1.40s`）。 |
| **M3** | 點按鈕播/停，之後點其他地方不應再播 | **通過** | 點按鈕起播（`currentTime: 1.40s`），再點暫停（`paused: true`）；隨後點擊經文卡，`disarmFirstGesture()` 確保全域監聽已解綁，維持暫停狀態未再起播。 |
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
    - `audio.currentTime === 1.407066s`（穩定推進）
    - `#music-btn.aria-pressed === "true"`
    - `#music-btn.textContent === " 暫停音樂"`（聲波動畫運作）
- **實測截圖**：[`bible-site/screenshots-music/M1_mobile_tap_play.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-music/M1_mobile_tap_play.png) (811 KB)

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
       - 點擊後檢測：`audio.paused === false`，`currentTime === 1.402009s`，`aria-pressed === "true"`，按鈕切換為「 暫停音樂」。
- **實測截圖**：[`bible-site/screenshots-music/M2_scroll_then_tap.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-music/M2_scroll_then_tap.png) (808 KB)

---

### M3. 點按鈕播放與暫停，確認主動暫停後點空白處不重複播放
- **判定結果**：**通過**（初測抓出 bug，修正引入 `disarmFirstGesture()` 後複測確認解決）
- **初測問題與分析（Commit a0d58f0）**：
  - 初測時發現：若使用者第一次互動是直接點擊 `#music-btn`，`onFirstGesture` 遇到 `closest("#music-btn")` 即 `return`，閉包內的 `cleanup()` 從未被呼叫。
  - 這導致使用者在按鈕上按暫停後，點擊畫面其他空白處時，未解綁的全域監聽又被觸發，再次執行 `tryPlay()` 強制播放。
- **最新版本實測驗證（Commit 734fd3a，引入 `disarmFirstGesture()`）**：
  - 全新乾淨 Profile 載入頁面。
  - `#music-btn` 中心座標：`x: 293, y: 238`。
  1. **第一次點擊按鈕**：
     - 觸碰點擊 `#music-btn`：`audio.paused === false`，`currentTime === 1.401973s`，`aria-pressed === "true"`（成功起播）。
     - 按鈕點擊事件觸發 `disarmFirstGesture()`，即刻解綁 `document` 上所有 `GESTURES` 監聽器。
  2. **第二次點擊按鈕**：
     - 再次觸碰點擊 `#music-btn`：`audio.paused === true`，`currentTime === 1.474866s`，`aria-pressed === "false"`，按鈕恢復「♪ 播放音樂」（成功主動暫停）。
  3. **第三次點擊畫面其他區域（經文卡文字 `x: 180, y: 380`）**：
     - 觸碰經文卡後檢驗：
       - `audio.paused === true`（維持暫停）
       - `audio.currentTime === 1.474866s`（時間未前進）
       - `aria-pressed === "false"`
       - 按鈕維持「♪ 播放音樂」
     - **驗證通過**：全域監聽器已完全卸載，使用者主動暫停後點擊畫面任何位置均不會意外自動起播。
- **實測截圖**：[`bible-site/screenshots-music/M3_button_toggle_stay_paused.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-music/M3_button_toggle_stay_paused.png) (810 KB)

---

### M4. 鍵盤 keydown（Tab / Enter）起播
- **判定結果**：**通過**
- **客觀數據**：
  - 初始狀態：`audio.paused === true`，`currentTime === 0`。
  - 發送鍵盤 `Tab` 按鍵事件（`rawKeyDown` + `keyUp`）：
    - 鍵盤事件觸發 `GESTURES` 中的 `keydown` 監聽。
  - 經過 1.5 秒後：
    - `audio.paused === false`
    - `audio.currentTime === 1.410845s`
    - `aria-pressed === "true"`
    - 按鈕切換為「 暫停音樂」。
- **實測截圖**：[`bible-site/screenshots-music/M4_keyboard_play.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-music/M4_keyboard_play.png) (812 KB)

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
    - `audio.currentTime === 1.419373s`
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

1. **行程停止**：測試結束後已停止測試前台行程（Port 18190）及所有測試 Chrome 行程。
2. **暫存清理**：已完整刪除 `/tmp/agy-music-test` 複本目錄與 `/tmp/chrome-music-*` 臨時使用者資料目錄。
3. **線上服務保護**：線上生產環境 `8090`（PID 1439868）與 `8091`（PID 2158975）全程保持運行，未受任何干擾。
4. **工作目錄乾淨度**：未修改任何程式碼、未執行 `git commit` 或 `git push`；真實工作目錄僅新增驗收報告 `bible-site/AGY-MUSIC-TOUCH-TEST.md` 與截圖目錄 `bible-site/screenshots-music/`。


---

## 複測實測報告（M3、M3b、M1 回歸、M2 回歸）

- **實測時間**：2026-11-03 16:42（Asia/Taipei）
- **實測版本**：最新本機 `main` 分支（Commit `734fd3a`：引入 `disarmFirstGesture()` 解除全域監聽）
- **實測環境**：
  - Chrome 156.0.8078.73（X11 真實視窗，`DISPLAY=:0`）
  - Chrome 預設自動播放政策（無 `--autoplay-policy=no-user-gesture-required`）
  - 每個項目均使用獨立全新 User Data Profile（杜絕 MEI 記憶）
  - 裝置模擬：375×812、`mobile: true`、`setTouchEmulationEnabled: true`、CDP `Input.dispatchTouchEvent`（真觸控點擊與滑動）
  - 測試站點：`/tmp/agy-music-test` 複本，埠號 `18190`（`8090`/`8091` 全程未觸碰）

### 複測判定總表

| 項目代號 | 測試項目 | 判定結果 | 一句核心證據 |
|---|---|:---:|---|
| **M3** | 直接點按鈕播/停，再點經文卡與空白處維持暫停 | **通過** | 按鈕暫停後（`paused: true, currentTime: 1.48s`），隨後分別點擊經文卡與空白處，`audio` 均維持暫停、未再重複播放。 |
| **M3b** | 先觸控經文卡起播，再點按鈕暫停，再點按鈕播放 | **通過** | 觸碰經文卡成功起播（`currentTime: 1.40s`）；隨後點按鈕成功暫停（`paused: true`）；再次點按鈕順利恢復播放（`currentTime: 2.98s`）。 |
| **M1 回歸** | 手機觸控點擊經文卡文字起播 | **通過** | 觸控點擊經文卡文字，`audio.paused` 變為 `false`，按鈕切換為「 暫停音樂」，`currentTime` 推進至 `1.41s`，功能完好未受破壞。 |
| **M2 回歸** | 先捲動（維持暫停），隨後點擊觸發播放 | **通過** | 滑動捲動時呼叫 `play()` 被拒絕（`NotAllowedError`），維持暫停；隨後點擊經文卡重新掛載成功起播（`currentTime: 1.39s`），功能完好。 |

---

### 逐項細部客觀數據

#### M3. 直接點按鈕起播 → 再點一次暫停 → 之後點經文卡與空白處維持暫停
- **測試目標**：驗證使用者點擊 `#music-btn` 後立即執行 `disarmFirstGesture()`，解除全域第一次手勢監聽，避免主動暫停後點擊畫面其他區域意外自動播放。
- **判定結果**：**通過**
- **客觀數據**：
  1. 初始狀態（未觸碰）：
     - `audio.paused === true`
     - `audio.currentTime === 0`
     - `#music-btn` aria-pressed: `"false"`，文字: `"♪ 播放音樂"`
  2. 第一次點擊 `#music-btn`（座標 `x: 293, y: 238`）：
     - `audio.paused === false`
     - `audio.currentTime === 1.410700s`
     - `#music-btn` aria-pressed: `"true"`，文字: `" 暫停音樂"`（成功起播，且觸發 `disarmFirstGesture()` 卸載全域監聽）
  3. 第二次點擊 `#music-btn`：
     - `audio.paused === true`
     - `audio.currentTime === 1.483645s`
     - `#music-btn` aria-pressed: `"false"`，文字: `"♪ 播放音樂"`（成功暫停）
  4. 第三次觸碰：點擊經文卡文字（座標 `x: 180, y: 380`）：
     - `audio.paused === true`（維持暫停）
     - `audio.currentTime === 1.483645s`（時間未前進）
     - `#music-btn` aria-pressed: `"false"`，文字: `"♪ 播放音樂"`
  5. 第四次觸碰：點擊畫面空白處（座標 `x: 200, y: 100`）：
     - `audio.paused === true`（維持暫停）
     - `audio.currentTime === 1.483645s`（時間未前進）
     - `#music-btn` aria-pressed: `"false"`，文字: `"♪ 播放音樂"`
- **實測截圖**：[`bible-site/screenshots-music/M3_retest_button_stay_paused.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-music/M3_retest_button_stay_paused.png) (802 KB)

---

#### M3b. 先點經文卡起播 → 再點按鈕暫停 → 再點按鈕恢復播放
- **測試目標**：驗證先透過全域第一次手勢起播後，按鈕的暫停與恢復播放切換依舊正常運作。
- **判定結果**：**通過**
- **客觀數據**：
  1. 全新乾淨 Profile 載入頁面，初始狀態 `paused: true, currentTime: 0`。
  2. 第一次觸碰：不點按鈕，直接點擊經文卡中央文字（座標 `x: 180, y: 380`）：
     - `audio.paused === false`
     - `audio.currentTime === 1.395226s`
     - `#music-btn` aria-pressed: `"true"`，文字: `" 暫停音樂"`（起播成功）
  3. 第二次觸碰：點擊 `#music-btn`：
     - `audio.paused === true`
     - `audio.currentTime === 1.472793s`
     - `#music-btn` aria-pressed: `"false"`，文字: `"♪ 播放音樂"`（暫停成功）
  4. 第三次觸碰：再次點擊 `#music-btn`：
     - `audio.paused === false`
     - `audio.currentTime === 2.981343s`
     - `#music-btn` aria-pressed: `"true"`，文字: `" 暫停音樂"`（恢復播放成功）
- **實測截圖**：[`bible-site/screenshots-music/M3b_tap_then_button_toggle.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-music/M3b_tap_then_button_toggle.png) (802 KB)

---

#### M1 回歸. 手機觸控點擊經文卡文字起播
- **測試目標**：確認修復 M3 後，手機觸控任意非按鈕區域起播之功能未受回歸影響。
- **判定結果**：**通過**
- **客觀數據**：
  - 初始狀態：`audio.paused === true`，`currentTime === 0`，`aria-pressed === "false"`。
  - 觸控點擊經文卡文字（座標 `x: 180, y: 380`）：
    - 點擊後狀態：`audio.paused === false`，`currentTime === 1.408429s`，`aria-pressed === "true"`，按鈕切換為「 暫停音樂」。
- **實測截圖**：[`bible-site/screenshots-music/M1_regression.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-music/M1_regression.png) (810 KB)

---

#### M2 回歸. 先捲動畫面（保持暫停），隨後點擊觸發起播
- **測試目標**：確認捲動被瀏覽器判定拒絕後，重新掛載機制仍正常運作。
- **判定結果**：**通過**
- **客觀數據**：
  - 捲動操作：手指自 `y: 520` 向上滑動至 `y: 180`（touchMove 系列事件）：
    - 監聽記錄：`audio.play() called` → `play() rejected: NotAllowedError`。
    - 捲動後檢測：`audio.paused === true`，`currentTime === 0`（維持暫停，並重新 arm 監聽）。
  - 隨後點擊經文卡（座標 `x: 180, y: 350`）：
    - 監聽記錄：`audio.play() called` → `play() resolved`。
    - 點擊後檢測：`audio.paused === false`，`currentTime === 1.393496s`，`aria-pressed === "true"`，按鈕切換為「 暫停音樂」。
- **實測截圖**：[`bible-site/screenshots-music/M2_regression.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-music/M2_regression.png) (806 KB)
