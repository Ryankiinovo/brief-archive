"""Reading archive page: data shaping and HTML fragments.

This page publishes the reading archive itself: every unique highlight, with
the thought written on it when one exists. Quotes stay attributed to the book;
the author keeps copyright, and this is a personal reading record rather than a
replacement for the book.
"""

from __future__ import annotations

import html
import re
from datetime import date, datetime
from pathlib import Path

STATUS_LABEL = {"reading": "在读", "finished": "已读完", "paused": "搁置"}


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def duration_minutes(text: str) -> int:
    """Turn 46小时43分钟 / 7分钟 into minutes."""
    if not text:
        return 0
    hours = re.search(r"(\d+)\s*小时", text)
    minutes = re.search(r"(\d+)\s*分钟", text)
    total = 0
    if hours:
        total += int(hours.group(1)) * 60
    if minutes:
        total += int(minutes.group(1))
    return total


def format_hm(minutes: object) -> str:
    total = max(0, round(float(minutes or 0)))
    hours, rest = divmod(total, 60)
    if hours == 0:
        return f"{rest}m"
    return f"{hours}h{rest:02d}m"


def format_long(minutes: object) -> str:
    total = max(0, round(float(minutes or 0)))
    hours, rest = divmod(total, 60)
    if hours == 0:
        return f"{rest} 分钟"
    return f"{hours} 小时 {rest:02d} 分"


def dot_date(value: object) -> str:
    text = str(value or "")
    return text.replace("-", ".") if re.match(r"^\d{4}-\d{2}-\d{2}$", text) else text


def status_of(progress: object, reading_status: object = "", last_read: object = "") -> str:
    if str(reading_status or "").strip() == "4":
        return "finished"
    try:
        if progress is not None and float(progress) >= 100:
            return "finished"
    except (TypeError, ValueError):
        pass
    text = str(last_read or "").strip()
    if text:
        try:
            day = datetime.strptime(text, "%Y-%m-%d").date()
            if (date.today() - day).days <= 180:
                return "reading"
        except ValueError:
            pass
    return "paused"


def parse_stats(path: str | Path) -> dict[str, object]:
    """Parse the WeRead stats Markdown without third-party libraries."""
    path = Path(path)
    result: dict[str, object] = {"asOf": "", "lifetime": {}, "years": [], "monthly": []}
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return result
    lines = source.splitlines()
    for line in lines[:20]:
        match = re.match(r"^updated:\s*(\d{4}-\d{2}-\d{2})", line.strip())
        if match:
            result["asOf"] = match.group(1)
            break
    if not result["asOf"]:
        match = re.search(r"最后更新[：:]\s*(\d{4})/(\d{1,2})/(\d{1,2})", source)
        if match:
            result["asOf"] = f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    lifetime: dict[str, object] = {}
    seen: set[str] = set()
    for line in lines:
        match = re.match(r"^\|\s*(注册时间|累计阅读时长|累计阅读天数|读过|读完|笔记)\s*\|\s*(.+?)\s*\|", line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if key in seen:
            continue
        seen.add(key)
        if key == "注册时间":
            lifetime["since"] = value
        elif key == "累计阅读时长":
            lifetime["minutes"] = duration_minutes(value)
        elif key == "累计阅读天数":
            number = re.search(r"(\d+)", value)
            lifetime["days"] = int(number.group(1)) if number else 0
        elif key == "读过":
            number = re.search(r"(\d+)", value)
            lifetime["booksRead"] = int(number.group(1)) if number else 0
        elif key == "读完":
            number = re.search(r"(\d+)", value)
            lifetime["finished"] = int(number.group(1)) if number else 0
        elif key == "笔记":
            number = re.search(r"(\d+)", value)
            lifetime["notes"] = int(number.group(1)) if number else 0
    result["lifetime"] = lifetime
    years: list[dict[str, int]] = []
    in_years = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### 历年阅读时长"):
            in_years = True
            continue
        if in_years and stripped.startswith("## "):
            break
        if not in_years:
            continue
        match = re.match(r"^\|\s*(20\d{2})\s*\|\s*(.+?)\s*\|", stripped)
        if match:
            years.append({"year": int(match.group(1)), "minutes": duration_minutes(match.group(2))})
    result["years"] = years
    monthly: list[dict[str, int]] = []
    in_monthly = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### ") and "逐月阅读时长" in stripped:
            in_monthly = True
            continue
        if in_monthly and stripped.startswith("```"):
            if monthly:
                break
            continue
        if not in_monthly:
            continue
        match = re.match(r"^(\d{1,2})月\s+.*?(\d+\s*(?:小时|分钟).*?)$", stripped)
        if match:
            monthly.append({"month": int(match.group(1)), "minutes": duration_minutes(match.group(2))})
    result["monthly"] = monthly
    return result


def collect_excerpts(books: list[dict[str, object]]) -> list[dict[str, object]]:
    """Every unique highlight, plus the thought when one was written on it."""
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for book_index, book in enumerate(books):
        title = str(book.get("title", "")).strip()
        chapters = [str(name) for name in book.get("chapters", [])]  # type: ignore[union-attr]
        chapter_order = {name: index for index, name in enumerate(chapters)}
        for item in book.get("highlights", []):  # type: ignore[union-attr]
            quote = str(item.get("text", "")).strip()
            if not quote:
                continue
            key = (title, re.sub(r"\s+", "", quote))
            if key in seen:
                continue
            seen.add(key)
            chapter = str(item.get("chapter", "")).strip() or "未分章"
            date = str(item.get("date", "")).strip()
            note = str(item.get("note", "")).strip()
            rows.append(
                {
                    "book": title,
                    "bookIndex": book_index,
                    "chapter": chapter,
                    "chapterIndex": chapter_order.get(chapter, 999),
                    "date": date,
                    "month": date[:7] if re.match(r"^\d{4}-\d{2}", date) else "未标日期",
                    "quote": quote,
                    **({"note": note} if note else {}),
                }
            )
    rows.sort(
        key=lambda row: (str(row["date"]), -int(row["bookIndex"]), -int(row["chapterIndex"])),
        reverse=True,
    )
    return rows


def collect_thoughts(books: list[dict[str, object]]) -> list[dict[str, str]]:
    """Compatibility helper: the subset of excerpts that carries a thought."""
    return [
        {
            "book": str(row["book"]),
            "chapter": str(row["chapter"]),
            "date": str(row["date"]),
            "quote": str(row["quote"]),
            "text": str(row["note"]),
        }
        for row in collect_excerpts(books)
        if row.get("note")
    ]


def _year_chart(stats: dict[str, object]) -> str:
    years = [row for row in stats.get("years", []) if int(row.get("minutes") or 0) > 0]  # type: ignore[union-attr]
    if not years:
        return '<p class="chart-empty">暂无历年数据。</p>'
    peak = max(int(row["minutes"]) for row in years)
    bars = []
    for row in years:
        height = max(3, round(int(row["minutes"]) / peak * 100))
        bars.append(
            '<div class="bar">'
            f'<span class="bar-value">{esc(format_hm(row["minutes"]))}</span>'
            f'<span class="bar-fill" style="--h:{height}%"></span>'
            f'<span class="bar-year">{esc(row["year"])}</span>'
            "</div>"
        )
    label = "，".join(f"{row['year']} 年 {format_hm(row['minutes'])}" for row in years)
    return f'<div class="bars" role="img" aria-label="历年阅读时长：{esc(label)}">{"".join(bars)}</div>'


def _month_chart(stats: dict[str, object]) -> str:
    monthly = list(stats.get("monthly", []))  # type: ignore[arg-type]
    as_of = str(stats.get("asOf") or "")
    count = 9
    if re.match(r"^\d{4}-\d{2}-", as_of):
        count = int(as_of[5:7])
    monthly = monthly[: max(1, count)]
    if not monthly:
        return ""
    peak = max(1, max(int(row.get("minutes") or 0) for row in monthly))
    cols = []
    for row in monthly:
        height = max(3, round(int(row.get("minutes") or 0) / peak * 100))
        cols.append(
            '<div class="spark-col">'
            f'<span class="spark-fill" style="--h:{height}%"></span>'
            f'<span class="spark-month">{esc(row["month"])}月</span>'
            "</div>"
        )
    year = str(stats.get("asOf") or "")[:4] or "当年"
    return f'<div class="spark" role="img" aria-label="{year} 年逐月阅读时长">' + "".join(cols) + "</div>"


def _stat(value: str, label: str, note: str) -> str:
    return (
        '<div class="reading-stat">'
        f'<p class="reading-stat-value">{esc(value)}</p>'
        f'<p class="reading-stat-label">{esc(label)} <span>{esc(note)}</span></p>'
        "</div>"
    )


def _shelf_card(book: dict[str, object], index: int) -> str:
    progress = book.get("progress")
    try:
        percent = max(0, min(100, round(float(progress)))) if progress is not None else 0
    except (TypeError, ValueError):
        percent = 0
    status = str(book.get("status") or "paused")
    label = STATUS_LABEL.get(status, status)
    minutes = int(book.get("readingMinutes") or 0)
    highlights = int(book.get("highlightCount") or len(book.get("highlights", [])))  # type: ignore[arg-type]
    thoughts = int(book.get("noteCount") or 0)
    return (
        f'<article class="shelf-book" data-status="{esc(status)}">'
        '<div class="shelf-top">'
        f'<span class="shelf-no">{index:02d}</span>'
        f'<span class="pill pill-{esc(status)}">{esc(label)}</span>'
        "</div>"
        f'<h3 class="shelf-title">{esc(book.get("title", ""))}</h3>'
        f'<p class="shelf-author">{esc(book.get("author") or "微信读书")}</p>'
        f'<div class="shelf-progress" aria-label="阅读进度 {percent}%"><span style="width:{percent}%"></span></div>'
        f'<div class="shelf-meta"><span>{percent}%</span><span>{esc(format_hm(minutes))}</span></div>'
        '<div class="shelf-counts">'
        f'<span><b>{highlights}</b> 条摘录</span>'
        f'<span><b>{thoughts}</b> 条批注</span>'
        "</div></article>"
    )


def _month_label(value: str) -> str:
    match = re.match(r"^(\d{4})-(\d{2})$", value)
    if not match:
        return value
    return f"{match.group(1)} 年 {int(match.group(2))} 月"


def _excerpt_card(excerpt: dict[str, object]) -> str:
    book = str(excerpt["book"])
    chapter = str(excerpt["chapter"])
    date = str(excerpt["date"])
    note = str(excerpt.get("note", "")).strip()
    caption = " · ".join(part for part in (book, chapter, dot_date(date)) if part)
    note_html = (
        '<p class="excerpt-note"><span class="note-label">批注</span>'
        f'{esc(note)}</p>'
        if note
        else ""
    )
    return (
        f'<article class="excerpt-card" data-book="{esc(book)}" '
        f'data-book-index="{int(excerpt["bookIndex"])}" '
        f'data-chapter="{esc(chapter)}" '
        f'data-chapter-index="{int(excerpt["chapterIndex"])}" '
        f'data-month="{esc(excerpt["month"])}" '
        f'data-date="{esc(date)}">'
        '<blockquote class="excerpt-quote"><span class="note-label">原文</span>'
        f'{esc(excerpt["quote"])}</blockquote>'
        f'{note_html}'
        f'<footer class="excerpt-foot">{esc(caption)}</footer>'
        "</article>"
    )


def _book_chips(excerpts: list[dict[str, object]]) -> str:
    counts: dict[str, int] = {}
    for row in excerpts:
        book = str(row["book"])
        counts[book] = counts.get(book, 0) + 1
    order = sorted(counts, key=lambda name: (-counts[name], name))
    buttons = [
        f'<button class="chip is-active" type="button" data-filter="all" aria-pressed="true">全部 <span>{len(excerpts)}</span></button>'
    ]
    for name in order:
        buttons.append(
            f'<button class="chip" type="button" data-filter="{esc(name)}" aria-pressed="false">'
            f'{esc(name)} <span>{counts[name]}</span></button>'
        )
    return "".join(buttons)


def _month_options(excerpts: list[dict[str, object]]) -> str:
    counts: dict[str, int] = {}
    for row in excerpts:
        month = str(row["month"])
        counts[month] = counts.get(month, 0) + 1
    options = ['<option value="all">全部时间</option>']
    for month in sorted(counts, reverse=True):
        options.append(
            f'<option value="{esc(month)}">{esc(_month_label(month))} · {counts[month]} 条</option>'
        )
    return "".join(options)

def render_body(
    books: list[dict[str, object]],
    excerpts: list[dict[str, object]],
    stats: dict[str, object],
    site: dict[str, object],
) -> str:
    lifetime = dict(stats.get("lifetime") or {})  # type: ignore[arg-type]
    as_of = str(stats.get("asOf") or "")
    local_minutes = sum(int(book.get("readingMinutes") or 0) for book in books)
    excerpt_count = len(excerpts)
    note_count = sum(1 for row in excerpts if row.get("note"))
    source_blocks = sum(
        int(book.get("sourceHighlightCount") or book.get("source_highlight_count") or book.get("highlight_count") or 0)
        for book in books
    )
    source_note = (
        f"源文件 {source_blocks} 个划线块，按原文去重后为 {excerpt_count} 条。"
        if source_blocks > excerpt_count
        else ""
    )
    finished = sum(1 for book in books if book.get("status") == "finished")
    reading = sum(1 for book in books if book.get("status") == "reading")
    shelf = "".join(_shelf_card(book, index) for index, book in enumerate(books, 1))
    excerpt_html = "".join(
        _excerpt_card(row).replace("<article ", '<article hidden ', 1) if index >= 20 else _excerpt_card(row)
        for index, row in enumerate(excerpts)
    )
    excerpts_empty = "" if excerpts else (
        '<div class="excerpt-empty"><h3>还没有摘录</h3><p>在微信读书里划线后，重新构建页面即可看到。</p></div>'
    )
    stats_note = f"统计截至 {esc(as_of)}" if as_of else "尚未读取到官方统计"
    shelf_note = f"按最近一次阅读排序。{len(books)} 本书里有 {finished} 本已读完，{reading} 本在读。"
    site_name = str(site.get("site_name") or "简报档案")

    return f'''    <section class="reading-hero" aria-labelledby="readingTitle">
      <p class="reading-kicker">个人阅读档案 · PERSONAL READING ARCHIVE</p>
      <div class="reading-hero-grid">
        <div>
          <h1 id="readingTitle">把读过的书，<br><em>整理成可检索的档案。</em></h1>
          <p class="reading-lead">把微信读书里的划线、批注和阅读时长导出、解析，做成一份能反复回看的结构化记录。原文留在书里，这里把原文和判断放在一起。</p>
          <p class="reading-sync">已同步 {len(books)} 本书 · {excerpt_count} 条摘录 · {note_count} 条批注</p>
        </div>
        <aside class="reading-aside">
          <p class="aside-kicker">DATA, NOT DECORATION</p>
          <p>数据来自微信读书官方统计与 Obsidian 同步笔记。前者记录「读了多少」，后者留下划过与想过什么。</p>
          <p class="aside-date">{stats_note}</p>
        </aside>
      </div>
      <div class="reading-stats" aria-label="阅读概览">
        {_stat(format_hm(lifetime.get("minutes", 0)), "累计阅读", "官方统计")}
        {_stat(str(lifetime.get("booksRead", len(books))), "读过的书", "本")}
        {_stat(str(lifetime.get("finished", finished)), "读完的书", "本")}
        {_stat(str(lifetime.get("notes", note_count)), "笔记", "条")}
      </div>
    </section>

    <section class="reading-section" aria-labelledby="timeTitle">
      <div class="reading-section-head">
        <span class="section-no">01</span>
        <h2 id="timeTitle">时间花在哪里</h2>
        <p>官方统计的累计阅读时长，分布在 {esc(lifetime.get("days", "—"))} 个阅读日里。按年份与月份查看分布。</p>
      </div>
      <div class="time-grid">
        <div class="chart-stack">
          <div class="chart-card">
            <div class="chart-head"><span>历年阅读时长</span><span>小时 / 年</span></div>
            {_year_chart(stats)}
          </div>
          <div class="chart-card chart-card--spark">
            <div class="chart-head"><span>{esc((as_of[:4] if as_of else ""))} 年 · 逐月</span><span>本地同步前</span></div>
            {_month_chart(stats)}
          </div>
        </div>
        <aside class="coverage-card">
          <p class="coverage-kicker">本地同步覆盖</p>
          <dl class="coverage-list">
            <div><dt>已同步</dt><dd>{len(books)} <small>本</small></dd></div>
            <div><dt>摘录</dt><dd>{excerpt_count} <small>条</small></dd></div>
            <div><dt>批注</dt><dd>{note_count} <small>条</small></dd></div>
            <div><dt>阅读时长</dt><dd>{esc(format_hm(local_minutes))}</dd></div>
          </dl>
          <p class="coverage-note">官方统计是总量，这里只覆盖同步到本地的 {len(books)} 本书，两者口径不同，不做相加。</p>
        </aside>
      </div>
    </section>

    <section class="reading-section" aria-labelledby="shelfTitle">
      <div class="reading-section-head">
        <span class="section-no">02</span>
        <h2 id="shelfTitle">同步到本地的书架</h2>
        <p>{esc(shelf_note)}</p>
      </div>
      <div class="shelf">{shelf}</div>
    </section>

    <section class="reading-section" aria-labelledby="excerptsTitle" id="excerpts">
      <div class="reading-section-head">
        <span class="section-no">03</span>
        <h2 id="excerptsTitle">我的摘录</h2>
        <p>{excerpt_count} 条摘录，其中 {note_count} 条带批注。原文版权归原作者，批注为原创。{source_note}</p>
      </div>
      <div class="excerpt-toolbar">
        <div class="view-switch" role="group" aria-label="摘录视图">
          <button class="view-btn is-active" type="button" data-view="time" aria-pressed="true">时间线</button>
          <button class="view-btn" type="button" data-view="book" aria-pressed="false">按书</button>
        </div>
        <div class="excerpt-selects">
          <label class="excerpt-select"><span>月份</span>
            <select id="excerptMonth">{_month_options(excerpts)}</select>
          </label>
          <label class="excerpt-select"><span>章节</span>
            <select id="excerptChapter"><option value="all">全部章节</option></select>
          </label>
        </div>
        <p class="excerpt-count" id="excerptCount" aria-live="polite">共 {excerpt_count} 条摘录</p>
      </div>
      <div class="chips" id="excerptFilters" role="group" aria-label="按书筛选摘录">{_book_chips(excerpts)}</div>
      <div class="excerpt-grid" id="excerptGrid">{excerpt_html}</div>
      {excerpts_empty}
      <div class="excerpt-pager" id="excerptPager" aria-label="摘录分页"></div>
      <div class="excerpt-empty" id="excerptEmpty" hidden>
        <h3>这组筛选下还没有摘录</h3>
        <p>换一本书或月份试试。</p>
      </div>
      <noscript><p class="excerpt-noscript">分页与视图切换需要 JavaScript；关闭脚本时只显示前 20 条。</p></noscript>
    </section>

    <section class="reading-method" aria-labelledby="methodTitle">
      <div class="reading-method-inner">
        <div class="method-head">
          <div>
            <span class="section-no">04</span>
            <h2 id="methodTitle">这份档案怎么来的</h2>
          </div>
          <p>不是手工排的页面，而是一条可重复执行的流水线：换一台机器，改一下路径，就能生成同样的数据与页面。</p>
        </div>
        <div class="method-body">
          <ol class="method-steps">
            <li><span>01</span><h3>同步</h3><p>微信读书 → Obsidian，由 obsidian-weread-plugin 把划线、想法、进度与阅读时长写成本地 Markdown。</p></li>
            <li><span>02</span><h3>解析</h3><p>build_site.py 读取全量高亮与读书笔记，按原文去重，把想法挂回对应划线，再按书和章节聚合。</p></li>
            <li><span>03</span><h3>生成</h3><p>静态 HTML / CSS / JS，不依赖框架和第三方请求；样式与脚本都是手写的。</p></li>
            <li><span>04</span><h3>校验</h3><p>构建前做链接自检，构建后本地预览；确认没有漏数据、没有把私人字段带进页面。</p></li>
          </ol>
          <div class="terminal">
            <div class="terminal-bar"><span></span><span></span><span></span><b>BUILD</b></div>
            <pre><code>cd brief-archive
python3 build_site.py
python3 -m http.server 8000 -d dist</code></pre>
          </div>
        </div>
        <div class="principles">
          <div><h3>原文只作对照</h3><p>摘录原文用于定位与理解，版权归原作者；这里公开的是个人阅读记录与自己的判断，不替代原书。</p></div>
          <div><h3>口径写清楚</h3><p>官方 {esc(lifetime.get("notes", note_count))} 条笔记不等于这里的 {note_count} 条本地批注；这里是去重后的 {excerpt_count} 条摘录。</p></div>
          <div><h3>可复核</h3><p>每个数字都能由 Obsidian 笔记与本项目的构建脚本重新算出来，页面只是产物。</p></div>
        </div>
      </div>
    </section>'''
