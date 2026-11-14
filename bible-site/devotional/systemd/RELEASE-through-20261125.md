# 每日禱讀：逐日公開至 2026-11-25（含當日）

狀態：**檔案已備妥，PM 已於 2026-11-14 安全安裝並驗收；本文件不構成發佈宣告。**
範圍：只限制既有 `bible-devotional-publish.timer`／`.service` 的執行期間，不改資料庫、不改 365 篇內容、不改既有 `host.conf` 或主 unit。

## 1. 行為

- 沿用 Asia/Taipei 每日 **06:00**，執行日為 **2026-11-14～2026-11-25**（12 次，含截止日當天）。
- **11-25 06:00 是最後一次**；11-26 起 timer 沒有下一次排程。
- `Persistent=true` 由主 unit 保留。為防止關機／停機後在 11-26 之後補跑 11-25 的排程，service drop-in 以 `ExecCondition` 在 `ExecStart` 之前檢查台灣實際日期：
  - 台灣日期 **<= 2026-11-25** → 回 0，照常發佈。
  - 台灣日期 **> 2026-11-25** → 回 1，systemd 跳過此輪，不執行 git fetch/checkout 與 `publish_daily.py`。
- 判斷使用 Python 3 標準庫 `datetime` + `zoneinfo`，固定 `Asia/Taipei`，不受主機 `TZ` 或 UTC 日期影響；**沒有**測試用環境變數可繞過。
- 截止後，11-26 以後的內容仍留在 DB，已公開內容不刪除。

## 2. 檔案與安裝位置

| 本檔 | 安裝為 user unit drop-in |
|---|---|
| `release-through-20261125.timer.conf` | `~/.config/systemd/user/bible-devotional-publish.timer.d/release-through-20261125.conf` |
| `release-through-20261125.service.conf` | `~/.config/systemd/user/bible-devotional-publish.service.d/release-through-20261125.conf` |

（若設有 `XDG_CONFIG_HOME`，路徑為 `$XDG_CONFIG_HOME/systemd/user/...`。）

## 3. 安裝步驟（PM 執行；安全新增、不覆蓋）

```bash
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
SRC="$HOME/project/AI/Bible-Master/bible-site/devotional/systemd"

install -d -m 0755 \
  "$UNIT_DIR/bible-devotional-publish.timer.d" \
  "$UNIT_DIR/bible-devotional-publish.service.d"

# 目標已存在就停下，不覆蓋任何既有檔案
for pair in \
  "release-through-20261125.timer.conf:bible-devotional-publish.timer.d/release-through-20261125.conf" \
  "release-through-20261125.service.conf:bible-devotional-publish.service.d/release-through-20261125.conf"
do
  src="${pair%%:*}"; dst="$UNIT_DIR/${pair#*:}"
  if [ -e "$dst" ]; then echo "已存在，停止：$dst"; exit 1; fi
  cp "$SRC/$src" "$dst"
done

systemctl --user daemon-reload
systemctl --user restart bible-devotional-publish.timer
```

不要重啟或手動啟動 `bible-devotional-publish.service` 來測試：它會 fetch、commit、push 正式站。

## 4. 安裝後確認

```bash
systemctl --user list-timers bible-devotional-publish.timer --all
systemctl --user show bible-devotional-publish.timer \
  -p TimersCalendar -p NextElapseUSecRealtime -p LastTriggerUSec -p Persistent
systemctl --user show bible-devotional-publish.service -p ExecCondition
```

預期（2026-11-14 當天 06:00 過後安裝）：

- `TimersCalendar` 只有 `2026-11-14..25 06:00:00 Asia/Taipei`，不再有 `*-*-* 06:00:00`。
- 下一次：`2026-11-15 06:00:00 CST`；最後一次：`2026-11-25 06:00:00 CST`。
- `Persistent=yes`。
- `ExecCondition` 已載入上述 Python 指令。

## 5. 已執行測試（隔離，未觸發正式服務）

| 測試 | 方法 | 結果 |
|---|---|---|
| 排程範圍 | `systemd-analyze calendar --base-time="2026-11-13 00:00:00 Asia/Taipei" --iterations=13 '2026-11-14..25 06:00:00 Asia/Taipei'` | 11-14～11-25 共 12 次；第 12 次為 11-25 06:00，無第 13 次，無 11-26 |
| unit 語法 | 以臨時 `XDG_CONFIG_HOME` 放入主 unit＋兩個 drop-in，`systemd-analyze --user verify` | exit 0；另以故意錯誤的 drop-in 做控制組，確認 verify 確實會讀取 drop-in |
| 截止邊界 | 取出 drop-in 中**未修改**的 `python3 -c` 原始碼，凍結 `datetime.now()` 模擬 UTC 時刻 | 8/8 通過（見下） |
| 今日實際值 | 直接執行同一段程式碼 | 台灣 2026-11-14 → exit 0 |

邊界案例（UTC → 台北）：

| UTC | 台北 | ExecCondition |
|---|---|---|
| 2026-11-13 16:30 | 11-14 00:30 | 0 |
| 2026-11-24 15:59 | 11-24 23:59 | 0 |
| 2026-11-24 16:00 | 11-25 00:00 | 0 |
| 2026-11-25 15:59 | 11-25 23:59 | 0 |
| 2026-11-25 16:00 | **11-26 00:00**（UTC 仍是 11-25） | 1 |
| 2026-11-25 21:59 | 11-26 05:59 | 1 |
| 2026-11-25 22:00 | 11-26 06:00（排程時刻） | 1 |
| 2026-11-26 00:00 | 11-26 08:00 | 1 |

完整紀錄：`/tmp/dev365-138-calendar.txt`、`/tmp/dev365-138-verify.txt`、`/tmp/dev365-138-verify-installshape.txt`、`/tmp/dev365-138-verify-control.txt`、`/tmp/dev365-138-condition.txt`。

## 6. 預期公開數量

- 截至 2026-11-14，正式站為 **9 篇（11-06～11-14）**。
- 若 11-15～11-25 每天排程都成功，11-25 當天累計為 **20 篇（11-06～11-25）**：原 15 篇＋365 計畫前 5 篇。
- **這不代表 365 篇已全部公開**；11-26 之後的內容仍在 DB，維持未發佈。

## 7. 回滾

```bash
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
rm -f "$UNIT_DIR/bible-devotional-publish.timer.d/release-through-20261125.conf" \
      "$UNIT_DIR/bible-devotional-publish.service.d/release-through-20261125.conf"
systemctl --user daemon-reload
systemctl --user restart bible-devotional-publish.timer
```

移除後即恢復主 unit 的無限每日 `*-*-* 06:00:00 Asia/Taipei`；`host.conf` 與主 unit 未被本變更修改。
