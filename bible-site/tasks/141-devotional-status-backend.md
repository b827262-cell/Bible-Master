# 141 禱讀唯讀狀態API（tab2，139完成後）

只准修改 `bible-site/admin/server.py`、新增 `bible-site/admin/devotional_status.py`。保留既有週封面與其他功能。不改資料、DB、systemd、Git、正式站，不commit/push/部署，不觸發發布。

GET `/api/devotional-status` 回200 JSON，局部資源不可用仍回可用部分。新增模組供隔離mock測試，建議入口 `collect_status(site_root, now=None)`；now僅內部測試注入，不接受HTTP參數覆蓋日期或URL。API契約固定如下（可加欄位但不能改既有欄名）：

```
{observed_at: ISO8601, timezone:"Asia/Taipei",
 public:{state:"ok|unavailable|invalid",count:int|null,latest_date:"YYYY-MM-DD"|null,observed_at:ISO8601,source:"https://bible.b827262.org/data/devotional.json",error:string|null},
 local:{state:"ok|unavailable|invalid",count:int|null,latest_date:string|null,observed_at:ISO8601,source:"本機 data/devotional.json",error:string|null},
 schedule:{state:"ok|unavailable|invalid",enabled:bool|null,active:string|null,next_run:string|null,cutoff_date:"YYYY-MM-DD"|null,expired:bool|null,calendar:string|null,error:string|null},
 last_run:{state:"success|failed|never|unknown|skipped",started_at:string|null,finished_at:string|null,exit_code:int|null,error:string|null},
 release_state:"scheduled|cutoff|attention|unknown", warnings:[string]}
```

正式站與本機資料分開，不從本機猜正式站。驗證JSON陣列、每筆合法ISO日期、重複日期/壞資料不報成功，空陣列是ok count0/latestnull。不回傳禱讀正文。限制HTTP與本機讀取最多2MiB，HTTP timeout<=3秒，固定HTTPS來源、不允許任意重導來源。曾遇Python urllib預設UA 403但curl成功，請設定合理UA並實測；若採curl須固定參數、timeout及輸出上限，不能shell=True。

只讀 `systemctl --user show` 固定 `bible-devotional-publish.timer`與`.service`，LC_ALL=C，timeout每次<=2秒，輸出有界。不得讀任意journal或回傳原始命令錯誤／token／SSH／路徑機密。不存在systemd時state unavailable/lastunknown，不當failed。timer需要ActiveState/UnitFileState/NextElapseUSecRealtime/TimersCalendar；service需要Result/ExecMainStatus/ExecMainStartTimestamp/ExecMainExitTimestamp。時間字串可保留systemd原文供UI顯示（時區標明），未執行laststate=never。

截止日從實際載入的有限OnCalendar（例如2026-11-14..25 06:00:00 Asia/Taipei）解析，不硬編11/25。無法確定則cutoff_date/expired=null，誠實unknown。台灣日期>截止日則release_state=cutoff，正常停止不報故障；lastfailed時attention，其餘有完整可用資訊才scheduled，無法取得必需資訊unknown。不能僅因local檔案比正式站舊就報失敗。任何提醒必須可由資料支持，UI不會提供修改或發布按鈕。

保留原token/origin/靜態白名單及POST行為；不得讓新Python模組被靜態下載。查詢不得卡住主服務；總請求時間有界。實際送HTTP前後不改任何真實狀態。

請在/tmp以mock測試成功、partialfailure、空/壞JSON、size/timeout、無systemd、失敗與never/cutoff/跨UTC日期，並在隨機port開隔離admin測GET整合與靜態模組不可讀。不要跑真實check_all，不改測試檔。交付API契約有任何必要調整立刻通知PM，不自行改與tab3約定。完成回報後待命。
