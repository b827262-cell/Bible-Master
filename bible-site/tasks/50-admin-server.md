---
role: e500
files: [bible-site/admin/server.py]
checks:
  - python3 -m py_compile bible-site/admin/server.py
  - python3 bible-site/tests/service_checks.py admin --grep '^(?!.*(admin\.js|index\.html))'
---
只改 bible-site/admin/server.py（管理後台的安全與錯誤修正）。先讀完整個 server.py，再依下列清單修改；其他功能（/api/status、/api/models、/api/tasks、/api/ping、check_all、visual_checks、verify_text、smoke_test 動作）保留不變。

1. 移除所有 CORS：刪掉 send_json 裡三行 Access-Control-Allow-* 標頭，刪掉整個 do_OPTIONS 方法。
2. log_message 會當掉（固定讀 args[2]，但 send_error 只傳兩個參數，導致 404 變成空回應）。改成：
   sys.stderr.write("[%s] 後台API: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), format % args))
   注意是繁體「後台」，整個檔案不准出現簡體字（例如「后台」）。
3. 靜態檔只允許 "/"、"/index.html"、"/admin.js"、"/admin.css"；其他非 /api/ 路徑一律 self.send_json({"error": "找不到檔案"}, code=404)。（所以 GET /server.py 要回 404。）
4. /api/report/<name> 改成白名單：只允許 "TEST-REPORT.md"、"FAILS.md"、"DISPATCH-REPORT.md"、"PROGRESS.md"、"CHANGELOG.md"，而且只從 SITE_ROOT（bible-site/）讀；不在白名單就回 404。CLAUDE.md、HANDOFF.md 等都要回 404。
5. 刪除 build_data 動作（/api/action/build_data 整個 elif 分支刪掉，讓它落到 404）。
6. do_POST 一開始先檢查：
   - 必須有請求標頭 X-Bible-Admin，值為 "1"，否則回 self.send_json({"error": "缺少 X-Bible-Admin 標頭"}, code=403)。
   - 若有 Origin 標頭，它必須等於 "http://" + 請求的 Host 標頭，否則回 403（{"error": "不允許的來源"}）。沒有 Origin 標頭則允許。
7. 同一時間只能跑一個動作：在模組層級加 ACTION_LOCK = threading.Lock()；handle_run_command 先 ACTION_LOCK.acquire(blocking=False)，拿不到就回 self.send_json({"error": "已有動作執行中"}, code=409)；執行完（finally）釋放。
8. argparse 的 --host 預設改成 "127.0.0.1"，說明文字改成「監聽主機 IP（預設 127.0.0.1，只限本機）」；run_server 的預設參數也改成 "127.0.0.1"。

驗收（腳本自動跑）：python3 -m py_compile 通過，且 python3 bible-site/tests/service_checks.py admin 中與 server.py 有關的檢查全部通過（admin.js／index.html 的項目由下一個任務處理）。改完只回報改了哪些地方。
