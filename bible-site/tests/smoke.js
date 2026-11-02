// Smoke test: verse counts per chapter in data/<key>.json for the four Gospels, plus required site files.
// The per-chapter counts are frozen here on purpose (source numbering: Luke 1:1-2 and 2:34-35 are one verse
// each, John 7:53 is folded into 8:1), so an accidental change to the data or the converter is caught.
const fs = require("fs"), path = require("path");
const root = path.join(__dirname, "..");
const expect = {
  mat: [25, 23, 17, 25, 48, 34, 29, 34, 38, 42, 30, 50, 58, 36, 39, 28, 27, 35, 30, 34, 46, 46, 39, 51, 46, 75, 66, 20],
  mrk: [45, 28, 35, 41, 43, 56, 37, 38, 50, 52, 33, 44, 37, 72, 47, 20],
  luk: [79, 51, 38, 44, 39, 49, 50, 56, 62, 42, 54, 59, 35, 35, 32, 31, 37, 43, 48, 47, 38, 71, 56, 53],
  jhn: [51, 25, 36, 54, 47, 71, 52, 59, 41, 42, 57, 50, 38, 31, 27, 33, 26, 40, 42, 31, 25],
};
let fail = 0, grand = 0;
for (const [key, counts] of Object.entries(expect)) {
  const file = path.join(root, "data", key + ".json");
  if (!fs.existsSync(file)) { fail++; console.log(`不通過：缺少 data/${key}.json`); continue; }
  const data = JSON.parse(fs.readFileSync(file, "utf8"));
  data.chapters.forEach((c, i) => {
    if (c.verses.length !== counts[i]) { fail++; console.log(`不通過：${data.book} 第 ${c.ch} 章 ${c.verses.length} 節，應為 ${counts[i]}`); }
  });
  const total = data.chapters.reduce((n, c) => n + c.verses.length, 0);
  const want = counts.reduce((a, b) => a + b, 0);
  grand += total;
  console.log(`${data.book}：章數 ${data.chapters.length}/${counts.length}，總節數 ${total}/${want}`);
  if (data.chapters.length !== counts.length || total !== want) fail++;
}
console.log(`四福音總節數 ${grand}/3776`);
if (grand !== 3776) fail++;
for (const f of ["index.html", "chapter.html", "search.html", "card.html", "style.css", "app.js"]) {
  if (!fs.existsSync(path.join(root, "site", f))) { fail++; console.log(`不通過：缺少 site/${f}`); }
}
console.log(fail ? `結果：不通過（${fail} 項）` : "結果：全部通過");
process.exit(fail ? 1 : 0);
