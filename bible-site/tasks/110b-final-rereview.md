---
role: cbr
files: [bible-site/REVIEW-zone-art.md, bible-site/tools/build_public.py, bible-site/site/music.js, bible-site/site/blessing.html, bible-site/admin/server.py, bible-site/admin/index.html, bible-site/admin/admin.js]
timeout_min: 45
checks:
  - python3 bible-site/tools/check_all.py
  - python3 bible-site/tests/service_checks.py zoneadmin blessartadmin homeadmin admin
  - python3 bible-site/tests/deploy_checks.py
  - grep -Eq '^\*\*狀態：(PASS|FAIL)\*\*' bible-site/REVIEW-zone-art.md
---
所有操作都在 E500 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，不碰經文 JSON、home.json、blessing.json、chapter.html，不下載或引入外部資源。只能更改 front matter 允許的檔案；`bible-site/tests/` 這一輪由 PM 改過，你只讀不改。

這是 110-final-review 的複審。上一輪你的 `bible-site/REVIEW-zone-art.md` 標題寫 PASS、內文寫 FAIL，互相矛盾，這一輪要整份重寫成前後一致。

上一輪的兩個問題，PM 已在測試端處理，請獨立核對而不是照單全收：

1. 「跨頁續播探測不穩定」：PM 查到原因在測試伺服器。Python 的 `SimpleHTTPRequestHandler` 不支援 HTTP Range，headless Chrome 對還沒整檔下載的 mp3 無法 seek，探測頁自己把第二頁跳到第 7 秒的動作留在 0 秒（前一頁播過同一檔時有快取才會成功）。處理：
   - `bible-site/tests/site_checks.py` 新增 `RangeHandler`（回 206／416），zonemusic 的本機伺服器改用它。
   - `bible-site/tests/zone_probe.html` 第三頁在同一首曲子時，最多等 6 秒讓續播位置生效再取樣；換曲不等。
   - PM 實測：改之前 6 個 zonemusic 平行跑有 1 個失敗，新增跨曲案例後 8 個有 7 個失敗；改之後 8 個平行跑 8 個全過（各 113 項）。
2. 「四區測試用同一首曲子」：`zone_variants()` 的「四區獨立」改成 index／search／card 各用不同檔、blessing 不設定而回退共用曲；另加「兩區同曲」案例驗證分區模式下同曲續播。PM 做過三個突變測試（永不續播、忽略分區鍵、search 誤用 index 鍵），zonemusic 分別出現 5、8、2 項不通過，還原後全過。

請你做的事：
- 讀 `git diff -- bible-site/tests/site_checks.py bible-site/tests/zone_probe.html`，判斷這些改動有沒有把真正的續播缺陷蓋掉（例如等待條件過寬、Range 實作有錯）。有疑慮就寫進報告，不要改測試。
- 在工作樹直接跑 front matter 的 checks；想確認穩定性可以再多跑幾次 `python3 bible-site/tests/site_checks.py zonemusic`。不需要另開隔離副本。
- 依 110-final-review.md 的第 1–5 點重新確認一次（範圍、舊 JSON 相容、寫入端點防護、前台行為、測試覆蓋）。上一輪已核對且程式沒變的項目可以沿用結論，但要註明是沿用。
- 重寫 `bible-site/REVIEW-zone-art.md`：第三行必須是 `**狀態：PASS**` 或 `**狀態：FAIL**`，全文結論與它一致；按嚴重度列問題、具體路徑行號、修補建議、剩餘風險。全部 checks 綠燈且沒有中度以上問題才能寫 PASS。
- 只允許極小且有測試覆蓋的明確缺陷直接修，修過要重跑 checks；結構問題只列在報告。報告不得包含 secrets。
