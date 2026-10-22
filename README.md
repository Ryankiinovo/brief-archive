# brief-archive

A small static-site generator for daily briefs and a personal reading archive, built with the Python standard library.

![preview](assets/preview.png)

No Node, database, or frontend framework is required. The output is plain HTML / CSS / JS that can be hosted anywhere.

## Features

- **Daily briefs**: the latest issue on the homepage, split into sections, with an archive switcher.
- **Reading excerpts**: timeline and by-book views, filters for month / book / chapter, 20 excerpts per page, filter state kept in the URL.
- **Reading stats**: lifetime time, books read / finished, notes, a yearly chart, and the current year's monthly distribution.
- **Content and presentation separated**: briefs are Markdown, excerpts are JSON, stats are Markdown tables.
- **No tracking**: no third-party scripts, fonts, or analytics.

## Quick start

```bash
python3 build_site.py
python3 -m http.server 8000 -d dist
```

Open <http://127.0.0.1:8000/>.

## Layout

```text
build_site.py           build entry: read content, render pages, write dist/
reading_archive.py      renderer for the reading page
site/                   CSS and frontend JS, copied into dist/assets/
content/
  site.json             site name, intro, owner
  about.md              about page
  briefs/               daily briefs as Markdown (YYYY-MM-DD*.md)
  reading.json          books, chapters, dates, quotes, notes
  stats.md              reading stats tables and monthly time
```

## Writing a brief

Create `content/briefs/YYYY-MM-DD.md`:

```markdown
---
type: daily-brief
created: 2026-10-20
---

# Daily brief · 2026-10-20

> One-line summary of the day.

## Top stories

### A headline

A short factual summary.

Why it matters: your reasoning.

AI note: your judgment, counterpoint, or risk.

Source: [Example](https://example.com/news)

---

## AI

### Another item

Body.

AI note: ...

Source: [Example](https://example.com/ai)
```

The builder removes frontmatter, uses the first H1 as the page title, the blockquote as the lead, H2 as sections, and H3 as news items. `Why it matters:`, `AI note:`, and `Source:` are styled specially.

## Reading data

`content/reading.json`:

```json
{
  "updated": "2026-10-20",
  "source": "sample data",
  "filter": { "mode": "all", "dedupe": "book+quote" },
  "books": [
    {
      "title": "Book title",
      "author": "Author",
      "last_read_date": "2026-10-14",
      "chapters": ["Chapter 1"],
      "source_highlight_count": 5,
      "highlight_count": 5,
      "note_count": 2,
      "readingMinutes": 185,
      "status": "reading",
      "progress": 62,
      "highlights": [
        {
          "chapter": "Chapter 1",
          "date": "2026-10-14",
          "text": "Highlighted passage",
          "note": "Optional note"
        }
      ]
    }
  ]
}
```

Lifetime time, books read / finished, notes, and the yearly chart come from `content/stats.md`. The two sources use different scopes, so the page labels them separately and never adds them together.

## Replace the sample content

1. Edit `content/site.json`.
2. Replace `content/briefs/`.
3. Replace `content/reading.json` and `content/stats.md`.
4. Optionally replace `content/about.md`.
5. Run `python3 build_site.py`.

## Deploy

`dist/` is a static directory. Nginx, Caddy, GitHub Pages, and Cloudflare Pages all work. The included `.github/workflows/pages.yml` can publish the demo through GitHub Actions.

## Privacy and copyright

All books, authors, quotes, notes, and stats in this repository are sample data and do not correspond to real publications. Before publishing real data, make sure you have the right to publish the text, that quoted passages remain credited to their authors, and that no private information is included.

## Limitations

- No search, auth, comments, or admin UI; rebuild after content changes.
- The brief parser targets the structure above, not arbitrary Markdown.
- Stats are maintained as Markdown tables; there is no platform API sync.

## License

MIT
