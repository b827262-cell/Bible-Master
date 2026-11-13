---
pane: w2:p5
role: qwen
files: [bible-site/tools/herdr_team.py]
timeout_min: 20
checks:
  - python3 -m py_compile bible-site/tools/herdr_team.py
  - python3 bible-site/tools/herdr_team.py status
  - python3 bible-site/tools/herdr_team.py status | grep -q "w2:p6.*agy"
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，只能更改 front matter 允許的檔案 `bible-site/tools/herdr_team.py`（若發現暫存檔請勿新增，先移除前次代理誤貼的重複區塊）。

請清理並補齊 `bible-site/tools/herdr_team.py` 的團隊表與說明：

1. **修復前次代理重複貼上的區塊並將 `w2:p6`（`agy`）加入 `TEAM` 表**：
   - 目前檔案內第 49–108 行與第 110–139 行有一段前次代理誤貼的重複 `TEAM`／import 區塊（第二個 `TEAM` 覆蓋了第一個 `TEAM`），請移除重複區塊，只保留單一乾淨的結構。
   - 在唯一的 `TEAM` 清單中加入 `w2:p6`：
     `{"pane": "w2:p6", "duty": "PM 調度／前端與生圖", "roles": ["agy", "image"]}`
   - 更新檔案頂部 docstring 的角色說明，列入 `agy/image`。
2. **評估並妥善標示 `w2:p4`（CodeBuddy）與 `w2:p8`（總PM Claude）**：
   - `w2:p4`（CodeBuddy）：因為 Herdr 的 `agent` 清單尚未支援 `codebuddy`，`herdr pane list` 中 `agent` 為空且 `agent_status` 恆為 `unknown`。若硬補 `herdr pane run` 分支，將無法透過 `herdr agent wait` 偵測完成或 `blocked` 審批狀態，也容易在互動式 TUI 產生競態風險，因此評估結論為**不補 `pane run` 自動派工分支，維持手動派發**。
   - 在 docstring 與程式內（`MANUAL_PANES` 字典：`"w2:p4": "CodeBuddy（Herdr 未識別 agent，手動派發）"`, `"w2:p8": "Claude（總PM，負責統籌與發佈）"`）清楚註明，讓 `herdr_team.py status` 顯示這些已知手動／總PM pane 的說明，而不再顯示突兀的 `←不在團隊映射`。
   - 將 `"bible-site/TEST-REPORT.md"` 與 `"bible-site/FAILS.md"` 加入 `IGNORE_FILES`，並將 `"bible-site/design/"` 與 `"output/"` 加入 `IGNORE`（避免生圖或設計稿預覽影響範圍檢查）。
3. **驗證與回報**：
   - 執行 `python3 -m py_compile bible-site/tools/herdr_team.py`
   - 執行 `python3 bible-site/tools/herdr_team.py status`
   - 用 `python3 bible-site/tools/herdr_team.py run bible-site/tasks/112-herdr-team-roster.md --dry-run` 測試解析輸出。
   - 在回覆中附上 `status` 輸出、`--dry-run` 輸出，以及對 `w2:p4` 為何不補 `pane run` 分支的評估摘要。
