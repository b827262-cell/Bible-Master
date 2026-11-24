# 148 Freebuff 單一實例對齊 `t7`、模擬測試與技能收斂計畫（t3 派工、PM 最終驗收）

## 一、背景與 PM 裁示

1. **維持單一 `t7` 實例，不另建 `t8`**：`bible-site/tools/freebuff_dispatch.py` 已實作唯一性保護（偵測到多個 `freebuff` 終端即視為 `ambiguous` 並以 `exit=2` 拒絕派工）；本機實際運行於 `t7`，若另開 `t8` 反而造成多實例阻擋與時間制額度雙重消耗。
2. **消除預設假警報，保留動態解析**：將預設預期終端由 `t8` 對齊為 `t7`，使本機常態執行與 `--dry-run` 回報 `expected_terminal: "t7"`、`terminal_mismatch: false`；底層仍維持 `resolve: dynamic` 動態探索，不硬編碼 tab id 或 pane id。
3. **零額度消耗驗證**：本任務所有驗證均走全模擬測試（`freebuff_dispatch_checks.py`）與 `--dry-run`，嚴禁向真實 `t7` 發送對話消耗 Freebuff 額度。

---

## 二、分派架構（由總工程師 `t3` 派工執行，檔案嚴格不重疊）

### 子任務 A — 程式預設值與模擬測試擴充（建議派給 `t4` Mistral Vibe）
- **准改檔案**（僅限此 2 檔）：
  - `bible-site/tools/freebuff_dispatch.py`
  - `bible-site/tests/freebuff_dispatch_checks.py`
- **實作項目**：
  1. `bible-site/tools/freebuff_dispatch.py`：將 `DEFAULT_EXPECTED_TERMINAL = "t8"` 改為 `"t7"`，並將檔頭說明範例中的 `--terminal t8` / `FREEBUFF_T8_OK` 同步調整為 `t7` / `FREEBUFF_OK`。
  2. `bible-site/tests/freebuff_dispatch_checks.py`：保留既有 15 項負向與防護測試（包含以 `--expected-terminal t8 --require-expected` 測試不符中止、多終端 `ambiguous`、舊回覆排除、併發鎖、重複阻擋等），並新增第 16 項檢查：驗證預設參數執行 `--dry-run --json` 對單一 `t7` 終端回傳 `expected_terminal == "t7"` 且 `terminal_mismatch is False`。
- **子任務檢查**：
  - `python3 -B bible-site/tests/freebuff_dispatch_checks.py`（16/16 通過）
  - `python3 -B bible-site/tools/freebuff_dispatch.py --dry-run --json`（確認 `terminal == "t7"`、`terminal_mismatch == false`，不送任何按鍵）

### 子任務 B — 角色設定、文件與隨庫技能同步（建議派給 `t6` Kilo CLI）
- **准改檔案**（僅限此 3 檔，另可同步更新本機 `~/.codebuddy/skills/herdr-freebuff-dispatch/SKILL.md`）：
  - `bible-site/tools/dispatch/roles.yml`
  - `bible-site/AGENT-ROLES.md`
  - `skills/herdr-freebuff-dispatch/SKILL.md`
- **實作項目**：
  1. `bible-site/tools/dispatch/roles.yml`：將 `freebuff.dispatch.terminal` 由 `t8` 改為 `t7`，維持 `manual: true`、`resolve: dynamic`、`guards: [lock, duplicate]` 與 `checks: bible-site/tests/freebuff_dispatch_checks.py`，註解標明維持單一 `t7` 實例以避免 `ambiguous` 衝突與額度消耗。
  2. `bible-site/AGENT-ROLES.md`：更新 `freebuff` 終端欄位說明為預設預期 `t7`、實際依 `foreground.argv` 檔名動態解析，不另開第二實例。
  3. `skills/herdr-freebuff-dispatch/SKILL.md`（及 `~/.codebuddy/skills/herdr-freebuff-dispatch/SKILL.md`）：將預設範例與提示由 `t8` 校正為 `t7`，保留動態探索與不硬編碼原則。
- **子任務檢查**：
  - `python3 -c 'import yaml; d = yaml.safe_load(open("bible-site/tools/dispatch/roles.yml")); assert d["roles"]["freebuff"]["manual"] is True and d["roles"]["freebuff"]["dispatch"]["terminal"] == "t7"'`
  - `git diff --check`

### 子任務 C — 總工程師 `t3` 整合複驗與交由 `t2` 提交推送
1. `t3` 收回 `t4`、`t6` 成果後，在工作樹執行整合檢查（不得對 `t7` 發送真實 prompt）：
   - `python3 -B bible-site/tests/freebuff_dispatch_checks.py`（16/16 通過）
   - `python3 -B bible-site/tools/freebuff_dispatch.py --dry-run --json`
   - `python3 -B bible-site/tools/dispatch.py health`（確認 `freebuff` 維持手動角色）
   - `python3 bible-site/tools/check_all.py`（3/3 通過）
   - `git diff --check`（結束碼 0）
2. `t3` 檢查通過後，指派 `t2` 以明確檔案白名單（禁止 `git add -A` / `git add .`，保留未引用之 `bible-site/site/assets/upload-20261103-153327-4d72.jpg` 不納入）提交以下檔案並執行 `git pull --rebase origin main` 與 `git push origin main`：
   - `bible-site/tasks/148-freebuff-t7-align.md`
   - `bible-site/tools/freebuff_dispatch.py`
   - `bible-site/tests/freebuff_dispatch_checks.py`
   - `bible-site/tools/dispatch/roles.yml`
   - `bible-site/AGENT-ROLES.md`
   - `skills/herdr-freebuff-dispatch/SKILL.md`
   - `bible-site/FAILS.md`
   - `bible-site/TEST-REPORT.md`
3. 推送完成後，由 `t3` 將派工與提交結果回報 PM（`t1`），由 **PM（`t1`）執行最終獨立驗收**。

---

## 三、PM 最終驗收標準（由 `t1` 獨立執行，不採信模型自述）

1. `python3 -B bible-site/tests/freebuff_dispatch_checks.py` → 結束碼 0，16/16 通過。
2. `python3 -B bible-site/tools/freebuff_dispatch.py --dry-run --json` → 結束碼 0，`terminal == "t7"`、`expected_terminal == "t7"`、`terminal_mismatch == false`。
3. `python3 bible-site/tools/check_all.py`（或核對最新報告與獨立 `verify_text.py` + `deploy_checks.py`）→ 全數通過。
4. `git status -sb` 與 `git log -n 2` → 本地 `HEAD` 與 `origin/main` 同步 `0/0`，`git diff --check` 為 0，且未消耗任何額外 Freebuff 對話回合。
