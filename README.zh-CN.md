# 简报档案 · brief-archive

把每日简报、读过的书和划线摘录，生成一套可检索、可自托管的静态页面。

![预览](assets/preview.png)

只用 Python 3 标准库构建，没有 Node、数据库或前端框架依赖。构建产物是纯 HTML / CSS / JS，可以放到任意静态托管。

## 特性

- **每日简报**：首页展示最新一期，按「今日重磅 / AI / 政策 / 市场 / 社会」分节；顶部下拉切换往期。
- **阅读摘录**：时间线与按书两个视图，支持按月份、书籍、章节筛选，每页 20 条，URL 记录筛选与页码。
- **阅读统计**：累计时长、读过 / 读完、笔记数、历年柱状图与当年逐月分布。
- **数据与展示分离**：简报是 Markdown，阅读数据是 JSON，统计是 Markdown 表格；替换内容即可复用。
- **无追踪**：不加载第三方脚本、字体或统计服务。

## 快速开始

```bash
python3 build_site.py
python3 -m http.server 8000 -d dist
```

打开 <http://127.0.0.1:8000/>。构建会生成：

```text
dist/
  index.html          最新一期简报
  reading.html        阅读摘录
  about.html          关于页
  data/*.json         每期简报的结构化数据（切换往期用）
  assets/             样式与脚本
```

## 目录

```text
build_site.py           构建入口：读取内容、渲染页面、生成 dist/
reading_archive.py      阅读摘录页的渲染层
site/                   样式与前端脚本（会被复制到 dist/assets/）
content/
  site.json             站点名称、简介、导航文案
  about.md              关于页正文
  briefs/               每日简报 Markdown（文件名 YYYY-MM-DD*.md）
  reading.json          阅读摘录数据（书籍、章节、日期、原文、批注）
  stats.md              阅读统计（Markdown 表格 + 逐月时长）
```

## 写一期简报

在 `content/briefs/` 新建 `YYYY-MM-DD.md`：

```markdown
---
type: daily-brief
created: 2026-10-20
---

# 每日个人日报 · 2026-10-20

> 今日要闻：一句话概括今天最重要的两三件事。

## 今日重磅

### 条目标题

一两段事实描述。

入选理由：为什么值得关注。

AI点评：你的判断、反例或风险。

来源（示例）：[Example](https://example.com/news)

---

## AI

### 另一条

正文。

AI点评：……

来源（示例）：[Example](https://example.com/ai)
```

约定：

- 一级标题作为页面标题，引用块作为导语。
- 二级标题决定分节；目前识别「今日重磅 / AI / 政策 / 市场 / 社会」，其他标题会归入正文。
- 三级标题是一条新闻；`入选理由：`、`AI点评：`、`来源（...）：` 会渲染成对应样式。
- frontmatter 可以是任意 YAML 风格键值，构建时会被移除。

## 阅读数据

`content/reading.json` 的顶层结构：

```json
{
  "updated": "2026-10-20",
  "source": "示例数据",
  "filter": { "mode": "all", "dedupe": "book+quote" },
  "books": [
    {
      "title": "书名",
      "author": "作者",
      "last_read_date": "2026-10-14",
      "chapters": ["第一章"],
      "source_highlight_count": 5,
      "highlight_count": 5,
      "note_count": 2,
      "readingMinutes": 185,
      "status": "reading",
      "progress": 62,
      "highlights": [
        {
          "chapter": "第一章",
          "date": "2026-10-14",
          "text": "划线原文",
          "note": "可选：自己的批注"
        }
      ]
    }
  ]
}
```

`reading.json` 只负责摘录页；累计时长、读过 / 读完、笔记数与年度分布来自 `content/stats.md`。两者统计口径不同时，页面会分别标注「官方统计」与「本地覆盖」，不做相加。

`stats.md` 至少需要：

- 「历年总览」表格：注册时间、累计阅读时长、累计阅读天数、读过、读完、笔记。
- 「历年阅读时长」表格：年份 + 时长。
- 当年逐月时长：`YYYY 年逐月阅读时长` 代码块，每行 `1月   30分钟`。

具体格式可直接参考仓库内的示例文件。

## 替换成自己的内容

1. 修改 `content/site.json` 的站点名、简介与署名。
2. 用你的简报替换 `content/briefs/`。
3. 用你的阅读数据替换 `content/reading.json` 与 `content/stats.md`。
4. 可选：替换 `content/about.md`。
5. 运行 `python3 build_site.py` 检查输出。

## 部署

`dist/` 是纯静态目录，Nginx、Caddy、GitHub Pages、Cloudflare Pages 都可以直接托管。仓库自带 `.github/workflows/pages.yml`，在 GitHub 仓库 Settings → Pages 选择 GitHub Actions 即可启用演示站。

## 隐私与版权

仓库内的书名、作者、划线、批注、统计均为示例，不对应真实出版物。替换成真实数据前请确认：

- 你拥有公开这些文字的权利；摘录原文的版权归原作者。
- 阅读数据里可能包含个人信息、账号痕迹或未公开的判断，发布前自行脱敏。
- 不要提交含个人隐私的原始导出文件。

## 限制

- 没有搜索、登录、评论或后台；内容变更需要重新构建。
- 简报解析器面向上述固定结构，不完整兼容任意 Markdown。
- 统计依赖手工维护的 Markdown 表格，不做平台 API 同步。

## License

MIT
