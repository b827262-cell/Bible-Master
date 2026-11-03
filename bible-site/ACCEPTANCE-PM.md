# PM 最終驗收報告（抽經文卡＋入口首頁）

- 驗收時間：2026-11-03 12:33–12:45（Asia/Taipei）
- 驗收者：PM（獨立驗收；只讀，未 commit／未 push／未修改任何檔案／未動 8090、8091／未執行 `build_data.py`）
- 範圍：(1) 抽經文卡 `blessing.html` ＋視覺美化；(2) 入口首頁 `home.html` ＋根目錄轉址
- 唯一新增檔案：本檔 `bible-site/ACCEPTANCE-PM.md`

## 結論：**通過**

兩批工作共 28 個檔案變更（11 個修改、17 個新增），全部符合 `CLAUDE.md` 鐵則，未發現阻擋上線的缺陷。建議 commit。

---

## a. 自動檢查（結束碼）

| 指令 | 結果 | 結束碼 |
|---|---|---|
| `python3 bible-site/tools/check_all.py` | 總結：3/3 項檢查通過 | **0** |
| `python3 bible-site/tests/visual_checks.py` | 92 項全部通過 | **0** |

`check_all.py` 三項細目：經文比對 四卷 1071／678／1149／878 全相符、無寫死經文；節數與檔案 3776/3776；網站檢查（含 home、blessing）全部通過。`FAILS.md` 為「全部通過，沒有要修的項目」。

## b. 指定分組檢查（結束碼）

```
python3 bible-site/tests/site_checks.py home blessing blessnav blessindex blessstyle
```

結果：60 項全部通過，結束碼 **0**。

## c. Repo 衛生與經文資料完整性

**沒有不該進 repo 的檔案。** 以 `git add -An .` 逐檔掃描，比對 `*.pid`、`__pycache__`、`*.pyc`、`tools/dispatch/generated`、`logs/`、`*.log`、`node_modules`、`.env`、`screenshots`：**0 命中**。

`.gitignore` 已正確涵蓋 `logs/`、`*.pid`、`__pycache__/`、`*.pyc`、`bible-site/logs/`、`bible-site/tools/dispatch/generated/`、`.verify/download/ebible/x/`。實測 `logs/frontend-8090.pid`、`logs/backend-8091.pid`、`bible-site/logs/`、`dispatch/generated/*.yml`、兩處 `__pycache__` 都仍被忽略。

**經文資料沒有被改動。**

- `git diff --stat bible-site/data`：**空**（追蹤中的四卷 JSON 無任何變更）。
- `git diff --exit-code HEAD -- data/{mat,mrk,luk,jhn}.json`：結束碼 **0**，即與 HEAD 位元組相同。
- `git status bible-site/data`：只有 `?? bible-site/data/blessing.json` 一項新增，符合預期。
- 檔案時間戳：`mat/mrk/luk/jhn.json` 皆為 11-02 20:06:15，未因本次驗收或 `build_data.py` 變動。

**其他衛生觀察**

- `blessing.json` 只存書卷／章／節參照（`book`、`ch`、`v`），**不含經文文字**，符合「經文只在 data/<book>.json」的分層。
- 本次進入 repo 的唯一較大二進位檔是 `site/assets/home-music.mp3`（2.8M）；`jordan.jpg` 157K。兩者都是頁面必要素材且為本機檔案。

## d. 新頁面：無寫死經文、無外部資源

以獨立腳本（不採信專案自述）掃描，比對 3776 節經文的 **8 字窗**：

| 檔案 | 寫死經文 | 外部資源 |
|---|---|---|
| `site/home.html` | 0 筆 | 無 |
| `site/blessing.html` | 0 筆 | 無 |
| `site/app.js`、`style.css`、`index.html`、`card.html`、`chapter.html`、`search.html` | 0 筆 | 無 |

- 全 `site/` 掃描 `https?:`、協定相對 URL、`@import`：**0 筆**。
- 經文取得路徑正確：`home.html` 用 `Bible.load("luk")`，`blessing.html` 用 `Bible.load(book)`；兩頁皆無自行 `fetch` 經文。
- 瀏覽器實測：`home.html` 的 `.home-verse` 逐字等於 `luk.json` 路加福音 4:27，出處「路加福音 4:27（和合本）」；`blessing.html?card=work-01` 正確顯示馬太福音 25:21。兩頁 `externalRefs` 皆為 `[]`。
- `blessing.json` 的 37 張卡：`theme` 皆有定義、`id` 無重複、書卷／章／節**全部可在 `data/*.json` 解析**、無簡體字。
- `home.html` 的 `<audio>` 無 `autoplay` 屬性（符合任務規格），音量 0.6。

## e. CLAUDE.md 鐵則逐條核對

| 鐵則 | 判定 | 證據 |
|---|---|---|
| 經文只能來自 `data/{mat,mrk,luk,jhn}.json`；網頁只用 fetch 讀 JSON，原始碼不可寫死經文 | **遵守** | 四卷 JSON 與 HEAD 位元組相同；`verify_text.py` 678 等全相符；新頁面 8 字窗掃描 0 筆；兩頁皆走 `Bible.load` |
| `.verify/` 必須在 `bible-site/` 上一層 | **遵守** | `.verify/` 存在於專案根，`bible-site/.verify` 不存在；未執行 `build_data.py`，路徑未變動 |
| 不載入外部資源 | **遵守** | 全 `site/` 0 筆外部 URL／`@import`；媒體為本機 `assets/` 檔案 |
| 介面全部繁體中文 | **遵守** | 新檔案（`home.html`、`blessing.html`、`blessing.json`、`index.html`、`app.js`、`style.css`）簡體字掃描 0 命中；`lang="zh-Hant"` |
| 模型自稱「測試全過」不可信，一律以外部腳本為準 | **遵守** | 本報告所有結論均來自實跑腳本與獨立探測，未引用任何模型自述 |
| 完成標準 `check_all.py` 結束碼 0 | **遵守** | 3/3，結束碼 0 |

## 加分驗證：檢查不是空的（mutation test）

為排除「檢查寫得太鬆、什麼都給過」的假陽性，我在 `/tmp` 的**隔離副本**上植入 5 種缺陷（未動專案檔），確認對應檢查都會失敗：

| 植入缺陷 | 被哪一項抓到 | 結束碼 |
|---|---|---|
| `blessing.html` 插入真實經文 | 「沒有寫死經文」（`site_checks` 與 `verify_text.py` 都抓到） | 1 |
| `home.html` 加入 CDN 外部樣式 | 「沒有載入外部資源」 | 1 |
| 320px 主題按鈕改成不等寬 | 「320px 四顆主題按鈕 2×2 等寬等高」 | 1 |
| 根目錄轉址改回 `site/index.html` | 「根目錄 index.html 三處都指向 site/home.html」 | 1 |
| `--grep` 打錯字（無匹配） | 「`--grep` 沒有對到任何檢查」 | 1 |

前輪 `FRONTEND-REVIEW-BLESSING-STYLE.md` 提出的 3 項不通過，本次複驗確認**都已修好**：

- 5-1 `--grep` 假陽性 → 已有 `if ONLY and not results` 防護，實測結束碼 1。
- 5-2 2×2 只量單一寬度 → 已改為在 320／375／1000px 各量一次。
- 6-1 320px 按鈕不等寬 → 實測 132/132/132/132，已等寬。

## 附註與非阻擋建議

1. **未執行 `build_data.py`**（依指示）。因此「`build_data.py` 能否由 `.verify/` 重建四卷 JSON」這一點本次**未驗證**；不過 `verify_text.py` 已用同一 `parse()` 逐節比對來源與產物，資料一致性仍受保障。
2. **`<mark>` 深色樣式**：搜尋關鍵字在深色模式仍是瀏覽器預設黃底黑字（對比約 19.5:1，可讀性無虞），屬觀感取捨，非缺陷，可不改。
3. **媒體素材授權**：`jordan.jpg`、`home-music.mp3` 由 ffmpeg 產生（檔頭 `Lavc/Lavf`），任務規格只寫「素材已放好」，專案內**沒有授權或來源紀錄**。若網站要公開發布，建議補一份素材來源／授權說明。此為建議，不影響本次驗收。
4. **導覽列同時有「經文卡片」與「抽經文卡」**：兩者功能不同（自選章節製卡 vs. 隨機抽祝福卡），符合 `tasks/62` 規格，非重複。
5. 本驗收只讀：專案工作區在驗收前後皆為同樣 28 項變更，`data/*.json` 時間戳未變，8090／8091 的 PID（1439868／1439888）與啟動時間未變。
