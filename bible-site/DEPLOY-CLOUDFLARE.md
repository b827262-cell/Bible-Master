# 上架 Cloudflare Pages 與同步流程

目標網址：`https://bible.b827262.org/`。同步方向只有一個：**本機 → GitHub → Cloudflare Pages**。線上網站是純靜態，不能在線上編輯，所以不會有本機與線上不一致的問題。

## 一次性設定（需要你操作）

1. **GitHub**：建立一個**私有**儲存庫（例如 `Bible-Master`），不要勾選「加入 README」。
2. **本機**加上 remote（在專案根目錄）：
   ```bash
   git remote add origin git@github.com:<帳號>/<儲存庫>.git
   ```
3. **Cloudflare Dashboard** → Workers & Pages → Create → Pages → Connect to Git → 選剛才的儲存庫：
   | 項目 | 值 |
   |---|---|
   | Production branch | `main` |
   | Framework preset | None |
   | Build command | `python3 bible-site/tools/build_public.py` |
   | Build output directory | `dist` |
   | 環境變數（若建置失敗再加） | `PYTHON_VERSION` = `3.12` |
4. 部署完成後：該 Pages 專案 → Custom domains → Set up a custom domain → 輸入 `bible.b827262.org`。`b827262.org` 的 DNS 已在 Cloudflare，會自動建立 CNAME 並簽發 HTTPS 憑證。
5. 第一次推送：
   ```bash
   python3 bible-site/tools/publish.py          # 先推到 preview 分支，看預覽網址
   python3 bible-site/tools/publish.py --prod   # 確認沒問題再上線（推到 main）
   ```

## 日常流程

1. 在本機後台（`http://127.0.0.1:8091/`）的「主頁設定」換圖片、經文、音樂，或照常修改程式。
2. 在本機網站（`http://127.0.0.1:8090/`）確認外觀。
3. 執行 `python3 bible-site/tools/publish.py`：
   1. 跑 `check_all.py`（必須 3/3），不通過就中止；
   2. 跑後台檢查、建置 `dist/`、檢查發佈包（不含後台、測試、報告；單檔 < 25 MiB）；
   3. 列出將提交的檔案，**輸入 `yes` 才會提交**；
   4. 推送到 `origin/preview`，Cloudflare 產生預覽網址（Dashboard → Pages → Deployments）。
4. 預覽網址確認沒問題，再執行 `python3 bible-site/tools/publish.py --prod` 上線。
5. 只想先驗證、不動 git：加 `--dry-run`。

## 發佈的內容

`dist/` 只包含：`index.html`、`site/`（頁面與素材）、`data/`（四卷經文、`blessing.json`、`home.json`）、`_headers`。不會發佈 `admin/`、`tests/`、`tools/`、`.md` 報告、`.verify/`、`logs/`。沒被 `home.json` 或頁面使用的上傳檔也不會發佈。

## 回滾

- Cloudflare Dashboard → Pages → Deployments → 選前一個版本 → Rollback。
- 或在本機 `git revert <commit>` 後再執行 `publish.py --prod`。

## 注意

- 後台的「儲存」只改本機檔案（`data/home.json`、`site/assets/`）；要上線一定要執行 `publish.py`。
- 後台寫入需要 token（`bible-site/admin/.token`，每次啟動重新產生，已被 `.gitignore` 排除），後台只應在本機使用。
- 圖片與音樂公開上線前，請在 `bible-site/ASSETS-LICENSE.md` 補上來源與授權。
