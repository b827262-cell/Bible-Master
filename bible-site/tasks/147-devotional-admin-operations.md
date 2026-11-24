# 147 後台禱讀排程設定與手動上架（獨立模組）

使用者已要求在後台可設定、編輯內容及上架。本任務只新增 `bible-site/admin/devotional_operations.py` 與 `bible-site/tests/devotional_operations_checks.py`。不改其他程式/資料/DB/systemd或Git，不commit/push，不實際啟動發布。PM/145整合後驗收。

模組對外固定：`get_settings()`、`save_settings(payload)`、`publish_now(payload)`；`OperationError(message,status)`安全繁中錯誤。環境設定/runner/clock可由Python內部建構注入供測試，但不可讓HTTP payload覆蓋路徑、命令、today或unit。標準庫，不需新套件。

get_settings回 `{version,enabled,start_date,end_date,time,timezone:"Asia/Taipei",today,busy,service:{active,result},warning:null|string}`。version是目前實際載入/managed檔案與狀態的穩定digest；保存時驗舊version409。從已載入固定timer的所有OnCalendar解析連續有限每日時間規則（目前2026-11-16..30及2026-12-01..16），取實際開始/截止及共同HH:MM；不可硬編12/16，無法確定就null+warning。service只查固定publisher unit，命令輸出限量/timeout，錯誤不能曝rawstderr/憑證。

save_settings body `{version,enabled:bool,start_date,end_date,time:"HH:MM"}`，canonical ISO日期、start<=end、最多730日，固定Asia/Taipei。只管理兩個自己專用的`zz-admin-release.conf`：
- `~/.config/systemd/user/bible-devotional-publish.timer.d/zz-admin-release.conf`
- `~/.config/systemd/user/bible-devotional-publish.service.d/zz-admin-release.conf`

加明確Managed by Bible-Master標記；若既有同名檔非本程式管理就拒絕，不覆蓋他人檔。舊1125/1216模板、host.conf及主unit不刪不改。新timer OnCalendar=清除舊規則，依月份生成有限日範圍及HH:MM；Persistent=yes。新service ExecCondition=取代已知日期護欄，生成以台灣實際日期[start,end]為範圍的Python條件（日期僅用驗證後整數，不拼接任意字串），原ExecStart不變。若偵測到無法辨識的自訂ExecCondition則拒絕並說明，避免清掉其他條件。

進程鎖避免重複操作；保存前在私有state目錄備份既有自己管理的兩檔；atomic replace、daemon-reload、enable+restart timer或disable --now timer。所有命令固定argv、無shell=True。任何一步失敗要還原自己檔案與原啟用/active狀態，不能假稱還原成功。不要restart/stop發佈service；發佈進行中拒絕改設定。成功回重新查驗的settings，不只回傳使用者輸入。

publish_now body `{confirm:true,schedule_version}`。需確認目前設定version、今天在[start,end]、service沒有active/job且同進程無其他發布；自動timer暫停不阻擋手動發布。只執行固定`systemctl --user start bible-devotional-publish.service`，等待最長90秒。事前/事後讀InvocationID、ActiveState、Job、Result、ExecMainStatus；不能把前一次success當本次成功，必須確認新InvocationID且Resultsuccess/exit0。日期條件跳過不能說成功；失敗回安全錯誤。timeout時服務可能仍在執行，要如實回503並保持後續active/job拒絕重送。服務完成回`{ok:true,outcome:"service_completed",message,settings}`，不宣稱Cloudflare已部署。禁止--date模擬未來或任意Git命令，既有publish_daily自行在獨立checkout只推當日核准資料。

測試只用temp config/state、mock runner/clock，至少涵蓋跨月設定、關閉/恢復、version衝突、拒非managed檔、UTC日期邊界、指令失敗rollback（含rollback失敗的誠實訊息）、重複/進行中發布拒絕、舊InvocationID success不算完成、真正新success、失敗/timeout/skip、無任意命令/路徑注入。嚴禁真實systemctl寫入或Git操作。GET唯讀且不自動建立配置。

閱讀145/146以保契約相容。完成實作及自己的測試，回報路徑/結果/限制，不再擴大範圍。
