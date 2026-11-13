---
pane: w2:p1
role: codex
files:
  - output/imagegen/weekly-cover-20261113/cover-4-thu.jpg
  - output/imagegen/weekly-cover-20261113/cover-5-fri.jpg
  - output/imagegen/weekly-cover-20261113/cover-6-sat.jpg
  - output/imagegen/weekly-cover-20261113/cover-7-sun.jpg
  - output/imagegen/weekly-cover-20261113/PROPOSAL.md
  - output/imagegen/weekly-cover-20261113/weekly.json
  - output/imagegen/weekly-cover-20261113/contact-sheet.jpg
timeout_min: 30
checks:
  - python3 -c 'import os, json; from PIL import Image; d="output/imagegen/weekly-cover-20261113"; names=["cover-1-mon.jpg","cover-2-tue.jpg","cover-3-wed.jpg","cover-4-thu.jpg","cover-5-fri.jpg","cover-6-sat.jpg","cover-7-sun.jpg"]; assert all(os.path.exists(f"{d}/{n}") and os.path.getsize(f"{d}/{n}")<=600*1024 for n in names); assert all(Image.open(f"{d}/{n}").size[0]>=1600 and abs(Image.open(f"{d}/{n}").size[0]/Image.open(f"{d}/{n}").size[1]-16/9)<0.03 for n in names); w=json.load(open(f"{d}/weekly.json",encoding="utf-8")); assert isinstance(w,list) and len(w)==7 and [x["day"] for x in w]==[1,2,3,4,5,6,7]; assert all(set(x.keys())=={"day","theme","book","ch","v","image","alt","light"} for x in w); assert os.path.exists(f"{d}/PROPOSAL.md") and os.path.exists(f"{d}/contact-sheet.jpg")'
---
所有操作都在 /home/b827262/project/AI/Bible-Master 這一棵工作樹完成。不要 commit／push／部署，不修改 `bible-site/site/`、`bible-site/data/`、`admin/`、測試；只能建立或修改 front matter 列出的 `output/imagegen/weekly-cover-20261113/` 檔案。
**重要：請勿透過 TUI 提問等待使用者確認（不要呼叫 request_user_input），直接執行完成所有交付物。**

請完整閱讀 `/home/b827262/project/AI/Bible-Master/bible-site/logs/herdr-dispatch/brief-20261113-weekly-cover.md`。
AGY（w2:p6）已先定好一週七天主題表（確保不撞題、整週有平日工作得力到週末安息敬拜的起伏），並已生成星期一～三（`cover-1-mon.jpg`、`cover-2-tue.jpg`、`cover-3-wed.jpg`，已放在 `output/imagegen/weekly-cover-20261113/`）。

### 固定七天主題與經文座標表（經文務必從 `bible-site/data/{book}.json` 程式讀取原文，不可手打）

| 星期 (`day`) | 圖檔 (`image`) | 設計者 | 主題 (`theme`) | 座標 (`book` `ch`:`v`) | 狀態 |
| --- | --- | --- | --- | --- | --- |
| 1（星期一） | `cover-1-mon.jpg` | AGY（w2:p6） | `清晨禱告` | `mrk` 1:35 | 已完成（圖檔已在目錄中，`light`: `#fae1c5`，`alt`: `破曉時分的加利利曠野山丘，柔和晨光穿過古橄欖樹枝葉灑在安靜跪禱的身影上，右側延伸向幽靜的晨霧山谷。`，生成模型：`AGY Google Imagen 3`） |
| 2（星期二） | `cover-2-tue.jpg` | AGY（w2:p6） | `先求神國` | `mat` 6:33 | 已完成（圖檔已在目錄中，`light`: `#f9e2bc`，`alt`: `溫暖晨光斜照在加利利山坡的白色野百合與金黃麥穗上，兩隻麻雀展翅飛過光束，右側遠眺平靜的湖面與遠山。`，生成模型：`AGY Google Imagen 3`） |
| 3（星期三） | `cover-3-wed.jpg` | AGY（w2:p6） | `風浪平靜` | `mrk` 4:39 | 已完成（圖檔已在目錄中，`light`: `#fdebcb`，`alt`: `風暴止息後的加利利海，烏雲向右側散開，溫暖金白陽光從左上穿雲照亮古木船與平靜如鏡的金色水面。`，生成模型：`AGY Google Imagen 3`） |
| 4（星期四） | `cover-4-thu.jpg` | Codex（w2:p1） | `活水泉源` | `jhn` 4:14 | **請由 Codex 生成** |
| 5（星期五） | `cover-5-fri.jpg` | Codex（w2:p1） | `祈求尋見` | `luk` 11:9 | **請由 Codex 生成** |
| 6（星期六） | `cover-6-sat.jpg` | Codex（w2:p1） | `上好福分` | `luk` 10:42 | **請由 Codex 生成** |
| 7（星期日） | `cover-7-sun.jpg` | Codex（w2:p1） | `生命的光` | `jhn` 8:12 | **請由 Codex 生成** |

### 請你完成的步驟

1. **生成星期四～日 4 張封面圖（`cover-4-thu.jpg`、`cover-5-fri.jpg`、`cover-6-sat.jpg`、`cover-7-sun.jpg`）**：
   - 使用你的 OpenAI `image_gen` 工具生成寫實攝影風格母圖（可先參考 `bible-site/site/assets/jordan.jpg` 與已產出的 `cover-1-mon.jpg`～`cover-3-wed.jpg`）：
     - **星期四 `cover-4-thu.jpg`（`活水泉源`，約翰福音 4:14）**：第一世紀撒瑪利亞古石井與湧出的清澈泉水，溫暖金光從左上方斜照在古石井與陶罐上，泉水在畫面左中側泛起透亮金光，右側為柔和開闊的橄欖山谷。
     - **星期五 `cover-5-fri.jpg`（`祈求尋見`，路加福音 11:9）**：第一世紀猶太石砌庭院半開的厚重木門（位於畫面左中側），溫暖醇厚的夕陽金光從敞開的門縫傾瀉而出照亮石板地面，右側為安靜溫潤的石牆與光影。
     - **星期六 `cover-6-sat.jpg`（`上好福分`，路加福音 10:42）**：第一世紀伯大尼溫暖靜謐的石屋窗畔（畫面左中側），柔和暖金色斜陽從窗格灑入，照在低矮木几上的羊皮卷與溫潤陶土油燈上，右側留有安靜柔和的空間。
     - **星期日 `cover-7-sun.jpg`（`生命的光`，約翰福音 8:12）**：主日清晨橄欖山巔的壯麗日出，燦爛溫暖的晨光從左上方穿透雲層，照亮左側蜿蜒山徑與橄欖樹冠（若有遠景人物須莊重自然、無臉手瑕疵），右側為遼闊寧靜的晨霧山谷。
   - **規格要求**：
     - 橫幅 16:9（至少 `1600×900`，建議統一存為 `1600×900`），JPG 格式，單檔 `<= 600 KB`（用 Pillow 控制 quality 壓縮，不裁切變形）。
     - **主體在畫面左側或左中側**，右側較開闊平緩。
     - 圖內不可有任何文字、字母、浮水印、標誌、邊框。
     - 量測每張圖照在主體上的溫暖光色 HEX（`#rrggbb`）並撰寫一句繁體中文圖說 `alt`（描述畫面，不引用經文）。
2. **產出 `output/imagegen/weekly-cover-20261113/weekly.json`**：
   - 7 筆陣列，每筆格式嚴格為：
     `{"day": 1..7, "theme": "...", "book": "mat|mrk|luk|jhn", "ch": 0, "v": 0, "image": "cover-1-mon.jpg", "alt": "...", "light": "#rrggbb"}`
   - **注意：`weekly.json` 內絕不可包含經文文字！**
3. **產出 `output/imagegen/weekly-cover-20261113/PROPOSAL.md`**：
   - **鐵則：不可憑記憶打經文！** 請用 Python 從 `bible-site/data/{book}.json` 讀出該節 `text` 原文寫入 `PROPOSAL.md`。
   - 包含完整七天提案表（一天一列：星期、設計者、主題、書卷章節、從 JSON 讀出的經文原文、圖檔、圖說、光色 HEX、生成模型與提示詞摘要）以及每張圖的尺寸與檔案大小驗證。
4. **產出總覽圖 `output/imagegen/weekly-cover-20261113/contact-sheet.jpg`**：
   - 用 Pillow 將 `cover-1-mon.jpg` … `cover-7-sun.jpg` 7 張縮圖排成兩列（例如上 4 下 3 或上 3 下 4），每張縮圖下方或上方用系統繁體中文字型標示「星期一｜清晨禱告（mrk 1:35）」等星期、主題與光色色票，存為 `contact-sheet.jpg`。
