---
role: a16
files: [bible-site/admin/admin.js]
depends: [108-admin-server-zone-art, 109-admin-html-zone-cards]
checks:
  - node --check bible-site/admin/admin.js
  - python3 bible-site/tests/service_checks.py zoneadmin blessartadmin homeadmin admin
---
所有操作都在 E500 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，不碰經文 JSON、home.json、chapter.html、不下載或引入外部資源。只能更改 front matter 允許的檔案。

只改 admin/admin.js，依照 admin/index.html 的四區 id 與 37 張卡 id 接線。
- zone-music GET 的 config.music / config.zones，原 zone-music-select 仍選共用曲；zone-<id>-select 空值＝回退共用曲，每區 select 更新對應音訊 preview，儲存透過原 X-Bible-Token 向 POST /api/zone-music 一次傳完整 {music, zones}（若全空可只傳 music）。reset 回共用曲並清空所有 zones，重新繪製 UI；保留本來上傳共用音樂的操作。
- blessing-art GET 的 themes / cards / config。沿用既有 image / alt / edition 及 upload helper，新增單張卡上傳：檔案 ≤5MB、預覽、alt / edition，POST /api/blessing-art 傳完整物件 {work:..., ..., cards: {...}} 而不是覆蓋其他主題；清除該 card key（無其他卡的 cards 時可移除 cards），fallback 自動回主題圖；主題操作也不能丟失 cards。上傳原始圖像，不壓縮。
- 所有錯誤展示給使用者，動作完成後更新狀態；保留 button aria 與 keyboard/a11y，試聽未經按鍵不可自播。
- 不碰 homeadmin、版面 CSS、scripture、chapter。
