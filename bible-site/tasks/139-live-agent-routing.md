# 139 Herdr角色路由修正（tab2）

使用者已要求execute NEXT-TARGETS。你是tab2後端。只准修改 `bible-site/tools/herdr_team.py`。保留已有變更，不commit/push/部署，不修改roles.yml或其他檔案。不向其他agent送測試prompt。

1. 依AGENT-ROLES目前映射：PM/codex/review→w2:p1；backend/pm/backend_developer→w2:p2；fe/ui/frontend→w2:p5；qa/test→w2:pC；assistant/local/docs→w2:pD。舊機器別名若保留，需明確標成相容別名，不能仍導向不存在的pane；pm舊語意後端可保留，但總PM用codex。
2. pane ID為opaque、可能含大寫英文字，resolve不得將w2:pC改成w2:pc。可接受明確全ID及同workspace的pC短ID。角色名稱可case-insensitive。
3. 送出前必須從live pane inventory確認存在；移除pane或agent_not_found必須拒絕，不送輸入。unknown/空agent不可當成已完成。保留人工派發邊界，不新增pane run自動輸入分支。
4. 更新舊TEAM/MANUAL_PANES與頂端說明，真實unknown的tab2～5自動run須拒絕並說明人工派發。即使被辨識為working之後變unknown，也不能當成功。原blocked拒送保留。
5. 以mock herdr inventory測試解析、失效ID拒絕、unknown/blocked不送出；不得碰真實pane。檢查py_compile改用ast避免寫pycache。

完成回報改動/實際測試/限制，然後立即接續讀取 `141-devotional-status-backend.md` 執行後端API；兩任務同屬你負責且檔案不重疊。若規格有衝突先回報PM，不能自行擴大白名單。
