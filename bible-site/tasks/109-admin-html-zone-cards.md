---
role: de1050
files: [bible-site/admin/index.html]
checks:
  - python3 bible-site/tests/service_checks.py zoneadmin blessartadmin --grep "後台"
---
所有操作都在 E500 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，不碰經文 JSON、home.json、chapter.html、不下載或引入外部資源。只能更改 front matter 允許的檔案。

只改 admin/index.html 的前台音樂與收藏卡圖片區塊。沿用原有風格、class 與原有 ID，不破壞既有標記與功能。此任務只加 HTML 標記，不寫 JS。四區各有獨立音樂選單（空選項表示沿用共用曲）和試聽 audio：
zone-index-select,zone-index-preview; zone-search-select,zone-search-preview; zone-card-select,zone-card-preview; zone-blessing-select,zone-blessing-preview。
要有四區中文名、清楚提示「留空沿用共用音樂」，保留原本 zone-music-select/zone-music-preview/save/reset/status。
在「收藏卡圖片」主題設定下，加可折疊的「單張卡片」介面，按 work／peace／rest／faith 分組，合計 37 張。每張卡有標示 id 與出處 book ch:v（請用下方對照直接產出文字；不要輸出經文正文），且有 6 個 id：art-card-<ID>-file、-alt、-edition、-preview、-save、-clear；accept="image/jpeg,image/png,image/webp"，alt 120 字、edition 20 字、按鈕明顯標示上傳／更新與清除（清除後回主題圖），圖片預覽 hidden。每一個按鈕至少 44px 高並有 label 和可鍵盤操作的 details/summary。
卡片清單：
- work: work-01 work-02 work-03 work-04 work-05 work-06 work-08 work-09 work-10 work-11 work-13 work-14 work-16 work-17 work-18 work-19 work-20 work-21 work-22 work-23
- peace: peace-01 peace-02 peace-03 peace-04 peace-05 peace-06
- rest: rest-01 rest-02 rest-03 rest-04 rest-05
- faith: faith-02 faith-03 faith-04 faith-05 faith-06 faith-07
只有 HTML 文件，無外部資源，排版寬度 320/375/768/1440 不溢出。
