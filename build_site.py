#!/usr/bin/env python3
"""Build a static daily-brief archive plus a reading-excerpt page.

Everything is plain Python 3 and the standard library. Run:
    python3 build_site.py
Output goes to dist/.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from pathlib import Path

from reading_archive import collect_excerpts, parse_stats, render_body

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
BRIEFS = CONTENT / "briefs"
ASSETS = ROOT / "site"
DIST = ROOT / "dist"
STATS = CONTENT / "stats.md"

LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
BRIEF_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
NAV = [("简报", "./"), ("读书", "reading.html"), ("关于", "about.html")]

DEFAULT_SITE: dict[str, object] = {
    "site_name": "简报档案",
    "owner": "Your Name",
    "tagline": "每日新闻简报与阅读摘录",
    "intro": "把每日简报、读过的书和划线摘录整理成可检索的静态档案。",
    "reading_intro": "从微信读书同步的划线摘录与原创批注。",
    "links": [],
}
SITE: dict[str, object] = dict(DEFAULT_SITE)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def inline_markdown(value: str) -> str:
    parts: list[str] = []
    cursor = 0
    for match in LINK_RE.finditer(value):
        parts.append(html.escape(value[cursor : match.start()]))
        label = html.escape(match.group(1))
        url = html.escape(match.group(2), quote=True)
        parts.append(f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>')
        cursor = match.end()
    parts.append(html.escape(value[cursor:]))
    rendered = "".join(parts)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", rendered)


def parse_frontmatter(source: str) -> tuple[dict[str, str], str]:
    lines = source.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, source
    for index in range(1, len(lines)):
        if lines[index].strip() != "---":
            continue
        data: dict[str, str] = {}
        for raw in lines[1:index]:
            if ":" not in raw:
                continue
            key, value = raw.split(":", 1)
            data[key.strip()] = value.strip().strip('"').strip("'")
        return data, "\n".join(lines[index + 1 :])
    return {}, source


def load_site() -> dict[str, object]:
    site: dict[str, object] = dict(DEFAULT_SITE)
    path = CONTENT / "site.json"
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                site.update(loaded)
        except (json.JSONDecodeError, OSError):
            pass
    return site


def render_prose(source: str) -> str:
    output: list[str] = []
    paragraph: list[str] = []
    items: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph:
            return
        text = " ".join(part.strip() for part in paragraph).strip()
        paragraph.clear()
        if text:
            output.append(f"<p>{inline_markdown(text)}</p>")

    def flush_items() -> None:
        if not items:
            return
        output.append("<ul>" + "".join(f"<li>{inline_markdown(item)}</li>" for item in items) + "</ul>")
        items.clear()

    for raw in source.splitlines():
        line = raw.strip()
        if not line:
            flush_paragraph()
            flush_items()
            continue
        if line.startswith("### "):
            flush_paragraph()
            flush_items()
            output.append(f"<h3>{inline_markdown(line[4:].strip())}</h3>")
            continue
        if line.startswith("## "):
            flush_paragraph()
            flush_items()
            output.append(f"<h2>{inline_markdown(line[3:].strip())}</h2>")
            continue
        if line.startswith("# "):
            flush_paragraph()
            flush_items()
            output.append(f"<h2>{inline_markdown(line[2:].strip())}</h2>")
            continue
        if line.startswith("- "):
            flush_paragraph()
            items.append(line[2:].strip())
            continue
        if line.startswith("> "):
            flush_paragraph()
            flush_items()
            output.append(f"<blockquote><p>{inline_markdown(line[2:].strip())}</p></blockquote>")
            continue
        flush_items()
        paragraph.append(line)
    flush_paragraph()
    flush_items()
    return "\n".join(output)


def nav_links(active: str, footer: bool = False) -> str:
    current = ' aria-current="page"' if not footer else ""
    output = []
    for label, href in NAV:
        classes = ' class="active"' if not footer and label == active else ""
        output.append(f'<a href="{href}"{classes}{current if label == active else ""}>{label}</a>')
    if footer:
        return "".join(f"<li>{link}</li>" for link in output)
    return "".join(output)


def render_header(active: str, right: str = "", brand_sub: str = "Notes") -> str:
    site_name = str(SITE.get("site_name") or "简报档案")
    mark = esc(site_name[:1])
    return f"""  <header class="site-header">
    <div class="header-left">
      <a class="brand" href="./" aria-label="返回{esc(site_name)}首页">
        <span class="brand-mark">{mark}</span>
        <span><strong>{esc(site_name)}</strong><small>{esc(brand_sub)}</small></span>
      </a>
      <nav class="site-nav" aria-label="站点导航">
        {nav_links(active)}
      </nav>
    </div>
    {right}
  </header>"""


def render_footer(active: str, lines: list[str] | None = None) -> str:
    body_lines = lines or [
        f"{esc(SITE.get('site_name'))} · {esc(SITE.get('tagline'))}",
        "示例项目 · 无广告、无追踪。",
    ]
    paragraph = "\n".join(f"    <p>{line}</p>" for line in body_lines)
    return f"""  <footer>
    <ul class="footer-nav">
      {nav_links(active, footer=True)}
    </ul>
{paragraph}
  </footer>"""


def render_page(
    *,
    title: str,
    description: str,
    active: str,
    body: str,
    main_class: str = "page-main",
    brand_sub: str = "Notes",
    script: bool = True,
    body_class: str = "",
    extra_head: str = "",
    footer_lines: list[str] | None = None,
) -> str:
    script_tag = '\n  <script src="assets/app.js" defer></script>' if script else ""
    body_attr = f' class="{esc(body_class)}"' if body_class else ""
    extra = f"\n{extra_head}" if extra_head else ""
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{esc(description)}">
  <meta name="color-scheme" content="light">
  <title>{esc(title)}</title>
  <link rel="stylesheet" href="assets/styles.css">{extra}
</head>
<body{body_attr}>
  <a class="skip-link" href="#main">跳到主要内容</a>
{render_header(active, brand_sub=brand_sub)}

  <main class="{main_class}" id="main">
{body}
  </main>

{render_footer(active, lines=footer_lines)}{script_tag}
</body>
</html>"""


def flush_paragraph(buffer: list[str], output: list[str]) -> None:
    if not buffer:
        return
    text = " ".join(part.strip() for part in buffer if part.strip()).strip()
    buffer.clear()
    if not text or text == "先看这几条：":
        return
    rendered = inline_markdown(text)
    if text.startswith("AI点评："):
        output.append(f'<aside class="ai-note"><span>AI 点评</span>{rendered[5:]}</aside>')
    elif text.startswith("入选理由："):
        output.append(f'<p class="reason"><strong>为什么重要</strong>{rendered[5:]}</p>')
    elif text.startswith("来源（"):
        output.append(f'<p class="sources">{rendered}</p>')
    else:
        output.append(f"<p>{rendered}</p>")


def strip_frontmatter(lines: list[str]) -> list[str]:
    if not lines or lines[0].strip() != "---":
        return lines
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[index + 1 :]
    return lines


def render_markdown(source: str) -> tuple[str, str, str, dict[str, int], list[tuple[str, str]]]:
    lines = strip_frontmatter(source.splitlines())
    output: list[str] = []
    paragraph: list[str] = []
    lead = ""
    title = "每日新闻简报"
    current_section = ""
    article_open = False
    section_open = False
    counts = {"重磅": 0, "AI": 0, "政策": 0, "市场": 0, "社会": 0}
    sections: list[tuple[str, str]] = []

    def close_article() -> None:
        nonlocal article_open
        flush_paragraph(paragraph, output)
        if article_open:
            output.append("</article>")
            article_open = False

    def close_section() -> None:
        nonlocal section_open
        close_article()
        if section_open:
            output.append("</section>")
            section_open = False

    for raw in lines:
        line = raw.strip()
        if line.startswith("# "):
            flush_paragraph(paragraph, output)
            title = line[2:].strip()
            continue
        if line.startswith("> ") and not lead:
            flush_paragraph(paragraph, output)
            lead = line[2:].strip()
            continue
        if line.startswith("## "):
            close_section()
            current_section = line[3:].strip()
            section_id = {
                "今日重磅": "top",
                "AI": "ai",
                "政策": "policy",
                "市场": "market",
                "社会": "society",
            }.get(current_section, re.sub(r"\W+", "-", current_section).strip("-") or "section")
            sections.append((current_section, section_id))
            output.append(
                f'<section class="brief-section" id="{html.escape(section_id)}">'
                f'<header class="section-header"><span>{html.escape(current_section)}</span></header>'
            )
            section_open = True
            continue
        if line.startswith("### "):
            close_article()
            headline = line[4:].strip()
            output.append('<article class="news-item">')
            output.append(f"<h3>{inline_markdown(headline)}</h3>")
            article_open = True
            key = "重磅" if current_section == "今日重磅" else current_section
            if key in counts:
                counts[key] += 1
            continue
        if line == "---":
            flush_paragraph(paragraph, output)
            continue
        if not line:
            flush_paragraph(paragraph, output)
            continue
        paragraph.append(line)

    close_section()
    return title, lead, "\n".join(output), counts, sections


def brief_paths() -> list[Path]:
    found = [path for path in BRIEFS.glob("*.md") if BRIEF_NAME_RE.match(path.name)]
    return sorted(found, reverse=True)


def collect_briefs() -> list[dict[str, object]]:
    briefs: list[dict[str, object]] = []
    for path in brief_paths():
        match = BRIEF_NAME_RE.match(path.name)
        if not match:
            continue
        day = match.group(1)
        title, lead, body, counts, sections = render_markdown(path.read_text(encoding="utf-8"))
        briefs.append(
            {
                "date": day,
                "display_date": f"{int(day[5:7])}月{int(day[8:10])}日",
                "title": title,
                "lead": lead,
                "body": body,
                "counts": counts,
                "sections": sections,
            }
        )
    return briefs


def archive_options(latest: dict[str, object], archive: list[dict[str, object]]) -> str:
    return "\n".join(
        f'<option value="{item["date"]}"{(" selected" if item["date"] == latest["date"] else "")}>'
        f'{item["display_date"]}</option>'
        for item in archive
    )


def brief_page(latest: dict[str, object], archive: list[dict[str, object]]) -> str:
    stats = latest["counts"]
    total = sum(int(value) for value in stats.values())
    sections = latest.get("sections") or [("今日重磅", "top"), ("AI", "ai"), ("政策", "policy"), ("市场", "market"), ("社会", "society")]
    section_nav = "".join(f'<a href="#{sid}">{esc(label)}</a>' for label, sid in sections)
    site_name = str(SITE.get("site_name") or "简报档案")
    right = f"""<label class="archive-picker">
      <span>往期</span>
      <select id="archiveSelect" aria-label="选择往期日报">{archive_options(latest, archive)}</select>
    </label>"""
    header = render_header("简报", right=right, brand_sub="Daily Brief")
    footer = render_footer(
        "简报",
        lines=[
            f"{esc(site_name)} · 示例内容，来自可编辑的 Markdown。",
            "仅供信息整理，不构成投资、法律或医疗建议。",
        ],
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{esc(site_name)}的每日新闻简报，聚焦 AI、政策、市场与社会。">
  <meta name="color-scheme" content="light">
  <title>{esc(str(latest['display_date']))}新闻简报 · {esc(site_name)}</title>
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body data-site="{esc(site_name)}">
  <a class="skip-link" href="#main">跳到主要内容</a>
{header}

  <main id="main">
    <section class="hero" aria-labelledby="pageTitle">
      <p class="eyebrow">每日新闻简报 · {esc(str(latest['display_date']))}</p>
      <h1 id="pageTitle">今天发生了什么</h1>
      <p class="lead" id="lead">{esc(str(latest['lead']))}</p>
      <div class="meta" aria-label="日报信息">
        <span id="itemCount">{total} 条要闻</span>
        <span id="topCount">{int(stats.get('重磅', 0))} 条今日重磅</span>
        <span>示例内容 · AI 辅助整理</span>
      </div>
    </section>

    <div class="reading-layout">
      <nav class="section-nav" aria-label="日报目录">{section_nav}</nav>
      <article class="brief" id="brief" aria-live="polite">{latest['body']}</article>
    </div>
  </main>

{footer}
  <script>window.__BRIEF_INDEX__ = {json.dumps(archive, ensure_ascii=False)};</script>
  <script src="assets/app.js" defer></script>
</body>
</html>"""


def load_books() -> list[dict[str, object]]:
    path = CONTENT / "reading.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    books = payload.get("books") if isinstance(payload, dict) else None
    return books if isinstance(books, list) else []


def reading_page(books: list[dict[str, object]], stats: dict[str, object]) -> str:
    excerpts = collect_excerpts(books)
    body = render_body(books, excerpts, stats, SITE)
    as_of = str(stats.get("asOf") or "")
    note_count = sum(1 for row in excerpts if row.get("note"))
    description = (
        f"把微信读书里的划线、批注和阅读时长整理成可检索的档案：{len(books)} 本书、"
        f"{len(excerpts)} 条摘录、{note_count} 条批注。"
    )
    footer = [
        f"阅读档案 · 统计截至 {as_of}" if as_of else "阅读档案",
        "全部摘录原文仅作对照，版权归原作者；批注为个人阅读记录。",
    ]
    return render_page(
        title="读书 · 阅读档案",
        description=description,
        active="读书",
        body=body,
        main_class="reading-shell",
        brand_sub="Archive",
        body_class="reading-page",
        extra_head='  <link rel="stylesheet" href="assets/reading.css">',
        footer_lines=footer,
    )


def about_page() -> str:
    site = SITE
    path = CONTENT / "about.md"
    frontmatter: dict[str, str] = {}
    body_md = ""
    if path.exists():
        frontmatter, body_md = parse_frontmatter(path.read_text(encoding="utf-8"))
    title = frontmatter.get("title") or "关于这个项目"
    summary = frontmatter.get("summary") or str(site.get("intro"))
    prose = render_prose(body_md) if body_md.strip() else "<p>这是一个可以自行替换内容的示例项目。</p>"
    body = f"""    <section class="page-hero" aria-labelledby="aboutTitle">
      <p class="eyebrow">关于 · About</p>
      <h1 id="aboutTitle">{esc(title)}</h1>
      <p class="lead">{esc(summary)}</p>
    </section>

    <div class="about-grid">
      <div class="about-main prose">
{prose}
      </div>
      <aside class="about-side" aria-label="继续浏览">
        <section class="side-card">
          <h2>继续看</h2>
          <ul class="side-links">
            <li><a href="./">每日简报</a></li>
            <li><a href="reading.html">读书摘录</a></li>
          </ul>
        </section>
      </aside>
    </div>"""
    return render_page(
        title=f"关于 · {esc(str(site.get('site_name') or '简报档案'))}",
        description=str(summary),
        active="关于",
        body=body,
    )


def add_asset_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for relative in ("assets/styles.css", "assets/app.js", "assets/reading.css"):
        asset = DIST / relative
        if asset.exists():
            versions[relative] = hashlib.sha256(asset.read_bytes()).hexdigest()[:10]
    for page in DIST.glob("*.html"):
        text = page.read_text(encoding="utf-8")
        for relative, version in versions.items():
            text = text.replace(f'href="{relative}"', f'href="{relative}?v={version}"')
            text = text.replace(f'src="{relative}"', f'src="{relative}?v={version}"')
        page.write_text(text, encoding="utf-8")
    return versions


def check_links() -> list[str]:
    missing: list[str] = []
    for label, href in NAV:
        target = DIST / "index.html" if href == "./" else DIST / href
        if not target.exists():
            missing.append(f"{label} → {href}")
    for asset in ("assets/styles.css", "assets/app.js", "assets/reading.css"):
        if not (DIST / asset).exists():
            missing.append(asset)
    return missing


def main() -> int:
    global SITE
    SITE = load_site()
    briefs = collect_briefs()
    if not briefs:
        raise SystemExit("未找到简报：请在 content/briefs/ 放 YYYY-MM-DD*.md")
    books = load_books()
    stats = parse_stats(STATS)

    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "assets").mkdir(parents=True)
    (DIST / "data").mkdir(parents=True)
    for name in ("styles.css", "app.js", "reading.css"):
        shutil.copy2(ASSETS / name, DIST / "assets" / name)

    archive = [
        {
            "date": item["date"],
            "display_date": item["display_date"],
            "lead": item["lead"],
            "counts": item["counts"],
        }
        for item in briefs
    ]
    for item in briefs:
        (DIST / "data" / f"{item['date']}.json").write_text(
            json.dumps(item, ensure_ascii=False), encoding="utf-8"
        )
    (DIST / "index.html").write_text(brief_page(briefs[0], archive), encoding="utf-8")
    (DIST / "reading.html").write_text(reading_page(books, stats), encoding="utf-8")
    (DIST / "about.html").write_text(about_page(), encoding="utf-8")
    (DIST / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")

    add_asset_versions()
    missing = check_links()
    if missing:
        print("链接自检失败：\n  " + "\n  ".join(missing))
        return 1
    print(f"Built {len(briefs)} briefs; latest={briefs[0]['date']}")
    print(f"Pages: reading={len(books)} books/{len(collect_excerpts(books))} excerpts; about=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
