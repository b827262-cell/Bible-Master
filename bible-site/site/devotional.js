(function () {
  'use strict';
  Bible.nav('devotional.html');
  const date = document.getElementById('reading-date');
  const status = document.getElementById('reading-status');
  const container = document.getElementById('reading');
  const books = { MAT: 'mat', MRK: 'mrk', LUK: 'luk', JHN: 'jhn' };
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit', day: '2-digit'
  }).formatToParts(new Date());
  const component = (name) => parts.find((part) => part.type === name).value;
  date.value = `${component('year')}-${component('month')}-${component('day')}`;
  date.max = date.value; // 每日上架：只開放到今天

  let entries = [];
  let generation = 0;

  function add(parent, tag, text) {
    const node = document.createElement(tag);
    node.textContent = text;
    parent.appendChild(node);
    return node;
  }

  async function display() {
    const request = ++generation;
    container.replaceChildren();
    const match = entries.find((entry) => entry.devotional_date === date.value);
    if (!match) {
      status.textContent = '此日期尚無已審核的禱讀內容。';
      return;
    }
    status.textContent = '正在載入經文…';
    try {
      const passages = await Promise.all(match.ranges.map(async (range) => {
        const key = books[range.book];
        if (!key) throw new Error('不支援的書卷');
        const data = await Bible.load(key);
        const verses = [];
        data.chapters.forEach((chapter) => {
          if (chapter.ch < range.start_chapter || chapter.ch > range.end_chapter) return;
          chapter.verses.forEach((verse) => {
            if (chapter.ch === range.start_chapter && range.start_verse && (verse.end || verse.v) < range.start_verse) return;
            if (chapter.ch === range.end_chapter && range.end_verse && verse.v > range.end_verse) return;
            const label = verse.end ? `${verse.v}–${verse.end}` : String(verse.v);
            verses.push(`${chapter.ch}:${label} ${verse.text}`);
          });
        });
        return verses;
      }));
      if (request !== generation) return;
      if (!passages.length || passages.some((p) => !p.length)) throw new Error('找不到經文');
      status.textContent = '';
      add(container, 'h2', match.title || match.scripture_reference);
      if (match.title) add(container, 'p', match.scripture_reference);
      add(container, 'h3', '經文');
      passages.flat().forEach((verse) => add(container, 'p', verse));
      [['默想', 'summary'], ['反思', 'reflection'], ['禱告', 'prayer']].forEach(([title, key]) => {
        if (match[key]) { add(container, 'h3', title); add(container, 'p', match[key]); }
      });
    } catch (error) {
      if (request === generation) status.textContent = '經文載入失敗，請稍後再試。';
    }
  }

  date.addEventListener('change', display);
  fetch('../data/devotional.json').then((response) => {
    if (response.status === 404) return [];
    if (!response.ok) throw new Error('資料載入失敗');
    return response.json();
  }).then((data) => {
    if (!Array.isArray(data)) throw new Error('資料格式錯誤');
    entries = data;
    display();
  }).catch(() => { status.textContent = '禱讀資料載入失敗，請稍後再試。'; });
}());
