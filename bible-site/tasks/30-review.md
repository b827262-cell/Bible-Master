---
role: a16
files: [bible-site/REVIEW.md]
depends: [21-search-html]
checks:
  - test -s bible-site/REVIEW.md
---
你是審核員，只檢查、不修改網站程式。網站已改成四福音版（規格在 bible-site/prompts/multibook/SPEC.md）。請先執行 python3 bible-site/tools/verify_text.py，再閱讀 bible-site/site/ 裡的 6 個檔案，照下面 6 項檢查表逐項檢查：1. 所有頁面都只從 data/*.json 讀經文，沒有寫死的經文。2. verify_text.py 四卷都全部相符。3. 頁面之間的連結都正確，連結都帶 book=KEY。4. 沒有載入外部資源，字型用系統字型。5. 手機寬度 375px 下沒有橫向捲動（看 style.css 與各頁版面）。6. 簡繁一致，全部是繁體中文。把結果寫進 bible-site/REVIEW.md：每項標「通過」或「不通過」，不通過的要寫出檔案、行號和原因；沒有把握的項目標「不通過」並說明。完成後只回報 6 項的結果。
