# 「抽經文卡」視覺美化複審報告

- 複審時間：2026-11-03（Asia/Taipei）
- 範圍：任務 70–72（`site/style.css`、`site/blessing.html`、`tests/site_checks.py`、`tests/visual_checks.py`、`tests/blessing_probe.html`、`tests/visual_probe.html`）
- 設計依據：`bible-site/BLESSING-STYLE-REVIEW-PM.md`
- 複審者：Front-end Engineer（本會話）。**未修改任何檔案**（本報告除外）、未重啟 8090／8091、未 commit。
- 方法：`git diff` 逐行對照 ＋ 執行 `check_all.py`、`visual_checks.py` ＋ headless Chrome（每次獨立 `--user-data-dir`）實測五頁 × 320/375/768/1440 × 深淺色。
- 紅線確認：線上 8090（PID 1439868）／8091（PID 1439888）前後未變，皆回 200；`git log` 仍停在 `69d483a`，無新 commit；工作區 6 個檔案維持既有修改狀態，我未再動。

## 自動檢查結果

| 檢查 | 結果 |
|---|---|
| `python3 bible-site/tools/check_all.py` | **通過（3/3，exit 0）** |
| `python3 bible-site/tests/visual_checks.py` | **通過（全部，exit 0）** |

`site_checks.py` 的 `blessstyle` 9 項、`blessing` 8 項、`blessnav` 4 項、`blessindex` 1 項全部通過；`visual_checks.py` 新增的「導覽列目前頁不是實心色塊」與「blessing 畫布不顯示但畫好」在 4 種寬度都通過。

---

## 一、四個頁面的導覽列與目前頁辨識

| # | 項目 | 判定 | 證據（行號） |
|---|---|---|---|
| 1-1 | 導覽列目前頁改成透明底＋粗體＋3px 底線 | **通過** | `style.css` L100–106：`background: transparent; color: var(--accent); font-weight: 700; text-decoration: none; border-bottom: 3px solid var(--accent); border-radius: 0` |
| 1-2 | 實測：目錄／搜尋／經文卡片／抽經文卡四頁的 active 樣式 | **通過** | 四頁 active 皆 `bg=rgba(0,0,0,0)`、`color=rgb(122,74,31)`、`font-weight=700`、`border-bottom=3px`；**每頁只有 1 個 active**；未選中為 `rgb(44,43,40)`，對比清楚 |
| 1-3 | 導覽列在四頁都可正常運作（連結數、順序） | **通過** | 五頁皆 4 個連結（目錄／搜尋／經文卡片／抽經文卡），順序與 `app.js` L115–120 一致 |
| 1-4 | 目前頁對比（深淺色） | **通過** | 淺色 min **7.43:1**、深色 min **8.14:1**（40 組量測，全部 ≥4.5） |
| 1-5 | 逐章頁沒有 active 標示 | **通過（既有行為，非本次回歸）** | `chapter.html` L39 `Bible.nav("chapter.html")`，但 `app.js` L115–120 的 links 沒有 `chapter.html` 項目 → 不會有 active。`git show HEAD` 版本同樣如此，非本次改動造成。`visual_checks.py` 也已用 `if na is not None` 正確跳過此頁 |

## 二、blessing 下載 PNG 完整性

| # | 項目 | 判定 | 證據 |
|---|---|---|---|
| 2-1 | canvas 隱藏但仍在背景畫好 | **通過** | `blessing.html` L23 `#card-canvas { display: none; }`、L61 加 `hidden`；實測 `display=none`、`rectW=0`，但 `attrW=600`、`attrH=416`、`data-ref="馬太福音 25:21（和合本）"` |
| 2-2 | 下載 PNG 檔名與內容 | **通過** | 實測下載 `blessing-work-01.png`、78,521 bytes、600×416、PNG 檔頭 `89504e47`、與 `toDataURL` **逐位元組相同**、尺寸等於 canvas |
| 2-3 | 下載圖 `data-ref` 正確 | **通過** | `data-ref` = `.card-ref` = 「馬太福音 25:21（和合本）」 |
| 2-4 | 下載圖內框 2px `#e2d5be`、內縮 20px | **通過** | `blessing.html` L170–172；像素實測 (21,20) 與 (20,21) 皆為 `rgb(226,213,190)` |
| 2-5 | 下載圖底色 `#fbf7ee` | **通過** | L166；像素實測 (300,8) = `rgb(251,247,238)` |
| 2-6 | 經文用明體（serif） | **通過** | L150、L187 `"26px 'Songti TC', 'PMingLiU', serif"`；fillText 擷取到 `26px "Songti TC", PMingLiU, serif`，該字型只出現於經文段落 |
| 2-7 | 下載圖署名「—— 愛你的天父」靠右 | **通過** | L203–205；實測 `signText="—— 愛你的天父"`、`signColor=#7a4a1f`、右緣對齊（`W-pad-signWidth`） |
| 2-8 | 下載圖配色全部符合審查定案 | **通過** | 擷取到的顏色僅 4 種：`#7a4a1f`（標題／署名）、`#1f1e1b`（經文）、`#6e6659`（出處）、`#33312e`（短文），與 PM 文件 (B) 一致 |

## 三、分享、閱讀本章、再抽一次、主題切換

| # | 項目 | 判定 | 證據 |
|---|---|---|---|
| 3-1 | 分享 | **通過** | 實測 `navigator.share` 收到 `{title:"抽經文卡", url:"…/blessing.html?card=work-01"}` |
| 3-2 | 「閱讀本章 →」是可點連結、在卡片內、與出處同列 | **通過** | `blessing.html` L57–60 `.card-ref-row` 內 `<a id="read-link">閱讀本章 →</a>`；實測 `tag=A`、`href=chapter.html?book=mat&ch=25#v21`、`tabbable=true`、`inCard=true`、`sameRow=true`、`beforeActions=true` |
| 3-3 | 再抽一次（新版面下） | **通過** | 連按 5 次：`work-01→work-14→work-03→work-04→work-10→work-14`，**無連續同卡**、主題維持 work |
| 3-4 | 主題切換（新版面下） | **通過** | 從 work-14 點 rest → `rest-03`、`theme=rest`、標題「天父給你安息」、active 只有 rest、`card-ref` 與 `canvas data-ref` 相同 |
| 3-5 | 操作過程無 JS 錯誤 | **通過** | 所有實測段落 `Runtime.exceptionThrown` 與 console error 皆為 0 |

## 四、焦點外框、對比、44px 觸控

| # | 項目 | 判定 | 證據 |
|---|---|---|---|
| 4-1 | 鍵盤焦點外框（blessing，深淺色） | **通過** | Tab 走訪 12 個 stop（4 nav＋4 主題＋閱讀本章＋3 動作），**每個都是 `solid 2px`**、全部捲入畫面；深淺色一致 |
| 4-2 | 44px 觸控目標（375px） | **通過** | `again-btn` 301×44、`download-btn` 147×44、`share-btn` 147×44、`read-link` 87×44、4 個主題按鈕各 167×44 |
| 4-3 | 五頁 × 四寬度 × 深淺色水平溢出 | **通過** | 共 **40 組**，`scrollWidth ≤ innerWidth`、溢出元素 0，全數通過 |
| 4-4 | 深色模式卡片陰影與文字 | **通過** | `blessing.html` L28 深色加 `0 8px 24px rgba(0,0,0,.35)`；`--card-bg` 深色 `#28251f`；`visual_checks.py` 深色對比全過 |
| 4-5 | 卡片文字層次（PM 建議 3） | **通過** | 實測：標題 15px/600/accent、經文 19px/500/明體/fg、出處 14px/400/muted、短文 16.5px/400/fg、署名 15px/600/accent —— 層次分明 |

## 五、新加檢查本身的漏洞

| # | 漏洞 | 判定 | 說明與建議 |
|---|---|---|---|
| 5-1 | `--grep` 無匹配時仍「全部通過」且 exit 0 | **不通過** | `site_checks.py` L19–20 在 `ONLY` 不匹配時直接 `return`，`results` 為空；L392 `all([])` 為 True → 印「結果：全部通過」、`sys.exit(0)`。**實測**：`python3 bible-site/tests/site_checks.py blessing --grep 'zzz不存在zzz'` → 「結果：全部通過」、exit 0。<br>**影響**：驗收時 regex 打錯字（或檢查被改名）會靜默通過，是最容易被誤信的假陽性。<br>**建議修法**：在 `if __name__ == "__main__"` 結尾加 `if not results: print("不通過：--grep 沒有匹配任何檢查"); sys.exit(1)`（`visual_checks.py` 有同樣寫法，可一併檢查）。 |
| 5-2 | `blessstyle` 的 2×2 等寬檢查只在單一寬度（1280）量 | **不通過** | `site_checks.py` L173 用 `blessing_state(port, "blessing.html?card=work-01")`，未帶寬度參數，等同只用預設視窗。因此 **320px 的欄寬不等問題（見 6-1）不會被這項檢查抓到**。<br>**建議修法**：`blessing_probe.html` 接受寬度參數，`blessing_style` 至少在 320 與 1280 各量一次 2×2 等寬。 |
| 5-3 | canvas 檢查只驗 `attrW` 與 `data-ref`，未驗實際有無畫上內容 | **需人工（低風險）** | `visual_checks.py` L129 檢查 `attrW>=600`、`shownW==0`、`ref.startswith("馬太福音 25:21")`。若 `drawCanvas` 只設 `data-ref` 而沒真正填色，仍會通過。<br>本次我另外量了像素（底色、內框）與 `toDataURL` 長度（104,718 字元）確認實際有內容，故不影響本次結論。建議未來加一項「canvas 非空白」檢查（如取樣 4 個角與中央的像素）。 |
| 5-4 | `blessing_probe.html` 的 `ids` 在 theme 點擊時不等待（L53 `if (!a.click.includes("btn")) break`） | **通過** | 這是刻意設計（主題標籤在封面時不抽卡），非漏洞；`blessstyle` 需要的資料由 `read()` 另外提供 |
| 5-5 | 新增的 `navActive` 檢查在 `chapter.html` 會是 `None` | **通過** | `visual_checks.py` L98 `if na is not None` 正確跳過，不會誤判 |

## 六、不通過項（附重現步驟與建議修法）

### 6-1【不通過】320px 下主題按鈕不是等寬 2×2（153px ／ 125px）

- **位置**：`bible-site/site/blessing.html` L10
  ```css
  #theme-tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; ... }
  ```
  搭配 L11 `white-space: nowrap;`
- **重現步驟**：
  1. 以 headless Chrome 開 `http://127.0.0.1:8090/site/blessing.html?card=work-01`
  2. 視窗寬度設 320px（`Emulation.setDeviceMetricsOverride` 或實機 320 寬）
  3. 量測 `#theme-tabs` 的 `gridTemplateColumns` 與四顆按鈕寬度
- **實際結果**：
  ```
  grid-template-columns: 153px 125px   （容器 288px）
  work   x=16  y=162.8  w=153
  peace  x=179 y=162.8  w=125
  rest   x=16  y=216.8  w=153
  faith  x=179 y=216.8  w=125
  ```
  兩欄寬度不同（153／125），視覺上左右不對齊。375px（166.5／166.5）與 768px（283／283）都正常。
- **原因**：`1fr` 的最小值預設是 `auto`，而 `white-space: nowrap` 讓「天父賜福你的工作」的最小內容寬約 120px＋左右內距 ≈ 137px，撐大了第一欄。
- **判定理由**：任務 72 與 PM 文件 (C) 要求「2×2 grid、等寬」；`site_checks.py` 的等寬檢查（L173）只在 1280px 量，所以自動檢查沒抓到（見 5-2）。
- **影響**：僅 320px 寬（iPhone SE 直向等）出現；文字未裁切、無水平溢出，屬外觀瑕疵。
- **建議修法**（二選一，需實測確認）：
  1. `grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)` → 實測兩欄變 **139px / 139px**，但「天父賜福你的工作」會 `scrollWidth > clientWidth`（文字溢出按鈕），需同時把該按鈕 `white-space: normal` 或字級降到 14px、內距收窄。
  2. 保留 `1fr 1fr` 但對 `#theme-tabs button` 加 `min-width: 0; overflow: hidden; text-overflow: ellipsis;`，接受 320px 時長標題以省略號呈現。
  
  建議採 1 ＋ 短標題（或 `white-space: normal` 允許兩行），並把 320px 納入 `blessstyle` 的等寬檢查。

---

## 七、需人工

| # | 項目 | 原因 |
|---|---|---|
| 7-1 | 卡片整體視覺美感（14px 圓角、4px 頂線、陰影強度、明體在實機的顯示） | 主觀判斷。客觀數值（字級、顏色、對比、間距、圓角）皆符合 PM 文件；已用 375px 深淺色截圖確認示意。 |
| 7-2 | 真機 `navigator.share` 原生面板與剪貼簿提示外觀 | headless 只能驗 API 行為與訊息文字（已驗通過），真機 UI 無法確認。 |
| 7-3 | 「天父賜福你的工作」在 320px 的最佳取捨（等寬但換行／省略號／降字級） | 屬設計決策，需 PM 決定採哪一種；技術上三種都可行（見 6-1 建議）。 |

---

## 八、結論

| 分類 | 數量 |
|---|---|
| 通過 | 24 |
| 不通過 | 3（6-1 320px 不等寬；5-1 `--grep` 假陽性；5-2 2×2 檢查未涵蓋 320px） |
| 需人工 | 3 |

**整體評價**：任務 70–72 的主體改動品質良好——配色變數、導覽列、`.btn-secondary`、卡片版面、canvas 隱藏與匯出配色全部符合 PM 文件；`check_all.py` 3/3、`visual_checks.py` 全過；我另外做的 40 組（五頁×四寬度×深淺色）溢出量測、下載 PNG 逐位元組比對、canvas 像素取樣、12 個焦點 stop、8 個觸控目標，全部通過，且無任何 JS 錯誤。

需要處理的是**兩處檢查盲點**（5-1 `--grep` 空結果假陽性、5-2 等寬檢查只量 1280px）與**它們掩蓋的一個 320px 外觀瑕疵**（6-1）。三者中，5-1 的影響最大：它會讓任何用 `--grep` 的驗收在打錯 regex 時靜默通過。

總計：通過 24 項、不通過 3 項、需人工 3 項（共 30 項）。

---

## 處理紀錄（PM，複審後）

| # | 處理 |
|---|---|
| 5-1 | `site_checks.py`、`visual_checks.py` 結尾加判斷：有 `--grep` 但沒有對到任何檢查，就記一項不通過。實測：打錯的 regex 兩支都回傳 exit 1。 |
| 5-2 | `blessing_probe.html` 支援 `?w=<px>` 設定 iframe 寬度。`blessstyle` 的 2×2 檢查改在 320、375、1000px 各量一次，並多檢查「等高」和「文字沒有被裁切」（`scrollWidth > clientWidth`）。改完先跑，確認 320px 不通過。 |
| 5-3 | 採用。probe 讀 canvas 像素，檢查改成「角落是底色 #fbf7ee、深色像素 > 500」。實測深色像素 12010 個。 |
| 6-1 | `#theme-tabs` 改成 `minmax(0, 1fr) minmax(0, 1fr)`。只對 < 360px 加 `grid-auto-rows: 1fr`，按鈕允許換行、圓角 16px，最長的「天父賜福你的工作」在 320px 會折成兩行。四顆都是 132×53px，等寬等高、不裁切。375px 以上維持單行膠囊，不受影響。7-3 的取捨由此定案：等寬並允許換行。 |

複驗：`check_all.py` 3/3；`visual_checks.py` 全部通過；`site_checks.py`（含 blessstyle 三種寬度）全部通過。
