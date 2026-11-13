---
pane: w2:p1
role: codex
files:
  - bible-site/REVIEW-weekly-cover.md
  - bible-site/screenshots-weekly/mon-375.png
  - bible-site/screenshots-weekly/mon-1440.png
  - bible-site/screenshots-weekly/tue-375.png
  - bible-site/screenshots-weekly/tue-1440.png
  - bible-site/screenshots-weekly/wed-375.png
  - bible-site/screenshots-weekly/wed-1440.png
  - bible-site/screenshots-weekly/thu-375.png
  - bible-site/screenshots-weekly/thu-1440.png
  - bible-site/screenshots-weekly/fri-375.png
  - bible-site/screenshots-weekly/fri-1440.png
  - bible-site/screenshots-weekly/sat-375.png
  - bible-site/screenshots-weekly/sat-1440.png
  - bible-site/screenshots-weekly/sun-375.png
  - bible-site/screenshots-weekly/sun-1440.png
depends:
  - 134-weekly-wire-admin
timeout_min: 20
checks:
  - python3 -c 'import os; r=open("bible-site/REVIEW-weekly-cover.md",encoding="utf-8").read().splitlines(); assert len(r)>=3 and r[2].strip() in ("**狀態：PASS**","**狀態：FAIL**"); d="bible-site/screenshots-weekly"; pngs=[f for f in os.listdir(d) if f.endswith(".png")]; assert len(pngs)==14'
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。本任務為唯讀審查，只能建立或修改 `bible-site/REVIEW-weekly-cover.md` 與 `bible-site/screenshots-weekly/` 下 14 張 PNG，不可修改網站程式碼或資料，不可 commit／push／部署。
**重要：請勿透過 TUI 提問等待使用者確認（不要呼叫 request_user_input），直接完成審查與截圖。**

請依 `bible-site/logs/herdr-dispatch/brief-20261113-weekly-wire.md` 進行唯讀審查：
1. 以無頭 Chrome 擷取 `home.html?day=1` … `home.html?day=7` 在 `375px` 與 `1440px` 共 14 張截圖（`mon-375.png`, `mon-1440.png`, …, `sun-375.png`, `sun-1440.png`）並實際檢視，確認七天封面、主體裁切（`object-position`）、經文光色與對比、不重疊圖片、無水平溢出皆正常。
2. 確認 `check_all.py`、`visual_checks.py`、`deploy_checks.py`、`service_checks.py homeadmin admin` 皆通過（請在隔離副本執行，避免覆寫報告）。
3. 產出 `bible-site/REVIEW-weekly-cover.md`（第 3 行必須為 `**狀態：PASS**` 或 `**狀態：FAIL**`），簡述七天截圖與檢查結果，並附上後續建議（例如逐日編輯功能留待下一輪）。
