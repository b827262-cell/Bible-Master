# Bible-Master 後台「主頁設定」上傳與預覽 真人 Chrome 實測報告

- **實測時間**：2026-11-03 16:01（Asia/Taipei）
- **實測環境**：
  - 作業系統：Linux 6.8.0 x86_64
  - 瀏覽器：Google Chrome 156.0.8078.73（真實 X11 視窗模式，`DISPLAY=:0`，非 headless）
  - 實測連線埠號：`FRONTEND_PORT=18190`、後台 `18191`（線上 `8090` / `8091` 全程未碰觸、未重啟、完好無損運行）
  - 隔離測試環境：`/tmp/agy-admin-test/bible-site` 副本
- **實測原則**：只測試、不改任何程式碼、不變更正式資料庫、不提交 commit。

---

## 總結判定總表

| 項目代號 | 測試項目 | 判定結果 | 一句核心證據 |
|---|---|:---:|---|
| **A1** | 後台載入與主頁設定區塊初態 | **通過** | 開啟 `http://127.0.0.1:18191/` 成功顯示「主頁設定」區塊，下拉選單正確載入預設 `luk 4:27`、`assets/jordan.jpg`、`assets/home-music.mp3`。 |
| **A2** | 書卷／章／節連動與經文預覽 | **通過** | 切換約翰福音第 3 章第 16 節，下拉自動更新為 21 章與 36 節，預覽區即時呈現「約翰福音 3:16」與「神愛世人…反得永生」經文。 |
| **A3** | 圖片上傳（JPG/PNG/大小限制/格式檢驗/寬度提示） | **通過** | JPG 與 PNG 上傳成功並列入下拉選單；>5MB 檔即時警示上限 5 MB；偽裝文字檔經 Magic Sniff 攔截回傳格式不符（皆未留檔案）；>1600px 寬圖出現縮小建議。 |
| **A4** | 音樂 MP3 上傳與音訊播放 | **不通過** | 上傳 10 秒 MP3 成功並加入下拉選單；但後台 `<audio>` 播放失敗（`assetUrl` 寫死 `:8090/assets/` 導致 404 MEDIA_ELEMENT_ERROR）。 |
| **A5** | 點擊「儲存」與資料落地 | **通過** | 點擊儲存後提示「已儲存到本機…記得執行發佈」，複本 `data/home.json` 正確寫入約翰福音 3:16、新圖片與新音樂設定。 |
| **A6** | 前台 home.html 實機呈現與音訊互動 | **通過** | 開啟前台 `http://127.0.0.1:18190/site/home.html` 成功換上約翰福音 3:16、新圖與新音樂，「閱讀本章」連到 luk 換為 jhn 3:16，音樂按鈕能真實播放與暫停。 |
| **A7** | 點擊「還原預設」功能 | **通過** | 點擊還原跳出原生確認視窗，確認後設定正確還原回 luk 4:27，複本 `home.json` 恢復預設，先前上傳之檔案仍保留在選單內。 |
| **A8** | 點擊「開啟主頁預覽」網址分析 | **通過** | 點擊預覽解析開啟網址為 `http://127.0.0.1:8090/`（僅分析網址未操作線上頁面；正式環境合理但開發/自訂埠情境建議動態帶入）。 |
| **A9** | 無障礙與跨視窗實測 (A11y) | **通過** | 所有 11 個控制項高度皆 ≥44px 且具備明顯焦點外框，375px 手機與 1920×1024 桌機無水平溢出，深色模式對比度 >10:1。 |
| **A10** | 安全防護實測（無 Token POST 與 Host 檢驗） | **通過** | Console 未帶 `X-Bible-Token` 發出 POST 回傳 HTTP 403（寫入權杖不正確）；`localhost` 與 `127.0.0.1` 均可正常取得權杖與讀取設定。 |
| **A11** | 頁面重新整理與權杖自動重新取得 | **通過** | 重新整理後台頁面後自動重新呼叫 `/api/token` 取得記憶體權杖，狀態欄顯示「已載入目前設定」，操作功能維持正常。 |

---

## 逐項細部測試數據與證據

### A1. 後台首頁初態檢查
- **測試網址**：`http://127.0.0.1:18191/`
- **判定結果**：**通過**
- **客觀數據**：
  - `document.getElementById('home-settings')` 存在且顯示。
  - 書卷 `#home-book`：`luk`（路加福音）。
  - 章 `#home-ch`：`4`；節 `#home-v`：`27`。
  - 圖片下拉 `#home-image-select`：`assets/jordan.jpg`。
  - 音樂下拉 `#home-music-select`：`assets/home-music.mp3`。
  - 圖片說明 `#home-alt`：`一位男子站在約但河水中，仰望從雲層灑下的光`。
  - 經文預覽 `#home-verse-preview`：`路加福音 4:27先知以利沙的時候、以色列中有許多長大痲瘋的．但內中除了敘利亞國的乃縵、沒有一個得潔淨的。`
  - 狀態列 `#home-status`：`已載入目前設定。`
- **實測截圖**：[`bible-site/screenshots-admin/A1_home_settings_loaded.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A1_home_settings_loaded.png)

---

### A2. 書卷／章／節下拉連動與即時經文預覽
- **判定結果**：**通過**
- **客觀數據**：
  - 將 `#home-book` 改選為 `jhn`（約翰福音）：`#home-ch` 選項數動態重構為 21 章。
  - 將 `#home-ch` 改選為 `3`（第 3 章）：`#home-v` 選項數動態重構為 36 節。
  - 將 `#home-v` 改選為 `16`（第 16 節）：
    - 經文引用標籤顯示 `約翰福音 3:16`。
    - 經文內文即時更新為 `　神愛世人、甚至將他的獨生子賜給他們、叫一切信他的、不至滅亡、反得永生。`
- **實測截圖**：[`bible-site/screenshots-admin/A2_john_3_16_preview.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A2_john_3_16_preview.png)

---

### A3. 圖片上傳完整檢驗
- **判定結果**：**通過**
- **客觀數據**：
  1. **JPG 上傳（800×600）**：
     - 上傳 `test_800x600.jpg`（60,759 bytes）。
     - 狀態提示：`已上傳 test_800x600.jpg（60759 bytes）`。
     - 下拉選單自動新增並選取 `assets/upload-20261103-080113-4c06.jpg`。
     - 預覽圖 `#home-image-preview` 之 `hidden` 屬性設為 `false`。
     - 截圖：[`bible-site/screenshots-admin/A3_1_upload_jpg.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A3_1_upload_jpg.png)
  2. **PNG 上傳**：
     - 上傳 `test_sample.png`（650,428 bytes）。
     - 狀態提示：`已上傳 test_sample.png（650428 bytes）`。
     - 下拉選單自動新增並選取 `assets/upload-20261103-080114-0e70.png`。
     - 截圖：[`bible-site/screenshots-admin/A3_2_upload_png.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A3_2_upload_png.png)
  3. **超過 5 MB 假圖上傳（5.8 MB）**：
     - 上傳 `test_large_6mb.jpg`。
     - 前端立即攔截，狀態提示：`檔案太大（5.7 MB），圖片上限是 5 MB`（`class="home-status is-error"`）。
     - 檢查 `site/assets/` 目錄：檔案數未變動（檔案未落地）。
     - 截圖：[`bible-site/screenshots-admin/A3_3_large_5mb_error.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A3_3_large_5mb_error.png)
  4. **文字檔改名 .jpg 上傳**：
     - 上傳純文字檔 `fake_text.jpg`。
     - 後端 `sniff_upload` 辨識魔術位元組失敗，回傳 HTTP 400 `{"error": "檔案格式不符"}`。
     - 前端狀態提示：`上傳失敗：檔案格式不符`（`class="home-status is-error"`）。
     - 檢查 `site/assets/` 目錄：未留下任何殘餘檔案。
     - 截圖：[`bible-site/screenshots-admin/A3_4_fake_text_error.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A3_4_fake_text_error.png)
  5. **超過 1600px 寬度圖片提示**：
     - 上傳 2000×1125 圖片 `test_wide_2000px.jpg`。
     - 前端 `readImageWidth` 取得 naturalWidth 為 2000px。
     - 狀態提示顯示警告：`圖片寬度超過 1600px，建議先縮小再上傳`（`class="home-status is-warning"`）。
     - 截圖：[`bible-site/screenshots-admin/A3_5_width_warning.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A3_5_width_warning.png)

---

### A4. 音樂 MP3 上傳與音訊播放
- **判定結果**：**不通過**
- **客觀數據**：
  - **上傳部分**：上傳 `test_music_10s.mp3`（160,958 bytes）成功，後端儲存為 `assets/upload-20261103-080119-456c.mp3`，下拉選單自動新增並選取該項目，狀態顯示「`已上傳 test_music_10s.mp3（160958 bytes）`」。
  - **播放部分**：後台 `<audio id="home-music-preview">` 元素無法播放。
    - 實測錯誤：音訊物件 `networkState = 3`（NETWORK_NO_SOURCE），`mediaError.code = 4`（`MEDIA_ELEMENT_ERROR: Format error`）。
    - 根本原因：`bible-site/admin/admin.js` 第 334 行定義：
      ```javascript
      function assetUrl(path) {
        return `${location.protocol}//${location.hostname}:8090/${path}`;
      }
      ```
      此處有兩項路徑缺陷：
      1. 前台 SimpleHTTP 伺服器是以專案根目錄為根，靜態資源的實際 URL 是 `http://127.0.0.1:8090/site/assets/...`，而非 `/assets/...`（請求 `http://127.0.0.1:8090/assets/...` 直接回傳 404 File Not Found）。
      2. 埠號寫死 `:8090`，在以測試埠（18190）運作時，會向線上 8090 請求剛剛上傳到測試環境的檔案，線上 8090 並無該檔案，導致瀏覽器音訊元件因 404 而無法解碼發聲。
- **重現步驟**：
  1. 在後台主頁設定選擇上傳任一合法 MP3 檔。
  2. 上傳完成後，檢查後台 `<audio id="home-music-preview">` 之 `src`，為 `http://127.0.0.1:8090/assets/upload-*.mp3`。
  3. 點擊 `<audio>` 之播放按鈕或以 JS 呼叫 `play()`，瀏覽器發出 HTTP GET 收到 404，音訊載入失敗無法發聲。
- **實測截圖**：[`bible-site/screenshots-admin/A4_music_upload_audio.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A4_music_upload_audio.png)

---

### A5. 點擊「儲存」與資料落地
- **判定結果**：**通過**
- **客觀數據**：
  - 填入圖片說明 `約翰福音與新主視覺實測` 後點擊「儲存」按鈕。
  - 狀態列顯示繁體中文提示：`已儲存到本機。要更新線上網站，請記得執行發佈。`
  - 檢查副本檔案 `/tmp/agy-admin-test/bible-site/data/home.json`：
    ```json
    {
      "book": "jhn",
      "ch": 3,
      "v": 16,
      "image": "assets/upload-20261103-080117-7b80.jpg",
      "alt": "約翰福音與新主視覺實測",
      "music": "assets/upload-20261103-080119-456c.mp3"
    }
    ```
    檔案內容格式完整且正確原子寫入。
- **實測截圖**：[`bible-site/screenshots-admin/A5_home_saved.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A5_home_saved.png)

---

### A6. 前台 home.html 實機更新與音訊互動
- **測試網址**：`http://127.0.0.1:18190/site/home.html`
- **判定結果**：**通過**
- **客觀數據**：
  - 頁面載入後自動自 `data/home.json` 載入剛儲存的設定：
    - 經文標題：`四福音（和合本）`。
    - 經文引用：`約翰福音 3:16（和合本）`。
    - 經文文字：`　神愛世人、甚至將他的獨生子賜給他們、叫一切信他的、不至滅亡、反得永生。`
    - 主視覺圖片 `src`：`assets/upload-20261103-080117-7b80.jpg`。
    - 「閱讀本章」超連結：`chapter.html?book=jhn&ch=3#v16`。
    - 背景音樂 `<audio id="home-music">` `src`：`assets/upload-20261103-080119-456c.mp3`。
  - **音訊點擊播放**：以真實滑鼠事件點擊 `#music-btn`：
    - `audio.paused` 變為 `false`，`currentTime` 推進至 `1.41s`。
    - 按鈕 `aria-pressed` 變為 `"true"`，按鈕文字切換為「` 暫停音樂`」（包含動態音波圖示）。
  - **音訊點擊暫停**：再次點擊 `#music-btn`：
    - `audio.paused` 變為 `true`。
    - 按鈕 `aria-pressed` 變為 `"false"`，按鈕文字切換回「`♪ 播放音樂`」。
- **實測截圖**：[`bible-site/screenshots-admin/A6_frontend_home_updated.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A6_frontend_home_updated.png)

---

### A7. 點擊「還原預設」功能
- **判定結果**：**通過**
- **客觀數據**：
  - 在後台點擊「還原預設」按鈕，觸發瀏覽器原生對話框：`確定要還原成預設的主頁設定嗎？`。
  - 點擊「確認」後：
    - 狀態列顯示：`已還原成預設的主頁設定。`。
    - 表單還原為 `luk`、第 `4` 章、第 `27` 節。
    - 圖片選單與音樂選單還原為 `assets/jordan.jpg` 與 `assets/home-music.mp3`。
    - 圖片下拉選單仍保有 8 個選項、音樂下拉選單保有 3 個選項（先前上傳過的檔案未被刪除）。
    - 副本 `data/home.json` 正確恢復為路加福音 4:27 預設內容。
- **實測截圖**：[`bible-site/screenshots-admin/A7_reset_defaults.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A7_reset_defaults.png)

---

### A8. 點擊「開啟主頁預覽」網址分析
- **判定結果**：**通過**
- **客觀數據**：
  - 後台點擊「開啟主頁預覽」按鈕之程式實作為：
    ```javascript
    function openHomePreview() {
      const url = `${location.protocol}//${location.hostname}:8090/`;
      window.open(url, "_blank");
    }
    ```
  - 實測解析之開啟網址：`http://127.0.0.1:8090/`。
  - 全程僅分析網址，未在 8090 頁面做任何點擊或變更。
  - **正式使用合理性評估**：
    - **正式環境**：合理。正式啟動腳本 `start.sh` 將前台固定在 8090、後台在 8091，開啟 `http://<hostname>:8090/` 會透過根目錄轉址到 `/site/home.html`，符合使用者操作直覺。
    - **非預設埠／開發測試環境**：較不彈性。當使用者指定 `FRONTEND_PORT`（如 18190）啟動多組服務時，寫死 `:8090` 會連線到其他環境。建議未來可由後台啟動參數傳遞或動態計算前台埠號（如 `parseInt(location.port) - 1`）。
- **實測截圖**：[`bible-site/screenshots-admin/A8_home_open_preview.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A8_home_open_preview.png)

---

### A9. 無障礙與跨裝置尺寸實測 (A11y)
- **判定結果**：**通過**
- **客觀數據**：
  1. **控制項高度（≥ 44px 規範）**：
     - `#home-book`：44px（符合）
     - `#home-ch`：44px（符合）
     - `#home-v`：44px（符合）
     - `#home-image-file`：49px（符合）
     - `#home-image-select`：44px（符合）
     - `#home-alt`：44px（符合）
     - `#home-music-file`：49px（符合）
     - `#home-music-select`：44px（符合）
     - `#home-save`：44px（符合）
     - `#home-reset`：44px（符合）
     - `#home-open`：44px（符合）
  2. **鍵盤 Tab 焦點外框**：
     - 所有輸入框與下拉選單具有 `outline: 2px solid var(--accent-light)`。
     - 按鈕在焦點狀態下具有實體對比外框 `outline: auto 3px`（白色/橘色高對比環）。
  3. **375px 手機版**：
     - `scrollWidth: 375px`，`clientWidth: 375px`，無任何水平橫向溢出。
     - 網格自動折為單欄，按鈕寬度展開為 100%，好點擊。
  4. **1920×1024 桌機版**：
     - `scrollWidth: 1905px`，`clientWidth: 1905px`，無水平橫向溢出。
     - 網格工整排列，版面大氣且間距適度。
  5. **深色模式**：
     - 背景色為 `rgb(18, 19, 22)`，卡片色為 `rgb(26, 27, 32)`，文字為 `rgb(240, 242, 245)`。
     - 對比度高達 15.6:1，所有文字與欄位清楚可辨。
- **實測截圖**：
  - 焦點外框：[`bible-site/screenshots-admin/A9_tab_focus_outline.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A9_tab_focus_outline.png)
  - 手機版面：[`bible-site/screenshots-admin/A9_mobile_375px.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A9_mobile_375px.png)
  - 桌機版面：[`bible-site/screenshots-admin/A9_desktop_1920x1024.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A9_desktop_1920x1024.png)
  - 深色模式：[`bible-site/screenshots-admin/A9_dark_mode.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A9_dark_mode.png)

---

### A10. 安全實測：Token 檢驗與 Host 白名單
- **判定結果**：**通過**
- **客觀數據**：
  1. **無 X-Bible-Token 寫入攻擊測試**：
     - 於 DevTools Console 執行 `fetch("/api/home", { method: "POST", headers: { "X-Bible-Admin": "1", "Content-Type": "application/json" }, body: "{}" })`。
     - 後端 `check_write_auth()` 立即拒絕，回傳 HTTP 狀態碼 **403**，回應 JSON 為 `{"error": "寫入權杖不正確"}`。
  2. **Host 位址白名單相容性**：
     - 以 `http://127.0.0.1:18191/` 存取：成功取得 Token，狀態顯示「已載入目前設定。」。
     - 以 `http://localhost:18191/` 存取：成功通過 `LOCAL_HOSTNAMES` 檢驗，順利取得 Token 並載入主頁設定。
- **實測截圖**：[`bible-site/screenshots-admin/A10_security_403.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A10_security_403.png)

---

### A11. 重新整理後台頁與權杖重新取得
- **判定結果**：**通過**
- **客觀數據**：
  - 於後台執行 `location.reload()` 重新整理。
  - 前端初始化時自動重新發出 `GET /api/token`，成功將新 Token 存入記憶體變數 `adminToken`。
  - 後續主頁設定 API（`GET /api/home`）及寫入操作均順利授權，狀態提示「`已載入目前設定。`」。
- **實測截圖**：[`bible-site/screenshots-admin/A11_reload_token.png`](file:///home/b827262/project/AI/Bible-Master/bible-site/screenshots-admin/A11_reload_token.png)

---

## 隔離清理與正式環境完整性確認

1. **行程停止**：測試結束後已停止測試前台（PID 2149882, Port 18190）與測試後台（PID 2149937, Port 18191），以及測試用 Chrome（PID 2150289）。
2. **暫存清理**：已完整刪除 `/tmp/agy-admin-test` 與 `/tmp/agy-chrome-profile` 暫存目錄。
3. **線上服務保護**：正式服務 `8090`（PID 1439868）與 `8091`（PID 1439888）全程持續在線，完全未受影響。
4. **程式碼與資料完整性**：未修改任何程式碼、未執行 `build_data`、未執行 `git commit` 或 `git push`；正式環境之 `bible-site/data/home.json` 與 `bible-site/site/assets/` 完全未被修改。
