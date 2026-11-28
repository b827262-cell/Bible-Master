# 福音藝廊（音樂與經文圖區）設計與 AI 配樂提示詞規格單

> 本區定位為**極簡沉浸式「只放音樂與經文圖」專區**（前台入口：`bible-site/site/gallery.html`），設定檔位於 `bible-site/data/gospel-gallery.json`。
> 嚴守專案鐵則：所有經文原文均由前端執行期從 `bible-site/data/{mat,mrk,luk,jhn}.json` 動態讀取，不在 HTML／JS／JSON 或圖檔內寫死經文。

## 一、視覺與圖檔規格

- **畫風**：寬幅電影感油畫光影風景（16:9 橫式，`1600×900` JPG，單檔 1 MB 以內）。
- **畫面守則**：圖內不放任何文字、字母或浮水印；不正面畫耶穌面容；畫面底部約 25% 保持深沉柔和陰影，確保經文字幕高對比易讀。
- **預設檔名**：`bible-site/site/assets/gallery-1-mon.jpg` ～ `gallery-7-sun.jpg`。

## 二、音樂規格與日後替換站長 AI 音樂方式

- **初版內建配樂**：由 `python3 bible-site/tools/generate_gallery_music.py` 依每節經文之調性、速度與情緒合成 7 首無縫循環柔和器樂（`gallery-1-mon.wav` ～ `gallery-7-sun.wav`，每首約 1.1–1.4 MB），零外部資源、全瀏覽器原生支援。
- **替換為站長自製 AI MP3 流程**：
  1. 依下方各日 AI 配樂提示詞（適用 Suno / Udio 等工具）生成純器樂 MP3（建議 128 kbps、單檔 3 MB 以內、無語音人聲）。
  2. 將 MP3 放入 `bible-site/site/assets/`（例如 `gallery-1-mon.mp3`），並於 `bible-site/data/gospel-gallery.json` 將該日 `"audio"` 欄位改為 `"assets/gallery-1-mon.mp3"`。
  3. 同步在 `bible-site/ASSETS-LICENSE.md` 登記來源與日期，跑 `python3 bible-site/tools/check_all.py` 與 `python3 bible-site/tests/deploy_checks.py` 即可發佈。

---

## 三、一週七日「經文 × 油畫 × 音樂」企劃表與 AI 配樂提示詞

| 日次 | 主題 | 經文出處 | 調性與速度 | AI 配樂提示詞（Pure Instrumental, No Vocals） |
| --- | --- | --- | --- | --- |
| 週一 | 清晨禱告 | 馬可福音 1:35 | D 大調・60 BPM | `Contemplative solo felt piano and soft distant strings in D major, 60 BPM, pre-dawn stillness slowly warming into gentle sunrise glow, spacious cathedral reverb, devotional peaceful mood, purely instrumental, no vocals, seamless gentle ending` |
| 週二 | 先求神國 | 馬太福音 6:33 | G 大調・68 BPM | `Uplifting acoustic harp arpeggios with warm cello and airy strings in G major, 68 BPM, golden morning sunlight over open Galilean hills, hopeful serene pastoral mood, purely instrumental, no vocals` |
| 週三 | 風浪平靜 | 馬可福音 4:39 | C 小調轉 C 大調・58 BPM | `Cinematic ambient felt piano and deep cello starting in reflective C minor and resolving into radiant peaceful C major, 58 BPM, storm clouds parting over glassy calm sea, deep release and tranquility, purely instrumental, no vocals` |
| 週四 | 活水泉源 | 約翰福音 4:14 | F 大調・72 BPM | `Flowing crystalline Celtic harp and soft piano with gentle flute harmonies in F major, 72 BPM, sparkling clear spring water flowing gently through a sunlit valley, refreshing living water mood, purely instrumental, no vocals` |
| 週五 | 祈求尋見 | 路加福音 11:9 | A 小調轉 C 大調・64 BPM | `Intimate warm acoustic guitar and felt piano moving gently from tender A minor to welcoming C major, 64 BPM, golden light pouring through an open wooden door at twilight, earnest prayer answered with grace, purely instrumental, no vocals` |
| 週六 | 上好福分 | 路加福音 10:42 | Eb 大調・56 BPM | `Minimalist meditative warm piano with soft ambient string pad in Eb major, 56 BPM, quiet afternoon sunbeams in a peaceful room, unhurried rest and stillness, purely instrumental, no vocals` |
| 週日 | 生命的光 | 約翰福音 8:12 | Bb 大調・66 BPM | `Radiant uplifting orchestral strings, warm piano, and subtle chimes swelling gently in Bb major, 66 BPM, golden morning sunbeams breaking through olive groves, joyful light overcoming darkness, purely instrumental, no vocals` |
