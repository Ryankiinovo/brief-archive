# 每日简报档案 · daily-brief

[English](README.md) · **简体中文**

把每日简报整理成一套可检索、可自托管的静态页面。

![预览](assets/preview.png)

在线预览：<https://ryankiinovo.github.io/daily-brief/>

只用 Python 3 标准库构建，没有 Node、数据库或前端框架依赖。构建产物是纯 HTML / CSS / JS，可以放到任意静态托管。

> 本仓只做「每日简报」这一件事。个人阅读档案（划线、批注、统计）在另一个仓：[weread-brief](https://github.com/Ryankiinovo/weread-brief)。

## 特性

- **每日简报**：首页展示最新一期，按「今日重磅 / AI / 政策 / 市场 / 社会」分节；顶部下拉切换往期。
- **数据与展示分离**：简报是 Markdown，替换 `content/briefs/` 即可复用。
- **无追踪**：不加载第三方脚本、字体或统计服务。

## 快速开始

```bash
python3 build_site.py
python3 -m http.server 8000 -d dist
```

打开 <http://127.0.0.1:8000/>。

## 测试

```bash
python3 -m unittest discover -s tests -v
```

测试会把构建脚本与示例内容复制到临时目录重新构建，检查简报渲染、单页结构、关于页，以及输出里没有私人标记。

构建会生成：

```text
dist/
  index.html          最新一期简报
  about.html          关于页
  data/*.json         每期简报的结构化数据（切换往期用）
  assets/             样式与脚本
```

## 目录

```text
build_site.py           构建入口：读取内容、渲染页面、生成 dist/
site/                   样式与前端脚本（会被复制到 dist/assets/）
content/
  site.json             站点名称、简介、导航文案
  about.md              关于页正文
  briefs/               每日简报 Markdown（文件名 YYYY-MM-DD*.md）
tests/                  构建冒烟测试（unittest）
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
```

约定：

- 一级标题作为页面标题，引用块作为导语。
- 二级标题决定分节；目前识别「今日重磅 / AI / 政策 / 市场 / 社会」，其他标题会归入正文。
- 三级标题是一条新闻；`入选理由：`、`AI点评：`、`来源（...）：` 会渲染成对应样式。
- frontmatter 可以是任意 YAML 风格键值，构建时会被移除。

## 替换成自己的内容

1. 修改 `content/site.json` 的站点名、简介与署名。
2. 用你的简报替换 `content/briefs/`。
3. 可选：替换 `content/about.md`。
4. 运行 `python3 build_site.py` 检查输出。

## 部署

`dist/` 是纯静态目录，Nginx、Caddy、GitHub Pages、Cloudflare Pages 都可以直接托管。仓库自带 `.github/workflows/pages.yml`，在 GitHub 仓库 Settings → Pages 选择 GitHub Actions 即可启用演示站。

## 数据

仓库里的 26 期简报是**真实发布的内容**（2026-09-15 起），每天从公开信息源筛选，保留事实、入选理由与判断。来源链接指向公开报道，版权归原作者；页面不加载第三方脚本或统计服务。

如果你想用这套代码做自己的简报站，替换 `content/briefs/` 后重新构建即可。

## 限制

- 没有搜索、登录、评论或后台；内容变更需要重新构建。
- 简报解析器面向上述固定结构，不完整兼容任意 Markdown。

## License

MIT
