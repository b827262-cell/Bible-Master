# 110b 最終複審：區域音樂與收藏卡圖

**狀態：PASS**

## 結論

三項指定檢查全部通過，另外兩次單獨重跑 `zonemusic` 也全綠。區域音樂續播／換曲、單卡收藏圖與靜態發佈的實際瀏覽器及建置路徑均有動態測試；本次未發現中度以上缺陷。僅有一項低風險的瀏覽器測試覆蓋缺口，詳見下方。

## 問題與剩餘風險

### 低｜`blessing` 分區自訂曲尚未在獨立瀏覽器案例中單獨驗證

- `tests/site_checks.py:642-665` 的獨立分區案例為 `index`、`search`、`card` 配置三首不同曲，`blessing` 刻意省略以驗證沿用共用曲；服務測試 `tests/service_checks.py:356-364` 驗證 `blessing` 欄位可保存，但各分區使用同一檔名。
- 因此目前能抓出前三個區的鍵值對調及缺省回退錯誤；若只有 `zones.blessing` 的前台取值錯誤，合成瀏覽器案例未必會發現。程式以頁面鍵查找分區曲目，位置在 `site/music.js:165-183`。
- 建議補一個 `zones.blessing` 使用獨立曲目的瀏覽器案例。這是測試覆蓋建議，未阻擋目前 PASS。

## 複審核對

- **測試伺服器 Range 與續播等待：**`tests/site_checks.py:540-584` 的 `RangeHandler` 對合法單一 byte range 回 206、剪裁超出檔尾的 end、對無效範圍回 416，並限制回傳長度；路徑仍由標準 `translate_path` 處理。`tests/zone_probe.html:57-68` 僅在前後曲目相同時最多等 6 秒，換曲立即取樣。等待迴圈本身不設定 `currentTime`，所以不會直接替產品程式補做續播。
- **續播缺陷突變驗證：**在暫存副本把 `music.js` 的同曲 seek 條件改為永不成立，再跑 `site_checks.py zonemusic`，共 5 項續播檢查失敗；突變檔只存在暫存目錄。這支持等待條件能抓到目前環境下的「只續播狀態、未恢復時間」缺陷。正常版本全套檢查通過。
- **區域音樂：**舊格式 `{music}`、缺少設定的預設曲、分區自訂與缺省共用均有覆蓋。新測試以不同曲目驗證 `index`、`search`、`card` 實際來源，另有兩區同曲續播與跨曲歸零案例。`zone_probe` 使用 Range 支援的本機伺服器，檢查實際 audio 狀態、`sessionStorage`、切頁續播／換曲、按鈕狀態及 44×44 觸控尺寸。
- **收藏卡圖片：**測試驗證單卡圖優先於主題圖、其他同主題卡回退主題圖、無圖維持純文字，以及原圖下載位元組相同；建置測試以暫存站點建置並透過靜態伺服器確認設定引用的主題圖／單卡圖會收錄，未引用的上傳素材不會收錄。
- **寫入端點：**沿用上一輪程式碼核對結論；目前程式未再變更。服務檢查通過 `check_write_auth`、Host／Origin／token、路徑白名單與 `..`、副檔名／存在性、body 上限、驗證失敗不寫檔、原子寫入及 POST 400／403／413。主要程式位置：`admin/server.py:215-229,298-404,632-683,773-873`。
- **資料與前台：**沿用上一輪對未變更程式的核對結論；檢查確認 home 設定六欄、祝福卡 37 張凍結、舊 `zone-music.json`／`blessing-art.json` 相容、四卷經文 JSON 位元組不變。經文未寫死、沒有外部資源、a11y／手勢／播放狀態檢查通過。單卡圖 fallback 與下載實作位於 `site/blessing.html:218-230,361-386`。
- **發佈：**`tools/build_public.py:54-101` 收集主頁、分區音樂、主題與單卡設定引用的資產；`deploy_checks.py` 建置到暫存目錄並測靜態回應，未部署。

## Checks

- `python3 bible-site/tools/check_all.py`：通過，3/3。
- `python3 bible-site/tests/service_checks.py zoneadmin blessartadmin homeadmin admin`：通過。
- `python3 bible-site/tests/deploy_checks.py`：通過。
- `python3 bible-site/tests/site_checks.py zonemusic`：額外連跑兩次，均通過。
- `grep -Eq '^\*\*狀態：(PASS|FAIL)\*\*' bible-site/REVIEW-zone-art.md`：通過。

## 範圍與保全

- 執行前依 `git diff --name-only` 核對：允許清單中的六個程式檔原本已有變更；同時也有清單外的既有變更及未追蹤測試／任務、資料、素材與 `output/`。它們不是本輪修改。本輪只重寫此允許清單內的審查報告，未改動 `tests/`。
- 指定指令在目前工作樹執行。`check_all.py` 會寫 `TEST-REPORT.md`、`FAILS.md`，兩檔執行後已還原原有位元組、權限及時間；`deploy_checks.py` 的 Python bytecode 寫入導向暫存目錄。經文 JSON、`home.json`、`blessing.json`、`chapter.html`、`zone-music.json`、`blessing-art.json`、禱讀資料、既有音樂測試證據、Spark 角色設定及輸出目錄均未改動。
- 未下載或引入外部資源；未執行 commit、push 或部署。
