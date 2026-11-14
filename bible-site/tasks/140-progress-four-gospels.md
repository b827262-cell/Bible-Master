# 140 四福音進度誤報修正（tab5）

你是tab5地端工程助理。使用者要求execute NEXT-TARGETS。本任務只准修改 `bible-site/tools/pm_status.py`。不要修改PROGRESS/FAILS/TEST-REPORT、資料、其他程式；不要commit/push/部署。所有測試在/tmp隔離副本，不跑真實check_all。

目前工具檢查舊data/mark.json而誤報未完成。改為驗證mat/mrk/luk/jhn四份JSON：必須是物件、chapters為陣列、章數分別28/16/24/21、逐節物件總數1071/678/1149/878，總3776；缺檔、壞JSON、錯型別、章數/節數不符皆不可報完成。文案改四福音／3776節。site核心清單涵蓋目前前台home/index/chapter/search/card/blessing/devotional的HTML與app.js/style.css/music.js/devotional.js，不能仍聲稱只有6檔。缺必要檔需失敗。

保留自動區塊外的所有手寫內容。--no-checks不可觸發check_all，只沿用FAILS結果並清楚標示；不得把失敗硬改成功。其他CLI/退出碼語意保持。

最少測試：完整四卷與站檔→0；缺一卷／壞JSON／節數少一／必要站檔缺失→非0；--no-checks沒有子程序呼叫，手寫紀錄完整保留。可用/tmp副本import模組+mock方式檢查，不新增repo測試檔，QA另獨立驗證。用ast解析語法。完成回報檔案、測試、證據位置，然後待命。
