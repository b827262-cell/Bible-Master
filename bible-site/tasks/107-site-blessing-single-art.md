---
role: e500
files: [bible-site/site/blessing.html]
depends: [106-site-music-zones]
checks:
  - python3 bible-site/tests/site_checks.py blessart
---
所有操作都在 E500 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，不碰經文 JSON、home.json、chapter.html、不下載或引入外部資源。只能更改 front matter 允許的檔案。

改 site/blessing.html 的 showCard(cardObj,themeId) 圖檔查找規則：
- 若 artMap.cards 是物件且有 artMap.cards[cardObj.id]，優先此單卡圖；
- 否則回退 artMap[themeId] 主題圖；
- 若兩者沒有可用圖，沿用目前純文字流程。
其他 renderCard / data-art / #art-download 原檔 byte-for-byte 下載 / canvas 合成 / aria / 切換主題維持。不要修改 blessing.json 與寫死經文。詳見 site_checks.py blessart。
