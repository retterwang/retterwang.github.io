---
title: 文章标题示例
date: 2026-11-17
desc: 一句话摘要，会显示在博客首页文章列表和 RSS 描述里。
tags:
  - 数据
  - 工具
author_type: human
---

正文使用 Markdown 书写，构建时会自动转换为 HTML。

支持标准 Markdown 语法，另外还额外支持：

- 表格（宽表会自动包一层横向滚动容器，窄屏不会撑破页面）
- 引用块
- 代码块（带语法高亮基础样式）
- 图片
- 分隔线
- 脚注与定义列表（extra 扩展）

支持 `draft: true` 字段，加入草稿箱的文章不会出现在首页和 RSS 中。

## 多语言：每篇文章一种语言一个文件

文件的**后缀决定语言**。默认语言（简体中文）不带后缀，其他语言在 `.md` 前加 `.<lang>`：

```
posts/
  my-post.md            ← 简体中文（zh-CN，默认语言，必须有）
  my-post.zh-Hant.md    ← 繁體中文
  my-post.en.md         ← English
  my-post.ja.md         ← 日本語
  my-post.ko.md         ← 한국어
  my-post.fr.md         ← Français
  my-post.es.md         ← Español
  my-post.de.md         ← Deutsch
```

支持的语言代码：`zh-CN`（默认）`zh-Hant` `en` `ja` `ko` `fr` `es` `de`。

生成规则：

| 语言 | 博客首页 | 文章页 | RSS |
|---|---|---|---|
| zh-CN | `/blog/` | `/blog/<slug>/` | `/blog/feed.xml` |
| 其他 | `/blog/<lang>/` | `/blog/<lang>/<slug>/` | `/blog/<lang>/feed.xml` |

要点：

- **默认语言文件必须存在**（`<slug>.md`），否则整篇会被跳过并打印警告——其他语言版本需要挂在它上面。
- 每个语言版本的 front-matter 独立，`title` / `desc` / `tags` 都要翻译成该语言。
- `date` / `author_type` 以默认语言版本为准，译文里写一致的即可。
- 某篇缺某个语言时，该语言首页不列这篇；文章页的语言下拉里那一项会渲染为灰色不可点。
- **slug 不能等于任何语言代码**（如 `en`、`ja`），构建时会跳过并提示改名。

## 内容来源标识（必填）

本站每篇文章都必须标注内容来源，构建器会自动在文章页和列表页渲染对应徽章。

| `author_type` | 徽章 | 含义 |
|---|---|---|
| `ai` | **AIGC**（粉色） | 由人工智能生成，已经过人工审阅与事实核验 |
| `human` | **HMGC · 人工创作** | 由人工独立撰写（译文按界面语言显示，如 HMGC · Human） |

规则：

- **AI 参与写作的文章一律填 `ai`**，页面上会同时出现 AIGC 徽章和
  HTML `<meta name="aigc" content="ai-generated">` 隐式标识。
- **完全由人写的文章填 `human`**，仅显示 HMGC 徽章。
- 缺省值为 `human`。为避免漏标，新文章请显式写出该字段。
- 同一篇文章的各语言版本应保持相同的 `author_type`。

AIGC 标识依据《人工智能生成合成内容标识办法》对显式标识与隐式标识的要求实现。

## 构建与验证

```bash
python build.py     # 生成全部语言页面与 feed
python verify.py    # 结构 / RSS / 渲染 / 明暗 / 语言切换 全量自检
```
