// Smoke test: verse counts per chapter in data/mark.json, plus required site files.
const fs = require("fs"), path = require("path");
const root = path.join(__dirname, "..");
const expect = [45, 28, 35, 41, 43, 56, 37, 38, 50, 52, 33, 44, 37, 72, 47, 20];
const data = JSON.parse(fs.readFileSync(path.join(root, "data", "mark.json"), "utf8"));
let fail = 0;
data.chapters.forEach((c, i) => {
  if (c.verses.length !== expect[i]) { fail++; console.log(`不通過：第 ${c.ch} 章 ${c.verses.length} 節，應為 ${expect[i]}`); }
});
const total = data.chapters.reduce((n, c) => n + c.verses.length, 0);
console.log(`章數 ${data.chapters.length}/16，總節數 ${total}/678`);
if (data.chapters.length !== 16 || total !== 678) fail++;
for (const f of ["index.html", "chapter.html", "search.html", "card.html", "style.css", "app.js"]) {
  if (!fs.existsSync(path.join(root, "site", f))) { fail++; console.log(`不通過：缺少 site/${f}`); }
}
console.log(fail ? `結果：不通過（${fail} 項）` : "結果：全部通過");
process.exit(fail ? 1 : 0);
