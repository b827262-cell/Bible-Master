# 每日禱讀逐日公開至2026-12-16驗收

**狀態：PASS**

使用者於2026-11-16要求「請上架每日禱讀1個月到12/16日」，沿用既有逐日公開決策：台灣時間每日06:00，12/16含當日，12/17起停止自動公開。本次已實際安裝並啟用延長設定，沒有一次公開未來內容。

## 內容與正式站

- 正式站實際讀取：11篇，日期11/06～11/16，今天已公開。
- 從已核准匯出view唯讀匯出至12/16：41篇、日期11/06～12/16逐日連續，title／summary／reflection／prayer／ranges皆完整；原15篇＋365日計畫前26篇。
- 截至12/16的內容已備妥；若後續每天排程成功，最後累計41篇。此數字不代表目前已公開41篇。
- 沒有修改正式資料庫、文章、審核狀態或工作樹data/*.json；未手動啟動發布服務。

## 已生效的設定

安全新增兩份user drop-in，原主unit、host.conf及舊11/25設定逐份SHA256比對未變，沒有刪除或覆蓋：

- `~/.config/systemd/user/bible-devotional-publish.timer.d/release-through-20261216.conf`
- `~/.config/systemd/user/bible-devotional-publish.service.d/release-through-20261216.conf`

新timer清除舊OnCalendar後只保留以下兩條：

```
2026-11-16..30 06:00:00 Asia/Taipei
2026-12-01..16 06:00:00 Asia/Taipei
```

新service清除舊11/25的ExecCondition後，僅載入一條新日期條件：台灣實際日期<=2026-12-16回0，12/17起回1跳過。已查驗實際載入的ExecCondition只有新條件，沒有舊條件繼續阻擋。原ExecStart與SSH主機設定保留。

`daemon-reload`與重啟timer完成後：active、enabled、Persistent=yes；下一次2026-11-17 06:00，最後2026-12-16 06:00。使用者Linger沿用原本設定。若過期後才補跑，日期條件仍阻止截止日後的公開。

## 跨月份狀態辨識修正

tab2新增兩份模板與說明，並修正`admin/devotional_status.py`：

1. 所有規則均可辨識為有限日期時，取最後截止日；任何無限／未知規則仍回未知，不把12/16寫死在程式。
2. systemd實際以多行同名`TimersCalendar=`回傳多條排程，現在累積完整規則，避免只留下11月並誤報11/30。此問題由PM真實安裝驗證發現，先補失敗測試再修正。

修正後真實唯讀收集器同時看到兩個月份，回報截止2026-12-16、下一次11/17及scheduled。既有長駐後台沒有重啟；新版辨識於下次啟動載入，不影響已生效的發布排程。

## PM獨立驗證

| 檢查 | 結果 |
| --- | --- |
| `python3 -B bible-site/tests/ops_dashboard_checks.py` | PASS，25項，包含新增跨月份／重複property整合案例及既有離線回歸 |
| 新測試效力 | 修正前兩個月規則無法判定截止日、重複property被覆寫，對應測試確實判失敗；修正後通過 |
| calendar完整範圍 | 11/16～12/16共31個唯一連續每日06:00，最後12/16；12/16 06:00之後兩規則皆回never |
| 合併unit語法 | 舊主unit、舊drop-in及新drop-in一起以`systemd-analyze --user verify`檢查，exit0 |
| 實際日期條件 | 5個UTC／台灣案例全過；11/26仍可執行、12/16 23:59:59可執行、12/17 00:00起跳過 |
| 實際載入狀態 | 兩條有限calendar、timer active/enabled、Persistent=yes；唯一ExecCondition為12/16新條件 |
| 內容準備 | 41篇已核准、日期連續、所有必要內容非空；不把未來匯出寫入公開JSON |
| 原設定保留 | 5份原unit／host／11/25 drop-in雜湊一致 |
| `git diff --check` | PASS |

證據位置：`../output/devotional-through-20261216/`。僅保存內容摘要與匯出雜湊，不保存未來文章正文到此交付資料夾。新模板、測試與說明位於工作樹；本次沒有commit／push或Cloudflare部署。
