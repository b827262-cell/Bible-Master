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

  function add(parent, tag, text, className) {
    const node = document.createElement(tag);
    node.textContent = text;
    if (className) node.className = className;
    parent.appendChild(node);
    return node;
  }

  /* 狀態列三態：busy 的文字一律以「正在」兩個字開頭，探測頁就是靠這個線索判斷渲染結束了沒有；
     渲染成功時 data-state 與文字一起清掉；沒有資料或出錯才用 fix，文字要講清楚下一步該怎麼做。 */
  function setStatus(state, text) {
    if (state) status.dataset.state = state;
    else delete status.dataset.state;
    status.textContent = text;
  }
  setStatus('busy', '正在載入禱讀資料…');

  async function display() {
    const request = ++generation;
    container.replaceChildren();
    const match = entries.find((entry) => entry.devotional_date === date.value);
    if (!match) {
      setStatus('fix', '此日期尚無已審核的禱讀內容。');
      return;
    }
    setStatus('busy', '正在載入經文…');
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
      add(container, 'h2', match.title || match.scripture_reference);
      if (match.title) add(container, 'p', match.scripture_reference, 'eyebrow');
      add(container, 'h3', '經文');
      passages.flat().forEach((verse) => add(container, 'p', verse));
      [['默想', 'summary'], ['反思', 'reflection'], ['禱告', 'prayer']].forEach(([title, key]) => {
        if (match[key]) {
          add(container, 'h3', title);
          // 禱告那一段套樣本三的淺綠底塊（.dev .pray 在 style.css）
          add(container, 'p', match[key], key === 'prayer' ? 'pray' : '');
        }
      });
      setStatus('', '');
    } catch (error) {
      if (request === generation) setStatus('fix', '經文載入失敗，請稍後再試。');
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
  }).catch(() => { setStatus('fix', '禱讀資料載入失敗，請稍後再試。'); });
}());
