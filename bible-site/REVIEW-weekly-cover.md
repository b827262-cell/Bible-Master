# 首頁一週封面接線最終審查報告

**狀態：PASS**

依 `brief-20261113-weekly-wire.md` 唯讀審查。七天各擷取 375px 與 1440px 畫面，共 14 張 PNG；檢視總覽可見七張不同封面，主體在兩種寬度可辨識，經文區與照片分開。自動檢查涵蓋七天資料與經文、光色對比、各寬度不重疊及水平溢出。

| 星期 | 主題 | 截圖 | 視覺檢視 |
| --- | --- | --- | --- |
| 一 | 清晨禱告 | `mon-375.png`、`mon-1440.png` | PASS |
| 二 | 先求神國 | `tue-375.png`、`tue-1440.png` | PASS |
| 三 | 風浪平靜 | `wed-375.png`、`wed-1440.png` | PASS |
| 四 | 活水泉源 | `thu-375.png`、`thu-1440.png` | PASS |
| 五 | 祈求尋見 | `fri-375.png`、`fri-1440.png` | PASS |
| 六 | 上好福分 | `sat-375.png`、`sat-1440.png` | PASS |
| 日 | 生命的光 | `sun-375.png`、`sun-1440.png` | PASS |

截圖位於 `bible-site/screenshots-weekly/`，皆為 375 或 1440px 寬、1000px 高。七天 `focus` 均為 `35% 50%`；截圖中主體未見明顯裁切，經文顯示於深色背景，未壓住照片。

## 自動檢查

檢查在含 `bible-site/`、`.verify/` 與根目錄 `.gitignore` 的隔離副本執行，避免覆寫工作樹報告。

- `python3 bible-site/tools/check_all.py`：PASS，3/3。
- `python3 bible-site/tests/visual_checks.py`：PASS，全部通過。
- `python3 bible-site/tests/deploy_checks.py`：PASS，全部通過。
- `python3 bible-site/tests/service_checks.py homeadmin admin`：PASS，全部通過。後台一週封面設定區、啟用開關與 `/api/home-week` 端點已就位，讀寫、權限及資料驗證檢查均通過。

## 後續建議

逐日編輯主題、經文及換圖功能可留待下一輪。
