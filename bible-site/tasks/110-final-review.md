---
role: cbr
files: [bible-site/REVIEW-zone-art.md, bible-site/tools/build_public.py, bible-site/site/music.js, bible-site/site/blessing.html, bible-site/admin/server.py, bible-site/admin/index.html, bible-site/admin/admin.js]
depends: [109b-admin-js-zone-cards]
checks:
  - python3 bible-site/tools/check_all.py
  - python3 bible-site/tests/service_checks.py zoneadmin blessartadmin homeadmin admin
  - python3 bible-site/tests/deploy_checks.py
---
所有操作都在 E500 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，不碰經文 JSON、home.json、chapter.html、不下載或引入外部資源。只能更改 front matter 允許的檔案。

這是 CodeBuddy CLI 最終審核，只在首輪 check_all.py 3/3、service_checks、deploy_checks 成功後執行一次；effort high，優先唯讀。
1. git diff --name-only 逐項確認本次許可範圍，不要將本次新增的測試／任務誤當成模型擅改，也不要覆蓋執行前已有的 AGY-MUSIC-TOUCH-TEST.md、角色 Spark 設定與圖片／output。
2. 舊 JSON zone-music.json / blessing-art.json 仍可用，home.json 六欄、blessing.json 凍結、四福音 JSON 位元組不變。
3. check_write_auth、路徑白名單、..、副檔名、存在性、body 最大值、原子寫入、POST 400/403/413。
4. 前台無外部資源或經文寫死、手勢與 sessionStorage 舊曲續播/新曲歸零、按鈕 min 44px、a11y。
5. 測試是否真的覆蓋四區獨立/缺省共用、單卡覆蓋/主題回退/純文字/原檔下載、靜態發佈收錄 assets，排除純靜態假陽性。
產出 bible-site/REVIEW-zone-art.md：狀態 PASS / FAIL、按嚴重度列問題、具體路徑行號、修補建議、風險。只允許極小且有測試覆蓋的明確缺陷直接修；結構問題只列報告，禁止重構。若修過必須重跑 check_all.py 全綠才可以宣稱通過。**不得** git commit／push／部署；報告不應包含 secrets。
