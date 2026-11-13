---
pane: w2:p5
role: qwen
files: [bible-site/REVIEW-devotional.md]
depends: [112-herdr-team-roster]
timeout_min: 20
checks:
  - test -s bible-site/REVIEW-devotional.md
  - sed -n '3p' bible-site/REVIEW-devotional.md | grep -Eq '^\*\*狀態：(PASS|FAIL)\*\*$'
  - grep -q "^\*\*狀態：PASS\*\*$" bible-site/REVIEW-devotional.md
  - python3 bible-site/tests/site_checks.py devotional
  - python3 bible-site/tools/check_all.py
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，本任務是唯讀審查，唯一准許新增／修改的檔案為 `bible-site/REVIEW-devotional.md`（切勿改動正式工作樹其他檔案，也不要執行任何需要互動確認的複雜 `/tmp` 腳本，可直接查閱 `bible-site/logs/herdr-dispatch/111-devotional-site-checks-1-w2_p1.log` 與 `111-devotional-site-checks-2-w2_p1.log` 中已完成並驗證通過的突變測試紀錄，並執行下方非互動式檢查指令）。

請針對本次禱讀（devotional）自動化檢查與團隊編制更新進行最終審查，並將完整審查報告寫入 `bible-site/REVIEW-devotional.md`：

### 格式鐵則
- `bible-site/REVIEW-devotional.md` 的**第 3 行**必須精確為 `**狀態：PASS**` 或 `**狀態：FAIL**`（例如第 1 行 `# 禱讀（Devotional）最終審查報告`，第 2 行空行，第 3 行 `**狀態：PASS**`）。
- 全文使用繁體中文，不得出現簡體字或日文漢字。

### 審查項目
1. **檢查 `site_checks.py devotional` 覆蓋度與真實性**：
   - 是否能以 `python3 bible-site/tests/site_checks.py devotional` 單獨執行，且已納入 `check_all.py`？
   - 是否在 `/tmp` 臨時副本以假 `devotional.json` 測試，且**完全沒有寫死經文**（動態讀取 `bible-site/data/{mat,mrk,luk,jhn}.json` 逐節比對渲染出的經文與合併節）？
   - 是否涵蓋：有資料日期渲染、無資料日期／空陣列 `[]`／HTTP 404／損壞 JSON／非陣列 JSON／不支援書卷與無效範圍、預設台灣日期與切換日期、320/375/768/1440px 四種寬度無水平溢出、導覽列、無外部資源、無未捕捉 JS 錯誤？
   - **突變測試（Mutation Test）驗證紀錄**：記載在 `/tmp` 副本移除 `devotional.js` 章節結尾範圍判斷時，`site_checks.py devotional` 成功抓到兩項失敗（MAT 預期 12 節、實際 945 節；日期切換預期 6 節、實際 1842 節），且未污染正式工作樹。
2. **鐵則與保護檔案檢查**：
   - `bible-site/tests/site_checks.py`、`bible-site/site/devotional.html`、`bible-site/site/devotional.js` 是否有任何地方寫死經文？
   - `bible-site/data/{mat,mrk,luk,jhn,blessing,home,devotional}.json` 與 `.verify/` 是否完全未被改動？
3. **`check_all.py` 全套檢查與 `herdr_team.py` 編制檢查**：
   - 執行 `python3 bible-site/tests/site_checks.py devotional` 與 `python3 bible-site/tools/check_all.py` 確認 3/3 全綠。
   - 執行 `python3 bible-site/tools/herdr_team.py status` 確認 `w2:p6`（`agy`）已在 `TEAM` 表內，`w2:p4`（CodeBuddy）與 `w2:p8`（Claude）已清楚標示。
