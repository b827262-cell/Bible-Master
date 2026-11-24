# 每日禱讀延長至 2026-12-16（含當日）

**執行狀態：2026-11-16 已由PM安全新增安裝並驗收，timer active且enabled；下一次11/17 06:00 Asia/Taipei，最後12/16 06:00。** 舊11/25檔案保留，以新drop-in覆蓋其排程及日期條件；沒有手動觸發正式發布。

## 目的與邊界

- 台灣時間每天 06:00 逐日公開，**2026-12-16 含當日**；2026-12-17 起停止自動公開。
- 只延長排程與截止護欄，不改資料、DB、已核准內容或正式站。
- 不一次公開未來內容；發佈內容仍由 `publish_daily.py` 依當日日期逐日處理。

## 新增的兩個 user drop-in（PM 手動安裝）

| 用途 | 安裝位置 |
| --- | --- |
| timer 排程 | `~/.config/systemd/user/bible-devotional-publish.timer.d/release-through-20261216.conf` |
| service 截止護欄 | `~/.config/systemd/user/bible-devotional-publish.service.d/release-through-20261216.conf` |

repo 內的來源檔：

- `bible-site/devotional/systemd/release-through-20261216.timer.conf`
- `bible-site/devotional/systemd/release-through-20261216.service.conf`

安裝時請**安全新增**，不要覆蓋或刪除舊的 `release-through-20261125.*` 模板與已安裝的
`release-through-20261125.conf`。

## 舊檔保留與排序覆蓋

- timer drop-in 以檔名排序讀取：`release-through-20261125.conf` 先、`release-through-20261216.conf` 後。
- 新 timer drop-in 先寫 `OnCalendar=` 清空舊 11/25 規則，再只加入：
  - `2026-11-16..30 06:00:00 Asia/Taipei`
  - `2026-12-01..16 06:00:00 Asia/Taipei`
- 新 service drop-in 先寫 `ExecCondition=` 清空舊 11/25 日期護欄，再加入新的 12/16 日期條件。
  若不先清空，兩條 ExecCondition 會以 AND 串接，排程會在 11/25 提前截止。
- `Persistent=true`、原 `ExecStart` 與 `host.conf` 都不動；沒有新增可繞過日期的環境變數。

## PM 安裝後驗證

1. `systemctl --user daemon-reload`
2. `systemctl --user restart bible-devotional-publish.timer`
3. 確認 timer 只載入兩段新規則，且最後一天是 12/16：

   ```bash
   systemctl --user show bible-devotional-publish.timer -p TimersCalendar
   ```

4. 確認有效 `ExecCondition` **只有**新的 12/16 日期條件，沒有殘留 2026-11-25：

   ```bash
   systemctl --user show bible-devotional-publish.service -p ExecCondition \
     | grep -o 'argv\[\]=.*ignore_errors'
   ```

   `argv[]` 內應只看到 `2026-12-16`，不應出現 `2026-11-25`。只看 `argv[]`，不要用
   `start_time`／`stop_time` 的執行時間欄位判斷，那些是上次執行的時間戳。

5. 用 `systemd-analyze calendar` 核對 11/16～11/30 共 15 次、12/01～12/16 共 16 次，
   合計 31 次，最後一次為 12/16；12/17 之後 `Next elapse: never`：

   ```bash
   systemd-analyze calendar --base-time='2026-11-15 21:59:00 UTC' --iterations=15 \
     '2026-11-16..30 06:00:00 Asia/Taipei'
   systemd-analyze calendar --base-time='2026-11-15 21:59:00 UTC' --iterations=16 \
     '2026-12-01..16 06:00:00 Asia/Taipei'
   systemd-analyze calendar --base-time='2026-12-16 23:00:00 UTC' --iterations=1 \
     '2026-11-16..30 06:00:00 Asia/Taipei'
   systemd-analyze calendar --base-time='2026-12-16 23:00:00 UTC' --iterations=1 \
     '2026-12-01..16 06:00:00 Asia/Taipei'
   ```

## 注意

- 不要用 `systemctl --user start bible-devotional-publish.service` 測試；這會觸發正式發佈流程。
- 本任務未安裝 systemd、未重啟 timer、未觸發 publish、未 commit/push/部署。
- 內容篇數（PM 另行核對：截至 12/16 可匯出 41 篇，含原 15 篇與 365 計畫前 26 篇）不在本檔變更範圍。
