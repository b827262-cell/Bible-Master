---
role: e500
files: [start.sh]
depends: [91-launcher-entry-url]
checks:
  - python3 bible-site/tests/launcher_checks.py syntax entry data
  - python3 bible-site/tests/service_checks.py service
---
只改專案根目錄的 `start.sh`（`service.sh` 是指向它的符號連結，不要動）。上一個任務已經改過入口網址那幾行，不要再動它們。
`check_environment`（第 78 行附近）現在只檢查馬太與馬可：

```bash
if [ ! -f "${SITE_ROOT}/data/mat.json" ] || [ ! -f "${SITE_ROOT}/data/mrk.json" ]; then
  ... python3 "${SITE_ROOT}/tools/build_data.py" ...
fi
```

請改成：
1. 條件擴大成四卷：`mat.json`、`mrk.json`、`luk.json`、`jhn.json` 任何一個不存在，才印警告並執行 `build_data.py`。整個 `if [ ... ]; then` 條件寫在同一行或相鄰行都可以，但這四個 `data/<卷>.json` 字樣都要出現在條件裡。
2. 在這個 `if ... fi` **之後**另外加一個獨立檢查：若 `"${SITE_ROOT}/data/blessing.json"` 不存在，只呼叫 `print_warn "缺少 blessing.json，抽經文卡功能將無法使用"`。`blessing.json` 不是 `build_data.py` 產出的，所以這個警告附近**不可以**呼叫 `build_data.py`，也不可以讓腳本因此結束（只警告，繼續啟動）。
3. 其餘不動；介面文字全部繁體中文。

改完請跑：`bash -n start.sh`、`python3 bible-site/tests/launcher_checks.py syntax entry data`。不要啟動或停止任何服務（線上 8090/8091 不可碰）。
