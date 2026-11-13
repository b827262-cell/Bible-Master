---
pane: w2:p5
role: qwen
files:
  - bible-site/tools/build_public.py
depends:
  - 132-weekly-wire-data-home
timeout_min: 10
checks:
  - python3 bible-site/tests/deploy_checks.py
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署。
**重要：請勿呼叫 `AskUserQuestion`，也切勿執行含 `<<'PY'` 多行 heredoc 的 bash 指令，只執行單行指令即可。**

請更新 `bible-site/tools/build_public.py`（對應 `brief-20261113-weekly-wire.md` 第 3 節）：
1. 將 `"home-week.json"` 納入 `DATA_FILES`（當 `data/home-week.json` 不存在時，建置流程不可失敗，維持正常略過）。
2. 在 `referenced_assets()` 中，若 `bible-site/data/home-week.json` 存在且為合法 JSON，讀取 `days[*].image`（`assets/...`），確保 7 張封面圖全部被複製進 `dist/site/assets/`。
3. 執行 `python3 bible-site/tests/deploy_checks.py` 確認全數通過。
