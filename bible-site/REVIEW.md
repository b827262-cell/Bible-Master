# 四福音網站審核報告

## 檢查項目與結果

| 檢查項目 | 結果 | 說明 |
|---------|------|------|
| 1. 所有頁面都只從 data/*.json 讀經文，沒有寫死的經文 | 通過 | app.js 使用 fetch 從 ../data/<key>.json 讀取經文，各頁引入 app.js，無寫死經文 |
| 2. verify_text.py 四卷都全部相符 | 通過 | 馬太福音：1071/1071 節相符，馬可福音：678/678 節相符，路加福音：1149/1149 節相符，約翰福音：878/878 節相符 |
| 3. 頁面之間的連結都正確，連結都帶 book=KEY | 通過 | index.html、chapter.html、search.html 的連結均使用 `book=KEY` 格式 |
| 4. 沒有載入外部資源，字型用系統字型 | 通過 | style.css 無 @import，字型使用 system-ui, -apple-system, "PingFang TC" 等系統字型 |
| 5. 手機寬度 375px 下沒有橫向捲動 | 通過 | style.css 第 47 行設定 `overflow-x: hidden;`，第 48 行設定 `min-width: 0;` |
| 6. 簡繁一致，全部是繁體中文 | 通過 | 所有頁面 `<html lang="zh-Hant">`，內容使用繁體中文（經文、書卷、章、節） |

