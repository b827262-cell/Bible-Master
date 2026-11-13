---
pane: w2:p1
role: codex
files:
  - output/imagegen/heart-20261113/build_assets.py
  - output/imagegen/heart-20261113/README.md
  - output/imagegen/heart-20261113/heart-still.png
  - output/imagegen/heart-20261113/heart-idle-light.gif
  - output/imagegen/heart-20261113/heart-idle-dark.gif
  - output/imagegen/heart-20261113/heart-surprise-light.gif
  - output/imagegen/heart-20261113/heart-surprise-dark.gif
  - output/imagegen/heart-20261113/pattern-light.png
  - output/imagegen/heart-20261113/pattern-dark.png
  - output/imagegen/heart-20261113/pattern-preview.png
  - output/imagegen/heart-20261113/surprise-preview.png
  - output/imagegen/heart-20261113/v2/build_assets.py
  - output/imagegen/heart-20261113/v2/README.md
  - output/imagegen/heart-20261113/v2/heart-still.png
  - output/imagegen/heart-20261113/v2/heart-idle-light.gif
  - output/imagegen/heart-20261113/v2/heart-idle-dark.gif
  - output/imagegen/heart-20261113/v2/heart-surprise-light.gif
  - output/imagegen/heart-20261113/v2/heart-surprise-dark.gif
  - output/imagegen/heart-20261113/v2/pattern-light.png
  - output/imagegen/heart-20261113/v2/pattern-dark.png
  - output/imagegen/heart-20261113/v2/pattern-preview.png
timeout_min: 20
checks:
  - test -d output/imagegen/heart-20261113/v2
  - test -s output/imagegen/heart-20261113/v2/heart-surprise-light.gif
  - test -s output/imagegen/heart-20261113/v2/heart-surprise-dark.gif
  - test -s output/imagegen/heart-20261113/heart-surprise-light.gif
  - test -s output/imagegen/heart-20261113/heart-surprise-dark.gif
  - test -s output/imagegen/heart-20261113/surprise-preview.png
  - python3 -c 'import os; from PIL import Image; p="output/imagegen/heart-20261113"; assert os.path.getsize(f"{p}/heart-surprise-light.gif") < 600*1024 and os.path.getsize(f"{p}/heart-surprise-dark.gif") < 600*1024; im=Image.open(f"{p}/surprise-preview.png"); assert im.width >= 960 and im.height >= 480'
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，本任務**只做素材**，只能在 `output/imagegen/heart-20261113/` 內作業，不可修改 `bible-site/` 下任何檔案。

請依據 `bible-site/logs/herdr-dispatch/brief-20261113-round3.md` 的「A. 小驚喜光束修正」完成 v3 素材製作：

1. **保存現行 v2**：
   - 在 `output/imagegen/heart-20261113/` 下建立 `v2/` 目錄，將現行 v2 的檔案（`README.md`、`build_assets.py`、`heart-still.png`、`heart-idle-light.gif`、`heart-idle-dark.gif`、`heart-surprise-light.gif`、`heart-surprise-dark.gif`、`pattern-light.png`、`pattern-dark.png`、`pattern-preview.png`）移入 `v2/` 保存（保留 `v1/` 不動）。
2. **修正 `heart-surprise-{light,dark}.gif` 的結尾光束**：
   - **現行 v2 的問題**：結尾向上的金光是又細又實、上窄下寬的錐形（`top` 寬僅 8px、`bottom` 寬僅 28px），看起來像愛心頂上長了一根尖角。
   - **改為柔和的扇形光束**：
     - 底部寬度約為愛心寬度的 **35%–45%**（愛心寬約 `480 * 0.62 ≈ 298px`，故光束底部寬約 `105px–134px`），且**往上漸寬散開**成扇形光（上寬下窄的柔和展開扇面，或由多道柔和扇形光束組成，**絕不可有尖頂的實心錐**）。
     - 可用 **2–3 階實色**（配合淺色底 `#f3f6f2` 與深色底 `#0a1412` 各自適合的 2–3 階暖金／柔光色階，由內而外、由下而上階層變淡並散開，頂部以柔和圓弧或散開光點收尾，避免硬邊截斷）疊出柔和漸層感，或者直接繪製在心形圖層背後再疊上心形（`paste_heart` 在光束之上，使光束自然從心形上方凹槽背後往上散發，不會壓髒心形頂緣），在淺色底與深色底都要清楚好看、柔和自然。
     - 其餘設定維持不變：縮彈（0.9x → 1.12x → 1.0x）、四周光點、5 片小羽毛、待機動圖（`heart-idle-{light,dark}.gif`）、靜態圖（`heart-still.png`）、底紋（`pattern-{light,dark}.png`）、尺寸（480×480）、檔名、16 幀共 1.6 秒只播一次（不循環）、每個檔案 `< 600 KB`。
3. **產出分格預覽圖 `surprise-preview.png` 與更新 `README.md`**：
   - 產出 `output/imagegen/heart-20261113/surprise-preview.png`：展示淺色底（`#f3f6f2`）與深色底（`#0a1412`）下 `heart-surprise-{light,dark}.gif` 關鍵格（特別是光束升起與結尾幀）的分格預覽圖，並親自檢視確認沒有尖角錐形、光束柔和自然。
   - 更新 `output/imagegen/heart-20261113/README.md` 記錄 v3 規格、各檔位元組大小與 `v2/` 封存說明。
