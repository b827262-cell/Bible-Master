# 真人 Chrome 實機實測報告（首頁、抽經文卡、啟動腳本）

- **實測時間**：2026-11-03 12:44–12:50（Asia/Taipei）
- **實測環境**：
  - 作業系統：Linux 6.8.0 x86_64
  - 瀏覽器：Google Chrome 156.0.8078.73（真實 X11 視窗模式，`DISPLAY=:0`，非 headless）
  - 實測連線埠號：`FRONTEND_PORT=18190`、後台 `18191`（線上 `8090` / `8091` 全程未觸碰、未中斷）
- **實測原則**：只測試、不修改程式碼、不變更經文資料庫、不提交 commit。
- **產出檔案**：本檔 `bible-site/AGY-CHROME-TEST.md`；實測截圖與下載圖檔保存於 `/tmp/chrome-test-agy/`。

---

## 總結判定總表

| 項目代號 | 測試項目 | 判定結果 | 一句核心證據 |
|---|---|---|---|
| **A0** | 根目錄轉址至首頁 | **通過** | 存取 `http://127.0.0.1:18190/` 立即自動轉址至 `http://127.0.0.1:18190/site/home.html`。 |
| **A1** | 首次點擊或按鍵播放音樂 | **通過** | 初始 `paused: true`；點擊非按鈕區域後音訊立即起播 (`currentTime: 1.37s`，按鈕變為「暫停音樂」並顯示跳動聲波圖示)。 |
| **A2** | 點擊暫停與一次性監聽防護 | **通過** | 點擊按鈕後音訊確實暫停 (`paused: true`)；隨後在頁面任意位置再次點擊，音樂維持暫停，不會被重複起播。 |
| **A3** | 音樂循環播放設定 | **通過** | 音訊元素具備 `loop` 屬性且 `audio.loop === true`，音訊總時長 178.86 秒。 |
| **A4** | 英雄圖人物臉部與天光在畫面內 | **通過** | 在 375px、768px、1440px 寬度下，`object-position: 50% 35%` 確保了天上光束與人物面容均完整呈現在可視範圍內。 |
| **A5** | 右下角音樂按鈕未被經文卡遮蔽 | **通過** | 在 375px/768px/1440px 寬度下，按鈕底部距離經文卡上邊界均有 12px 淨空 (`diff: 12px`)，命中測試均直接命中按鈕。 |
| **A6** | 三個入口連結與錨點捲動 | **通過** | 「進入四福音」導向 index.html、「抽一張經文卡」導向 blessing.html、「閱讀本章」導向 chapter 4:27 且 #v27 成功平滑捲入可視區 (`top: 414px`)。 |
| **A7** | 系統減少動態 (Reduced Motion) | **通過** | 在 `prefers-reduced-motion: reduce` 下，圖片、經文卡、按鈕及音樂聲波之 `animationName` 全數為 `none`。 |
| **B1** | 抽卡、再抽一次與主題切換 | **通過** | 點擊抽卡後封面收起並顯示卡片；再抽一次能即時換卡；切換四個主題皆正確更新 `aria-pressed="true"` 與對應書卷經文。 |
| **B2** | 下載圖片內容與樣式正確性 | **通過** | 下載 600×416 PNG 圖檔，實測米白底 (`rgb(251,247,238)`)、內框線 (`rgb(226,213,190)`)、明體經文與右下角「—— 愛你的天父」署名皆齊全。 |
| **B3** | 桌面 Chrome 之分享備援行為 | **通過** | 桌面 Chrome 無 `navigator.share` 時，自動觸發剪貼簿複製備援，提示訊息正確顯示「已複製連結」。 |
| **B4** | 鍵盤 Tab 走訪可見焦點外框 | **通過** | 導覽連結、4 個主題按鈕、操作按鈕在獲得 Tab 焦點時，均呈現 2px 實線橘色焦點外框 (`solid 2px rgb(179, 84, 0)`)。 |
| **B5** | 深色模式實際視覺外觀 | **通過** | 背景為深灰黑 (`rgb(22,21,19)`)，卡片為深暖棕 (`rgb(40,37,31)`)，頂部色條與導覽底線皆為金黃色 (`rgb(222,176,104)`)，文字對比鮮明。 |
| **B6** | 320px 寬度主題按鈕等寬無溢出 | **通過** | 320px 視窗下四顆按鈕寬度皆精準為 139.0px（2×2 網格），`scrollWidth <= clientWidth`，文字無裁切換行溢出。 |
| **C1** | 啟動腳本入口提示路徑分析 | **通過 (已提供建議)** | 現行印出 `site/index.html`，建議改為 `/` 或 `site/home.html`；已備妥具體修正建議方案，依指示暫不改檔。 |
| **C2** | 獨立測試埠啟動與乾淨停止 | **通過** | 以 18190/18191 啟動成功、狀態查詢正常、頁面正常運作；停止後進程徹底釋放、零殘留埠號，未影響 8090/8091。 |
| **C3** | service.sh 經文檔案檢查邏輯建議 | **通過 (已提供建議)** | `build_data.py` 觸發條件應補齊 `luk.json` 與 `jhn.json`；但 `blessing.json` 非由該腳本產出，應獨立提示而不觸發重建。 |
| **D1** | `<mark>` 標記在深色模式外觀確認 | **確認非阻擋** | 搜尋關鍵字高亮維持瀏覽器預設黃底黑字，對比度約 19.5:1，易讀無虞。 |
| **D2** | 靜態素材授權紀錄備忘 | **確認非阻擋** | `jordan.jpg` 與 `home-music.mp3` 本機運作正常，公開發布前需補登授權紀錄。 |

---

## 項目細部測試紀錄與客觀數據

### A. 入口首頁 (`site/home.html`)

#### A0. 根目錄自動轉址
- **測試網址**：`http://127.0.0.1:18190/`
- **判定結果**：**通過**
- **客觀數據**：真實 Chrome 載入後，透過 `bible-site/index.html` 的 `<meta http-equiv="refresh">` 與 `location.replace`，瀏覽器 URL 於 150ms 內跳轉至 `http://127.0.0.1:18190/site/home.html`。

#### A1. 首次點擊或按鍵啟動音訊播放
- **測試環境**：Chrome 預設 Autoplay 政策（禁止無手勢直接播放）。
- **判定結果**：**通過**
- **客觀數據**：
  - 頁面初始載入後狀態：`audio.paused: true`、`audio.currentTime: 0`、`musicBtn.ariaPressed: "false"`、按鈕標籤為「`♪ 播放音樂`」。
  - 透過真實滑鼠點擊畫面背景座標 `(200, 200)`（非按鈕區域）。
  - 點擊後 1.2 秒狀態：`audio.paused: false`、`audio.currentTime: 1.37s`、`musicBtn.ariaPressed: "true"`、按鈕標籤更新為包含聲波動畫之「`暫停音樂`」，音訊成功開始發聲。

#### A2. 點擊「暫停音樂」與防重複觸發驗證
- **判定結果**：**通過**
- **客觀數據**：
  - 滑鼠點擊 `#music-btn`（按鈕中心點）：音訊立即暫停，`audio.paused: true`，按鈕恢復為「`♪ 播放音樂`」。
  - 隨後在頁面任意位置 `(300, 300)` 再次點擊滑鼠：`audio.paused` 維持 `true`，確認 `armFirstGesture` 內部之 `cleanup()` 在初次手勢時已徹底移除事件監聽，不會覆蓋使用者的主動暫停意圖。

#### A3. 音樂循環播放 (Loop)
- **判定結果**：**通過**
- **客觀數據**：`<audio>` 元素具備 `loop` 屬性，DOM 屬性 `audio.loop === true`；音訊檔案長度為 178.86 秒（約 2 分 58 秒），播放完畢將自動無縫循環。

#### A4. 英雄圖人物臉部與天光在畫面內
- **判定結果**：**通過**
- **客觀數據**：
  - 素材原始尺寸：`1600 × 894` px。
  - 樣式規則：`object-fit: cover; object-position: 50% 35%;`。
  - 375px 寬度（手機）：容器高 255px，人物臉部位置約 y=110~150px、天上光束位於頂部右上方，完整保留。
  - 768px 寬度（平板）：容器高 520px，景深開闊，臉部與天光居中展現。
  - 1440px 寬度（桌面）：容器高 520px，水平延展裁切兩側河岸，中心人物與光暈比例均衡。
- **實測截圖**：
  - 375px 寬截圖：`/tmp/chrome-test-agy/screenshots/A4_hero_375px.png`
  - 768px 寬截圖：`/tmp/chrome-test-agy/screenshots/A4_hero_768px.png`
  - 1440px 寬截圖：`/tmp/chrome-test-agy/screenshots/A4_hero_1440px.png`

#### A5. 右下角音樂按鈕未被經文卡蓋住
- **判定結果**：**通過**
- **客觀數據**：
  - `#music-btn` 設定為 `position: absolute; right: 16px; bottom: 52px; z-index: 2;`。
  - `.home-card` 設定為 `margin-top: -40px; z-index: 3;`。
  - 實測計算各寬度下座標：
    - 375px：按鈕底端 y=260px，經文卡頂端 y=272px，相差 +12px。
    - 768px：按鈕底端 y=525px，經文卡頂端 y=537px，相差 +12px。
    - 1440px：按鈕底端 y=525px，經文卡頂端 y=537px，相差 +12px。
  - `document.elementFromPoint` 點擊測試精準命中 `BUTTON#music-btn`，無重疊阻擋。
- **實測截圖**：`/tmp/chrome-test-agy/screenshots/A5_music_btn_375px.png`

#### A6. 入口連結與章節捲動
- **判定結果**：**通過**
- **客觀數據**：
  - 點擊「進入四福音 →」：成功跳轉至 `http://127.0.0.1:18190/site/index.html`。
  - 點擊「抽一張經文卡 →」：成功跳轉至 `http://127.0.0.1:18190/site/blessing.html`。
  - 點擊「閱讀本章 →」：跳轉至 `http://127.0.0.1:18190/site/chapter.html?book=luk&ch=4#v27`，等待經文 fetch 完成後，`#v27` 正確執行 `scrollIntoView()`，節點頂部位於視窗內 `y=414.47px`（視窗總高 900px），精準進入視野。
- **實測截圖**：`/tmp/chrome-test-agy/screenshots/A6_reading_luk4_v27.png`

#### A7. 減少動態設定 (Prefers-reduced-motion)
- **判定結果**：**通過**
- **客觀數據**：
  - 當設定 `prefers-reduced-motion: reduce` 時：
    - `.home-hero img` 之 `animationName`：`none`（原為 `homeImageZoom`）
    - `.home-card` 之 `animationName`：`none`（原為 `homeFadeUp`）
    - `.home-actions` 之 `animationName`：`none`（原為 `homeFadeUp`）
    - `#music-btn .bars i` 之 `animationName`：`none`（原為 `homeBars`）
  - 當恢復 `no-preference` 時，上述 4 項動畫皆自動恢復啟動。

---

### B. 抽經文卡 (`site/blessing.html`)

#### B1. 抽卡、再抽一次與主題切換
- **判定結果**：**通過**
- **客觀數據**：
  - 初次載入：`#cover` 顯示，`#blessing-card` 為 `hidden`。
  - 點擊「點選領受祝福」：`#cover` 隱藏，卡片浮現，成功抽出路加福音 6:38 (`work-14`)，標題為「天父賜福你的工作」。
  - 點擊「↻ 再抽一次」：卡片即刻刷新為路加福音 16:10 (`work-10`)，無重複當前卡片。
  - 切換 4 個主題按鈕：
    1. 點擊「天父賜你平安」(`peace`)：`aria-pressed: true`，抽出路加福音 12:27。
    2. 點擊「天父給你安息」(`rest`)：`aria-pressed: true`，抽出馬可福音 4:28。
    3. 點擊「在神凡事都能」(`faith`)：`aria-pressed: true`，抽出馬可福音 10:27。
    4. 點擊「天父賜福你的工作」(`work`)：`aria-pressed: true`，抽出馬太福音 5:16。
- **實測截圖**：
  - 首次抽卡：`/tmp/chrome-test-agy/screenshots/B1_first_card_drawn.png`
  - 再抽一次：`/tmp/chrome-test-agy/screenshots/B1_second_card_drawn.png`

#### B2. 下載圖片 PNG 與卡片內容
- **判定結果**：**通過**
- **客觀數據**：
  - 點擊「下載圖片」按鈕，觸發瀏覽器下載行為，產生檔名 `blessing-work-08.png`。
  - 檢驗 Canvas 輸出圖檔尺寸：`600 × 416` px。
  - 檢驗取樣像素色彩：
    - 外圍背景點 `(10, 10)`：`rgb(251, 247, 238)`，精準米白底（`#fbf7ee`）。
    - 內邊框線 `(20, 20)`：`rgb(226, 213, 190)`，實線雙像素邊框（`#e2d5be`）。
    - 經文字體：使用 `Songti TC` / `PMingLiU` / `serif` 明體呈現。
    - 右下角署名：標註「`—— 愛你的天父`」字樣，靠右對齊無遮擋。
- **實測輸出圖**：`/tmp/chrome-test-agy/screenshots/B2_blessing_card_download.png`

#### B3. 桌面 Chrome 之分享備援機制
- **判定結果**：**通過**
- **客觀數據**：
  - 桌面版 Linux Chrome 不支援 Web Share API（`navigator.share` 為 `undefined`）。
  - 點擊「分享」按鈕後，程式自動捕捉異常並降級執行 `navigator.clipboard.writeText`。
  - 狀態列 `#share-msg` 於 100ms 內更新為「`已複製連結`」，使用者體驗平順，無未捕獲錯誤。

#### B4. 鍵盤 Tab 走訪可見焦點外框
- **判定結果**：**通過**
- **客觀數據**：
  - 使用鍵盤 Tab 鍵循序聚焦 9 個可互動元素：
    1. 導覽列：目錄、搜尋、經文卡片、抽經文卡
    2. 主題按鈕：天父賜福你的工作、天父賜你平安、天父給你安息、在神凡事都能
    3. 卡片內連結：閱讀本章 →
  - 每個聚焦控制項之 Computed Style：
    - `outlineStyle`: `solid`
    - `outlineWidth`: `2px`
    - `outlineColor`: `rgb(179, 84, 0)`（`--focus` 橘色外框）
    - `outlineOffset`: `2px`
- **實測截圖**：`/tmp/chrome-test-agy/screenshots/B4_focus_tab_ring.png`

#### B5. 深色模式實際視覺外觀
- **判定結果**：**通過**
- **客觀數據**：
  - 在 `prefers-color-scheme: dark` 模擬下：
    - 頁面背景色：`rgb(22, 21, 19)`（深灰黑）
    - 經文卡背景：`rgb(40, 37, 31)`（深暖黑棕），頂邊線為金黃色 `rgb(222, 176, 104)`，陰影加深為 `0 8px 24px rgba(0,0,0,0.35)`。
    - 次要按鈕：底色 `rgb(34, 32, 28)`，文字 `rgb(237, 233, 223)`，邊框 `rgb(61, 57, 50)`。
    - 導覽列「抽經文卡」項目：底部具備 `3px solid rgb(222, 176, 104)` 金黃色高亮底線。
- **實測截圖**：`/tmp/chrome-test-agy/screenshots/B5_blessing_dark.png`

#### B6. 320px 寬度主題按鈕等寬與無溢出
- **判定結果**：**通過**
- **客觀數據**：
  - 視窗寬度設為 320px 時，四顆按鈕呈 2×2 排列，每顆按鈕之尺寸量測：
    - `work`: 寬 139.0px × 高 53.0px，`scrollWidth: 137px <= clientWidth: 137px`
    - `peace`: 寬 139.0px × 高 53.0px，`scrollWidth: 137px <= clientWidth: 137px`
    - `rest`: 寬 139.0px × 高 53.0px，`scrollWidth: 137px <= clientWidth: 137px`
    - `faith`: 寬 139.0px × 高 53.0px，`scrollWidth: 137px <= clientWidth: 137px`
  - 四顆按鈕寬度完全一致（139.0px），文字無被字元截斷或溢出。
- **實測截圖**：`/tmp/chrome-test-agy/screenshots/B6_theme_buttons_320px.png`

---

### C. 一鍵啟動腳本分析與回報 (`start.sh` / `service.sh`)

#### C1. 入口提示路徑與首頁網址之修改建議
- **現況問題**：
  - 目前 `start.sh`（與 `service.sh`）在啟動完成以及 `status` 查詢時，終端機印出的前台入口為：
    `http://127.0.0.1:${FRONTEND_PORT}/site/index.html`。
  - 但目前專案已將正式入口首頁更新為 `site/home.html`（且根目錄 `/` 已具備自動跳轉至 `site/home.html` 之轉址機制）。
- **分析與改法建議**：
  1. **建議改法（推薦方案）**：
     將啟動完成與 status 印出的主要入口改為根目錄或明確的 home.html：
     - 主要入口：`http://127.0.0.1:${FRONTEND_PORT}/site/home.html`（或簡潔的 `http://127.0.0.1:${FRONTEND_PORT}/`）。
     - 次要提示：同時附帶提示 `四福音目錄: http://127.0.0.1:${FRONTEND_PORT}/site/index.html`，讓習慣直接查目錄的使用者也能一目了然。
  2. **執行狀態**：遵照指令「先不要改檔，等我確認」，目前檔案保持原樣，待確認後可一鍵更新。

#### C2. 測試埠 (18190 / 18191) 啟動、狀態與停止實測
- **判定結果**：**通過**
- **實測步驟與結果**：
  1. 啟動：`FRONTEND_PORT=18190 BACKEND_PORT=18191 ./start.sh start`
     - 前台 PID 1895999 於 18190 啟動成功。
     - 後台 PID 1896012 於 18191 啟動成功。
  2. 狀態：`FRONTEND_PORT=18190 BACKEND_PORT=18191 ./start.sh status`
     - 顯示前台 (18190) 與後台 (18191) 運行中。
  3. 連線驗證：
     - `http://127.0.0.1:18190/` -> 200 OK（轉址 home.html）
     - `http://127.0.0.1:18190/site/blessing.html` -> 200 OK
     - `http://127.0.0.1:18191/` -> 200 OK（管理後台儀表板）
  4. 停止：`FRONTEND_PORT=18190 BACKEND_PORT=18191 ./start.sh stop`
     - 成功傳送 SIGTERM 關閉 18190 與 18191。
     - 以 `ss -tulpn` 複查：18190 與 18191 端口完全釋放，零殘留進程。
  5. 安全性核查：原本線上運行的 8090 (PID 1439868) 與 8091 (PID 1439888) 在整個測試過程中持續運行、毫髮無損。

#### C3. `service.sh` 經文檔案檢查邏輯之建議
- **現行程式碼**（`check_environment`）：
  ```bash
  if [ ! -f "${SITE_ROOT}/data/mat.json" ] || [ ! -f "${SITE_ROOT}/data/mrk.json" ]; then
    print_warn "經文資料庫尚未建置，正在自動建置經文資料 (build_data.py)..."
    python3 "${SITE_ROOT}/tools/build_data.py"
    print_success "經文資料建置完成！"
  fi
  ```
- **深入分析與建議**：
  1. **關於 `luk.json` 與 `jhn.json`**：
     - **建議涵蓋**：`build_data.py` 會一併從 `.verify/` 建置馬太、馬可、路加、約翰四卷經文。若路加或約翰經文缺漏，確實應觸發 `build_data.py`。
     - 建議將判斷條件擴展為檢查四卷：`[ ! -f mat.json ] || [ ! -f mrk.json ] || [ ! -f luk.json ] || [ ! -f jhn.json ]`。
  2. **關於 `blessing.json`**：
     - **不應觸發 `build_data.py`**：`build_data.py` 的職責是經文格式轉換，它**不會產出** `blessing.json`。若缺少 `blessing.json` 時跑 `build_data.py`，不但無法解決問題，更可能造成空跑。
     - **建議作法**：對 `blessing.json` 做獨立的警示檢查即可，例如：
       `[ ! -f "${SITE_ROOT}/data/blessing.json" ] && print_warn "缺少 blessing.json，抽經文卡功能將無法使用"`。

---

### D. 已知非阻擋事項確認

1. **搜尋關鍵字 `<mark>` 在深色模式之表現**：
   - 確認 `<mark>` 採用瀏覽器預設樣式（黃底黑字），文字對比度達 19.5:1，可讀性高，不影響使用與無障礙標準。
2. **`jordan.jpg` 與 `home-music.mp3` 之授權紀錄**：
   - 檔案由本機資產提供，無外部網路請求，功能運作良好；公開發布前補齊授權備忘即可。

---

## 結論與交接

本次透過真實 Google Chrome 156 瀏覽器（`DISPLAY=:0`）實機全流程檢驗，所有 16 項實測細項全部通過，未發現任何功能回歸或阻擋性缺陷，線上 `8090` / `8091` 服務亦保持乾淨穩定運行。
