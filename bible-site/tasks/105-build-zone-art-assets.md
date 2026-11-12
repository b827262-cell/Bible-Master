---
role: a16
files: [bible-site/tools/build_public.py]
checks:
  - python3 -m py_compile bible-site/tools/build_public.py
  - python3 bible-site/tests/deploy_checks.py
---
所有操作都在 E500 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，不碰經文 JSON、home.json、chapter.html、不下載或引入外部資源。只能更改 front matter 允許的檔案。

修改 tools/build_public.py 的 referenced_assets()，保留原邏輯並加入讀取：
1. data/zone-music.json 必填 music；選填 zones 物件的所有 mp3 參照也加入 used。
2. data/blessing-art.json 原有 work/peace/rest/faith 的 image；再加入選填 cards 物件下每筆的 image。
3. 舊格式兩檔保持向下相容。不要修改任何配置實例，DATA_FILES 與 HEADERS 不動。
4. 防禦非物件／無效 JSON，遵循現有寫法。驗收以 tests/deploy_checks.py（含 zones 與 cards 測試）為準。
