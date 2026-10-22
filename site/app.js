const select = document.querySelector('#archiveSelect');
const brief = document.querySelector('#brief');
const lead = document.querySelector('#lead');
const itemCount = document.querySelector('#itemCount');
const topCount = document.querySelector('#topCount');
const eyebrow = document.querySelector('.eyebrow');

function articleTotal(counts) {
  return Object.values(counts).reduce((sum, value) => sum + (Number(value) || 0), 0);
}

async function loadBrief(day, { scroll = true } = {}) {
  const response = await fetch(`data/${day}.json`);
  if (!response.ok) throw new Error('无法读取该期日报');
  const data = await response.json();
  brief.innerHTML = data.body;
  lead.textContent = data.lead;
  eyebrow.textContent = `每日新闻简报 · ${data.display_date}`;
  itemCount.textContent = `${articleTotal(data.counts)} 条要闻`;
  if (topCount) topCount.textContent = `${data.counts['重磅'] || 0} 条今日重磅`;
  document.title = `${data.display_date}新闻简报 · ${document.body.dataset.site || '简报档案'}`;
  history.replaceState(null, '', `?date=${data.date}`);
  select.value = data.date;
  if (scroll) window.scrollTo({ top: 0, behavior: 'smooth' });
}

if (select && brief) {
  select.addEventListener('change', () => {
    loadBrief(select.value).catch(() => {
      window.location.reload();
    });
  });

  const requestedDate = new URLSearchParams(window.location.search).get('date');
  if (requestedDate && [...select.options].some(option => option.value === requestedDate)) {
    loadBrief(requestedDate, { scroll: false }).catch(() => {});
  }
}

// 读书页摘录：时间线 / 按书、筛选与分页
const excerptGrid = document.querySelector('#excerptGrid');
const excerptFilters = document.querySelector('#excerptFilters');
const excerptMonth = document.querySelector('#excerptMonth');
const excerptChapter = document.querySelector('#excerptChapter');
const excerptCount = document.querySelector('#excerptCount');
const excerptPager = document.querySelector('#excerptPager');
const excerptEmpty = document.querySelector('#excerptEmpty');
const excerptSection = document.querySelector('#excerpts');

if (excerptGrid && excerptFilters) {
  const PAGE_SIZE = 20;
  const allCards = Array.from(excerptGrid.querySelectorAll('.excerpt-card'));
  const order = new Map(allCards.map((card, index) => [card, index]));
  const chips = Array.from(excerptFilters.querySelectorAll('.chip'));
  const viewButtons = Array.from(document.querySelectorAll('.view-btn'));
  const state = { view: 'time', book: 'all', month: 'all', chapter: 'all', page: 1 };
  let sorted = allCards.slice();

  function formatMonth(value) {
    const match = /^(\d{4})-(\d{2})$/.exec(value || '');
    return match ? `${match[1]} 年 ${Number(match[2])} 月` : (value || '未标日期');
  }

  function readUrl() {
    const params = new URLSearchParams(window.location.search);
    const view = params.get('view');
    if (view === 'time' || view === 'book') state.view = view;
    const book = params.get('book');
    if (book && allCards.some(card => card.dataset.book === book)) state.book = book;
    const month = params.get('month');
    if (month && excerptMonth && [...excerptMonth.options].some(option => option.value === month)) {
      state.month = month;
    }
    const chapter = params.get('chapter');
    if (chapter) state.chapter = chapter;
    const page = Number(params.get('page'));
    if (Number.isInteger(page) && page > 0) state.page = page;
  }

  function sortCards() {
    sorted.sort((a, b) => {
      if (state.view === 'book') {
        const bookDiff = Number(a.dataset.bookIndex) - Number(b.dataset.bookIndex);
        if (bookDiff) return bookDiff;
        const chapterDiff = Number(a.dataset.chapterIndex) - Number(b.dataset.chapterIndex);
        if (chapterDiff) return chapterDiff;
        if (a.dataset.date !== b.dataset.date) return a.dataset.date < b.dataset.date ? 1 : -1;
      } else {
        if (a.dataset.date !== b.dataset.date) return a.dataset.date < b.dataset.date ? 1 : -1;
        const bookDiff = Number(a.dataset.bookIndex) - Number(b.dataset.bookIndex);
        if (bookDiff) return bookDiff;
        const chapterDiff = Number(a.dataset.chapterIndex) - Number(b.dataset.chapterIndex);
        if (chapterDiff) return chapterDiff;
      }
      return order.get(a) - order.get(b);
    });
    excerptGrid.querySelectorAll('.excerpt-group').forEach(node => node.remove());
    sorted.forEach(card => excerptGrid.appendChild(card));
  }

  function refreshChapterOptions() {
    if (!excerptChapter) return;
    const counts = new Map();
    if (state.book !== 'all') {
      allCards.forEach(card => {
        if (card.dataset.book !== state.book) return;
        const key = card.dataset.chapterIndex;
        const row = counts.get(key) || { chapter: card.dataset.chapter || '未分章', count: 0 };
        row.count += 1;
        counts.set(key, row);
      });
    }
    excerptChapter.innerHTML = '';
    const allOption = document.createElement('option');
    allOption.value = 'all';
    allOption.textContent = '全部章节';
    excerptChapter.appendChild(allOption);
    [...counts.entries()]
      .sort((a, b) => Number(a[0]) - Number(b[0]))
      .forEach(([key, row]) => {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = `${row.chapter} · ${row.count}`;
        excerptChapter.appendChild(option);
      });
    excerptChapter.disabled = state.book === 'all';
    if (state.chapter !== 'all' && !counts.has(state.chapter)) state.chapter = 'all';
    excerptChapter.value = state.chapter;
  }

  function syncControls() {
    chips.forEach(chip => {
      const active = chip.dataset.filter === state.book;
      chip.classList.toggle('is-active', active);
      chip.setAttribute('aria-pressed', String(active));
    });
    viewButtons.forEach(button => {
      const active = button.dataset.view === state.view;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    if (excerptMonth) excerptMonth.value = state.month;
  }

  function setUrl() {
    const url = new URL(window.location.href);
    ['view', 'book', 'month', 'chapter', 'page'].forEach(key => url.searchParams.delete(key));
    if (state.view !== 'time') url.searchParams.set('view', state.view);
    if (state.book !== 'all') url.searchParams.set('book', state.book);
    if (state.month !== 'all') url.searchParams.set('month', state.month);
    if (state.chapter !== 'all') url.searchParams.set('chapter', state.chapter);
    if (state.page > 1) url.searchParams.set('page', String(state.page));
    url.hash = '';
    history.replaceState(null, '', url);
  }

  function addPagerButton(label, page, { active = false, disabled = false, title = '' } = {}) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'pager-btn';
    button.textContent = label;
    if (title) button.title = title;
    if (active) {
      button.classList.add('is-active');
      button.setAttribute('aria-current', 'page');
    }
    button.disabled = disabled;
    button.dataset.page = String(page);
    excerptPager.appendChild(button);
  }

  function renderPager(totalPages) {
    excerptPager.innerHTML = '';
    if (totalPages <= 1) return;
    addPagerButton('上一页', state.page - 1, { disabled: state.page === 1 });
    const pages = new Set([1, totalPages, state.page, state.page - 1, state.page + 1]);
    const list = [...pages].filter(page => page >= 1 && page <= totalPages).sort((a, b) => a - b);
    let previous = 0;
    list.forEach(page => {
      if (page - previous > 1) {
        const gap = document.createElement('span');
        gap.className = 'pager-gap';
        gap.textContent = '…';
        excerptPager.appendChild(gap);
      }
      addPagerButton(String(page), page, { active: page === state.page });
      previous = page;
    });
    addPagerButton('下一页', state.page + 1, { disabled: state.page === totalPages });
  }

  function render({ scroll = false } = {}) {
    if (excerptChapter && excerptChapter.value !== state.chapter && !excerptChapter.disabled) {
      excerptChapter.value = state.chapter;
    }
    const filtered = sorted.filter(card => {
      if (state.book !== 'all' && card.dataset.book !== state.book) return false;
      if (state.month !== 'all' && card.dataset.month !== state.month) return false;
      if (state.chapter !== 'all' && card.dataset.chapterIndex !== state.chapter) return false;
      return true;
    });
    const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    state.page = Math.min(Math.max(1, state.page), totalPages);
    const start = (state.page - 1) * PAGE_SIZE;
    const pageCards = filtered.slice(start, start + PAGE_SIZE);

    allCards.forEach(card => { card.hidden = true; });
    pageCards.forEach(card => { card.hidden = false; });
    excerptGrid.hidden = filtered.length === 0;
    excerptGrid.querySelectorAll('.excerpt-group').forEach(node => node.remove());

    let currentKey = '';
    let group = null;
    let countNode = null;
    let groupCount = 0;
    pageCards.forEach(card => {
      const key = state.view === 'time'
        ? card.dataset.month
        : `${card.dataset.bookIndex}:${card.dataset.chapterIndex}`;
      if (key !== currentKey) {
        currentKey = key;
        groupCount = 0;
        group = document.createElement('div');
        group.className = 'excerpt-group';
        const title = document.createElement('span');
        const detail = document.createElement('small');
        if (state.view === 'time') {
          title.textContent = formatMonth(card.dataset.month);
        } else {
          title.textContent = card.dataset.chapter || '未分章';
          detail.dataset.book = card.dataset.book;
        }
        group.append(title, detail);
        excerptGrid.insertBefore(group, card);
        countNode = detail;
      }
      groupCount += 1;
      if (countNode) {
        countNode.textContent = state.view === 'time'
          ? `${groupCount} 条`
          : `${card.dataset.book} · ${groupCount} 条`;
      }
    });

    if (excerptEmpty) excerptEmpty.hidden = filtered.length !== 0;
    if (excerptCount) {
      excerptCount.textContent = filtered.length
        ? `共 ${filtered.length} 条摘录 · 第 ${state.page} / ${totalPages} 页`
        : '共 0 条摘录';
    }
    renderPager(totalPages);
    setUrl();
    if (scroll && excerptSection) {
      excerptSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  readUrl();
  syncControls();
  refreshChapterOptions();
  sortCards();
  render();

  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      state.book = chip.dataset.filter || 'all';
      state.chapter = 'all';
      state.page = 1;
      syncControls();
      refreshChapterOptions();
      render();
    });
  });

  if (excerptMonth) {
    excerptMonth.addEventListener('change', () => {
      state.month = excerptMonth.value;
      state.page = 1;
      render();
    });
  }

  if (excerptChapter) {
    excerptChapter.addEventListener('change', () => {
      state.chapter = excerptChapter.value;
      state.page = 1;
      render();
    });
  }

  viewButtons.forEach(button => {
    button.addEventListener('click', () => {
      const view = button.dataset.view;
      if (!view || view === state.view) return;
      state.view = view;
      state.page = 1;
      if (view === 'book') {
        state.month = 'all';
      } else {
        state.chapter = 'all';
      }
      syncControls();
      refreshChapterOptions();
      sortCards();
      render();
    });
  });

  excerptPager.addEventListener('click', event => {
    const button = event.target.closest('.pager-btn');
    if (!button || button.disabled) return;
    const page = Number(button.dataset.page);
    if (!Number.isInteger(page) || page < 1) return;
    state.page = page;
    render({ scroll: true });
  });
}
