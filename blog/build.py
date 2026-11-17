# -*- coding: utf-8 -*-
"""
retter.wang/blog 静态博客构建器

职责：
  1. 扫描 posts/*.md（带 front-matter）
  2. 生成 posts/<slug>/index.html 文章页
  3. 生成 index.html 博客首页（文章列表）
  4. 生成 feed.xml（RSS 2.0）

用法（在 blog/ 目录下）：
    python build.py

约定：
  - front-matter 为 YAML，位于文件开头 --- 之间
  - 必填字段：title / date（YYYY-MM-DD）；可选：desc / tags / draft
  - 文章正文以 Markdown 编写，输出为独立 HTML 文件（无前端框架）
  - 站点地址：SITE_BASE = https://retter.wang/blog
"""

import os
import re
import json
import html
import shutil
import datetime
import urllib.parse

import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(HERE, "posts")

SITE_BASE = "https://retter.wang/blog"
SITE_TITLE = "王文昊的博客"
SITE_TITLE_EN = "Wang Wenhao's Blog"
SITE_DESCRIPTION = "数据、工具与独立开发 —— 王文昊的个人博客。"
SITE_AUTHOR = "王文昊 · Wang Wenhao"
SITE_LANG = "zh-CN"
AUTHOR_EMAIL = "me@retter.wang"

# 站点集群（与个人主页保持一致）
SITES = [
    ("Gallery", "摄影作品集 · 主站", "abetterplace2.live", "https://abetterplace2.live"),
    ("Metro", "Windows Phone 风格磁贴画廊", "abetterplace2.live/metro/", "https://abetterplace2.live/metro/"),
    ("Marathon", "个人马拉松赛历与成绩", "marathon.abetterplace2.live", "https://marathon.abetterplace2.live"),
    ("PEDAL", "车辆加速感速度模拟器", "pedal.abetterplace2.live", "https://pedal.abetterplace2.live"),
    ("CAMCOP", "相机对比工具 · 网页版", "camera.abetterplace2.live", "https://camera.abetterplace2.live"),
]

ARROW_SVG = (
    '<svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" '
    'stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M3 9 9 3M4.5 3H9v4.5"/></svg>'
)

# ============================================================
# 通用样式：与个人主页同源（暖纸 / 墨 / 松绿）
# ============================================================
BASE_CSS = """
:root{
  --paper:#FAF9F7;
  --ink:#191817;
  --muted:#6F6B64;
  --faint:#9B968D;
  --line:#E6E3DD;
  --accent:#4A5D54;
  --accent-soft:#EDEFEA;

  --serif:'Spectral','Noto Serif SC','Songti SC','STSong',Georgia,serif;
  --sans:'Hanken Grotesk','Noto Sans SC',-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;

  --measure:38em;
  --w:700px;
  --gutter:clamp(24px,6vw,40px);
  --section-gap:clamp(72px,11vh,116px);
}

*,*::before,*::after{box-sizing:border-box;}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth;}
body{
  margin:0;
  background:var(--paper);
  color:var(--ink);
  font-family:var(--sans);
  font-size:17px;
  line-height:1.8;
  font-weight:400;
  -webkit-font-smoothing:antialiased;
  -moz-osx-font-smoothing:grayscale;
  text-rendering:optimizeLegibility;
  font-feature-settings:"kern" 1,"liga" 1;
}
::selection{background:var(--accent);color:var(--paper);}

a{
  color:inherit;
  text-decoration:none;
  text-decoration-thickness:1px;
  text-underline-offset:3px;
  transition:color .22s ease;
}
a.link{text-decoration:underline;text-decoration-color:var(--faint);}
a.link:hover{color:var(--accent);text-decoration-color:var(--accent);}

.wrap{
  max-width:var(--w);
  margin:0 auto;
  padding-left:var(--gutter);
  padding-right:var(--gutter);
}

.tr{font-size:.9em;color:var(--faint);font-weight:400;letter-spacing:.01em;}
.tr-b{display:block;margin-top:3px;font-size:.88em;color:var(--faint);font-weight:400;letter-spacing:.005em;line-height:1.55;}

section{scroll-margin-top:24px;}
.section{margin-bottom:var(--section-gap);}
.section-head{
  display:flex;
  align-items:baseline;
  gap:14px;
  margin:0 0 34px;
}
.section-head h2{
  font-family:var(--serif);
  font-size:1.18rem;
  font-weight:600;
  margin:0;
  letter-spacing:.01em;
  background:var(--accent);
  color:#fff;
  padding:0 4px;
  border-radius:0;
  line-height:1.1;
}
.section-head .en{font-size:.82rem;color:var(--faint);font-family:var(--sans);letter-spacing:.04em;}
.section-head .rule{flex:1;height:1px;background:var(--line);align-self:center;}

.prose{max-width:var(--measure);}
.prose p{margin:0 0 1.15em;color:var(--muted);}
.prose p:last-child{margin-bottom:0;}
.prose .lead{color:var(--ink);}
.prose h2,.prose h3,.prose h4{
  font-family:var(--serif);
  font-weight:600;
  line-height:1.4;
  margin:2em 0 .7em;
  color:var(--ink);
}
.prose h2{font-size:1.24rem;}
.prose h3{font-size:1.08rem;}
.prose h4{font-size:.98rem;}
.prose ul,.prose ol{margin:0 0 1.15em;padding-left:1.4em;color:var(--muted);}
.prose li{margin:0 0 .4em;}
.prose li::marker{color:var(--faint);}
.prose blockquote{
  margin:1.5em 0;
  padding:2px 0 2px 18px;
  border-left:2px solid var(--accent);
  color:var(--muted);
  font-style:normal;
}
.prose blockquote p{margin:0;}
.prose code{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'Courier New',monospace;
  font-size:.86em;
  background:var(--accent-soft);
  padding:.12em .38em;
  border-radius:3px;
}
.prose pre{
  background:var(--accent-soft);
  border:1px solid var(--line);
  border-radius:3px;
  padding:16px 18px;
  overflow-x:auto;
  margin:1.5em 0;
}
.prose pre code{background:none;padding:0;font-size:.85em;line-height:1.7;}
.prose img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:3px;}
.prose hr{border:0;border-top:1px solid var(--line);margin:2.4em 0;}
.prose table{width:100%;border-collapse:collapse;margin:1.5em 0;font-size:.92rem;}
.prose th,.prose td{border:1px solid var(--line);padding:8px 12px;text-align:left;}
.prose th{background:var(--accent-soft);font-weight:600;color:var(--ink);}

/* 宽表格（如 DNS 记录表）在窄屏会撑破容器：
   用 .table-wrap 包一层横向滚动容器，表格自身保留 min-width 以维持可读性 */
.table-wrap{
  overflow-x:auto;
  margin:1.5em 0;
  -webkit-overflow-scrolling:touch;
}
.table-wrap table{margin:0;min-width:34em;}
.table-wrap th,.table-wrap td{white-space:nowrap;}
.table-wrap th:first-child,.table-wrap td:first-child{white-space:normal;}

.rise{opacity:0;transform:translateY(10px);animation:rise .9s cubic-bezier(.22,.61,.36,1) forwards;}
.d1{animation-delay:.05s;}
.d2{animation-delay:.18s;}
.d3{animation-delay:.32s;}
.d4{animation-delay:.46s;}
@keyframes rise{to{opacity:1;transform:none;}}

@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto;}
  .rise{opacity:1;transform:none;animation:none;}
  *{transition:none !important;}
}

/* ---- 内容来源标识 AIGC / HMGC（首页与文章页共用） ---- */
.p-flag{
  display:inline-flex;
  align-items:center;
  gap:5px;
  font-family:var(--sans);
  font-size:.78rem;
  font-weight:600;
  line-height:1.5;
  letter-spacing:.06em;
  padding:3px 12px;
  border-radius:999px;
  white-space:nowrap;
  vertical-align:middle;
}
.p-flag::before{
  content:"";
  width:5px;height:5px;border-radius:50%;
  background:currentColor;
}
.p-flag-ai{
  color:#D6336C;
  background:#FDEBF2;
  border:1px solid #E64980;
}
.p-flag-human{
  background:var(--accent-soft);
  color:var(--accent);
  border:1px solid #D6DED8;
}
"""

# ============================================================
# 博客首页专用样式
# ============================================================
HOME_CSS = """
/* ---- 顶部栏 ---- */
.site-bar{
  border-bottom:1px solid var(--line);
  background:rgba(250,249,247,.86);
  backdrop-filter:saturate(140%) blur(8px);
  position:sticky;
  top:0;
  z-index:20;
}
.site-bar .bar-inner{
  max-width:var(--w);
  margin:0 auto;
  padding:13px var(--gutter);
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:16px;
}
.bar-left{display:flex;align-items:baseline;gap:10px;min-width:0;}
.bar-left .mark{
  font-family:var(--serif);
  font-weight:600;
  font-size:1rem;
  letter-spacing:.01em;
  color:var(--ink);
  white-space:nowrap;
}
.bar-left .mark:hover{color:var(--accent);}
.bar-left .bar-sub{
  font-size:.78rem;
  color:var(--faint);
  letter-spacing:.03em;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}
.bar-right{display:flex;align-items:center;gap:18px;flex:none;}
.bar-right a{
  font-size:.86rem;
  color:var(--muted);
  white-space:nowrap;
  letter-spacing:.01em;
}
.bar-right a:hover{color:var(--accent);}
.bar-right .rss{display:inline-flex;align-items:center;gap:6px;}

/* ---- 博客 Hero ---- */
.blog-hero{padding-top:clamp(56px,10vh,92px);padding-bottom:var(--section-gap);}
.blog-hero h1{
  font-family:var(--serif);
  font-weight:600;
  font-size:clamp(1.75rem,5vw,2.5rem);
  line-height:1.15;
  letter-spacing:-.01em;
  margin:0 0 18px;
}
.blog-hero .tagline{
  font-size:1.02rem;
  color:var(--muted);
  max-width:var(--measure);
  margin:0;
}
.blog-hero .hero-meta{
  margin-top:26px;
  display:flex;
  flex-wrap:wrap;
  gap:10px 26px;
  align-items:center;
  font-size:.86rem;
  color:var(--faint);
}
.blog-hero .hero-meta .rss-btn{
  display:inline-flex;
  align-items:center;
  gap:7px;
  color:var(--accent);
  border:1px solid var(--accent);
  border-radius:3px;
  padding:5px 12px;
  transition:background .22s ease,color .22s ease;
}
.blog-hero .hero-meta .rss-btn:hover{background:var(--accent);color:#fff;}
.blog-hero .hero-meta .rss-btn svg{flex:none;}

/* ---- 文章列表 ---- */
.post-list{list-style:none;margin:0;padding:0;}
.post-item{
  display:block;
  padding:24px 4px;
  border-bottom:1px solid var(--line);
  transition:background .25s ease,padding .25s ease;
}
.post-item:first-child{border-top:1px solid var(--line);}
.post-item:hover{background:var(--accent-soft);padding-left:12px;padding-right:12px;}
.post-item .p-meta{
  display:flex;
  align-items:baseline;
  gap:12px;
  font-size:.86rem;
  color:var(--faint);
  font-variant-numeric:tabular-nums;
  letter-spacing:.02em;
  margin-bottom:6px;
}
.post-item .p-title{
  font-family:var(--serif);
  font-size:1.2rem;
  font-weight:600;
  line-height:1.4;
  color:var(--ink);
  display:block;
  transition:color .22s ease;
}
.post-item:hover .p-title{color:var(--accent);}
.post-item .p-desc{
  margin:7px 0 0;
  font-size:.94rem;
  color:var(--muted);
  line-height:1.65;
  max-width:var(--measure);
}
.post-item .p-tags{
  margin-top:10px;
  display:flex;
  flex-wrap:wrap;
  gap:8px;
}
.post-item .p-tags span{
  font-size:.76rem;
  color:var(--faint);
  border:1px solid var(--line);
  border-radius:2px;
  padding:2px 8px;
  letter-spacing:.02em;
}

/* ---- 空状态 ---- */
.empty-note{
  border:1px dashed var(--line);
  border-radius:3px;
  padding:38px 26px;
  text-align:center;
  background:#fff;
}
.empty-note .e-t{
  font-family:var(--serif);
  font-size:1.08rem;
  font-weight:600;
  color:var(--ink);
  margin:0 0 10px;
}
.empty-note .e-d{
  font-size:.92rem;
  color:var(--muted);
  margin:0;
  line-height:1.7;
}

/* ---- 站点集群 ---- */
.site-cluster{
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:10px;
}
.site-card{
  display:flex;
  flex-direction:column;
  gap:3px;
  padding:12px 14px 13px;
  border:1px solid var(--line);
  border-radius:3px;
  transition:border-color .22s ease,background .22s ease;
}
.site-card .s-name{
  display:flex;
  align-items:center;
  gap:7px;
  font-family:var(--serif);
  font-size:.96rem;
  font-weight:600;
  line-height:1.35;
  color:var(--ink);
  transition:color .22s ease;
}
.site-card .s-name svg{flex:none;opacity:0;transform:translate(-3px,3px);transition:opacity .22s ease,transform .22s ease;}
.site-card .s-desc{font-size:.82rem;color:var(--muted);line-height:1.5;}
.site-card .s-url{font-size:.74rem;color:var(--faint);letter-spacing:.01em;overflow-wrap:anywhere;}
.site-card:hover{border-color:var(--accent);background:#fff;}
.site-card:hover .s-name{color:var(--accent);}
.site-card:hover .s-name svg{opacity:1;transform:none;}

/* ---- 页脚 ---- */
.blog-foot{
  border-top:1px solid var(--line);
  padding-top:44px;
  padding-bottom:56px;
}
.blog-foot .f-row{
  display:flex;
  justify-content:space-between;
  flex-wrap:wrap;
  gap:8px 20px;
  font-size:.82rem;
  color:var(--faint);
}
.blog-foot .f-links{
  display:flex;
  flex-wrap:wrap;
  gap:10px 22px;
  margin-top:14px;
  padding-top:14px;
  border-top:1px solid var(--line);
  font-size:.82rem;
  color:var(--faint);
}

@media (max-width:600px){
  body{font-size:16px;}
  .site-cluster{grid-template-columns:1fr;gap:8px;}
  .bar-left .bar-sub{display:none;}
  .bar-right{gap:14px;}
  .post-item{padding:20px 2px;}
  .post-item:hover{padding-left:8px;padding-right:8px;}
  .blog-hero .hero-meta{gap:10px 16px;}
}
"""

# ============================================================
# 文章页专用样式
# ============================================================
POST_CSS = """
/* ---- 顶部栏 ---- */
.site-bar{
  border-bottom:1px solid var(--line);
  background:rgba(250,249,247,.86);
  backdrop-filter:saturate(140%) blur(8px);
  position:sticky;
  top:0;
  z-index:20;
}
.site-bar .bar-inner{
  max-width:var(--w);
  margin:0 auto;
  padding:13px var(--gutter);
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:16px;
}
.bar-left{display:flex;align-items:baseline;gap:10px;min-width:0;}
.bar-left .mark{
  font-family:var(--serif);
  font-weight:600;
  font-size:1rem;
  letter-spacing:.01em;
  color:var(--ink);
  white-space:nowrap;
}
.bar-left .mark:hover{color:var(--accent);}
.bar-left .bar-sub{
  font-size:.78rem;
  color:var(--faint);
  letter-spacing:.03em;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}
.bar-right{display:flex;align-items:center;gap:18px;flex:none;}
.bar-right a{font-size:.86rem;color:var(--muted);white-space:nowrap;letter-spacing:.01em;}
.bar-right a:hover{color:var(--accent);}
.bar-right .rss{display:inline-flex;align-items:center;gap:6px;}

/* ---- 文章头 ---- */
.post-head{padding-top:clamp(48px,9vh,84px);padding-bottom:34px;}
.post-head .back{
  display:inline-flex;
  align-items:center;
  gap:6px;
  font-size:.86rem;
  color:var(--faint);
  margin-bottom:22px;
}
.post-head .back:hover{color:var(--accent);}
.post-head h1{
  font-family:var(--serif);
  font-weight:600;
  font-size:clamp(1.6rem,4.4vw,2.2rem);
  line-height:1.28;
  letter-spacing:-.01em;
  margin:0 0 16px;
  max-width:var(--measure);
}
.post-head .p-meta{
  display:flex;
  flex-wrap:wrap;
  align-items:baseline;
  gap:8px 16px;
  font-size:.88rem;
  color:var(--faint);
  font-variant-numeric:tabular-nums;
  letter-spacing:.02em;
}
.post-head .p-tags{display:flex;flex-wrap:wrap;gap:8px;}
.post-head .p-tags span{
  font-size:.76rem;
  color:var(--faint);
  border:1px solid var(--line);
  border-radius:2px;
  padding:2px 8px;
  letter-spacing:.02em;
}

/* ---- 文章页 AIGC 显式标识块 ---- */
.aigc-note{
  font-family:var(--sans);
  font-size:.82rem;
  line-height:1.7;
  color:#7A5B22;
  background:#FCF8EF;
  border:1px solid #EFE2C6;
  border-left:3px solid #D9A94C;
  border-radius:3px;
  padding:10px 14px;
  margin:0 0 26px;
}
.aigc-note b{font-weight:600;}

/* ---- 正文 ---- */
.post-body{padding-bottom:var(--section-gap);}
.post-body .prose{max-width:var(--measure);}
.post-foot{
  border-top:1px solid var(--line);
  margin-top:20px;
  padding-top:26px;
}
.post-foot .p-nav{
  display:flex;
  justify-content:space-between;
  flex-wrap:wrap;
  gap:14px 24px;
  font-size:.9rem;
}
.post-foot .p-nav a{color:var(--muted);max-width:44%;}
.post-foot .p-nav a:hover{color:var(--accent);}
.post-foot .p-nav .next{text-align:right;margin-left:auto;}
.post-foot .p-nav .lbl{
  display:block;
  font-size:.76rem;
  color:var(--faint);
  letter-spacing:.03em;
  margin-bottom:3px;
}

@media (max-width:600px){
  body{font-size:16px;}
  .bar-left .bar-sub{display:none;}
  .bar-right{gap:14px;}
  .post-foot .p-nav a{max-width:100%;}
  .post-foot .p-nav .next{text-align:left;margin-left:0;}
}
"""

FONT_LINK = (
    '<link rel="preconnect" href="https://miaoda.feishu.cn" crossorigin>\n'
    '<link rel="stylesheet" href="https://miaoda.feishu.cn/fonts/css2?'
    'family=Noto+Serif+SC:wght@400;500;600;700&'
    'family=Noto+Sans+SC:wght@300;400;500&'
    'family=Spectral:ital,wght@0,400;0,500;0,600;1,400&'
    'family=Hanken+Grotesk:wght@300;400;500;600&'
    'family=Pacifico&display=swap">'
)

RSS_ICON = (
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/>'
    '<circle cx="5" cy="19" r="1.6" fill="currentColor" stroke="none"/></svg>'
)


def esc(s):
    return html.escape(s or "", quote=True)


# ============================================================
# front-matter 解析
# ============================================================
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def parse_front_matter(raw):
    """返回 (meta_dict, body_markdown)"""
    m = FM_RE.match(raw)
    if not m:
        return {}, raw
    fm_text, body = m.group(1), m.group(2)
    meta = {}
    try:
        import yaml
        meta = yaml.safe_load(fm_text) or {}
    except Exception:
        # 极简回退解析
        for line in fm_text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip("'\"")
    if not isinstance(meta, dict):
        meta = {}
    return meta, body


def slugify(meta, filename):
    s = meta.get("slug") or os.path.splitext(filename)[0]
    return str(s).strip()


def parse_date(v):
    """返回 date 对象；支持 YYYY-MM-DD / YYYY-MM-DD HH:MM"""
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError("无法解析日期: %r" % v)


# ============================================================
# 内容来源标识：AIGC（AI 生成）/ HMGC（人工创作）
# ============================================================
FLAG_LABELS = {
    "ai": "AIGC",
    "human": "HMGC · 人工创作",
}
FLAG_HINTS = {
    "ai": ("本文由人工智能生成，已经过人工审阅与事实核验。"
           "依据《人工智能生成合成内容标识办法》，本文带 AIGC 显式标识。"),
    "human": "",
}
_AIGC_ALIASES = {"ai", "aigc", "machine", "llm", "generated"}


def norm_author_type(v):
    """归一化为 'ai' | 'human'；缺省视为人工创作。"""
    s = str(v or "").strip().lower()
    return "ai" if s in _AIGC_ALIASES else "human"


def flag_badge(author_type):
    cls = "p-flag-ai" if author_type == "ai" else "p-flag-human"
    return '<span class="p-flag %s">%s</span>' % (cls, FLAG_LABELS[author_type])


def flag_note(author_type):
    hint = FLAG_HINTS.get(author_type, "")
    if not hint:
        return ""
    return '    <div class="aigc-note"><b>AIGC 标识</b> · %s</div>\n' % hint


def collect_posts():
    posts = []
    if not os.path.isdir(POSTS_DIR):
        return posts
    for fn in sorted(os.listdir(POSTS_DIR)):
        # `_` 前缀视为模板/说明文件，不作为文章处理
        if not fn.endswith(".md") or fn.startswith("_"):
            continue
        path = os.path.join(POSTS_DIR, fn)
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        meta, body = parse_front_matter(raw)
        if meta.get("draft"):
            continue
        if "title" not in meta or "date" not in meta:
            print("  [skip] %s 缺少 title/date" % fn)
            continue
        try:
            d = parse_date(meta["date"])
        except ValueError as e:
            print("  [skip] %s %s" % (fn, e))
            continue
        posts.append(
            {
                "slug": slugify(meta, fn),
                "title": str(meta["title"]),
                "date": d,
                "desc": str(meta.get("desc", "") or ""),
                "tags": [str(t) for t in (meta.get("tags") or [])],
                "body": body,
                "source": fn,
                "author_type": norm_author_type(meta.get("author_type")),
            }
        )
    # 新文章在前
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
    return posts


# ============================================================
# HTML 组装
# ============================================================
def site_bar(current="", extra_right=None):
    """current: 'home' | 'post'"""
    right = []
    if extra_right:
        right.append(extra_right)
    right.append(
        '<a class="rss" href="%s/feed.xml" type="application/rss+xml">%s RSS</a>'
        % (SITE_BASE, RSS_ICON)
    )
    if current == "home":
        right.append('<a href="https://retter.wang/">个人主页</a>')
    else:
        right.append('<a href="%s/">博客首页</a>' % SITE_BASE)

    return (
        '<header class="site-bar">\n'
        '  <div class="bar-inner">\n'
        '    <div class="bar-left">\n'
        '      <a class="mark" href="%s/">%s</a>\n'
        '      <span class="bar-sub">%s</span>\n'
        '    </div>\n'
        '    <nav class="bar-right" aria-label="站点导航 Site navigation">\n'
        '      %s\n'
        '    </nav>\n'
        '  </div>\n'
        '</header>' % (SITE_BASE, esc(SITE_TITLE), esc(SITE_DESCRIPTION), "\n      ".join(right))
    )


def cluster_html():
    cards = []
    for name, desc, url, href in SITES:
        cards.append(
            '        <a class="site-card" href="%s" target="_blank" rel="noopener">\n'
            '          <span class="s-name">%s%s</span>\n'
            '          <span class="s-desc">%s</span>\n'
            '          <span class="s-url">%s</span>\n'
            '        </a>' % (esc(href), esc(name), ARROW_SVG, esc(desc), esc(url))
        )
    return (
        '      <div class="site-cluster">\n' + "\n".join(cards) + "\n      </div>"
    )


def build_home(posts):
    if posts:
        items = []
        for p in posts:
            tags = ""
            if p["tags"]:
                tags = (
                    '          <span class="p-tags">\n'
                    + "\n".join(
                        "            <span>%s</span>" % esc(t) for t in p["tags"]
                    )
                    + "\n          </span>"
                )
            desc_block = ""
            if p["desc"]:
                desc_block = '            <p class="p-desc">%s</p>\n' % esc(p["desc"])
            tags_block = ""
            if tags:
                tags_block = tags + "\n"
            flag = flag_badge(p.get("author_type", "human"))
            items.append(
                '        <li>\n'
                '          <a class="post-item" href="%s/%s/">\n'
                '            <span class="p-meta">\n'
                '              <time datetime="%s">%s</time>\n'
                '              %s\n'
                '            </span>\n'
                '            <span class="p-title">%s</span>\n'
                '%s%s'
                '          </a>\n'
                '        </li>'
                % (
                    SITE_BASE,
                    esc(p["slug"]),
                    p["date"].isoformat(),
                    p["date"].strftime("%Y-%m-%d"),
                    flag,
                    esc(p["title"]),
                    desc_block,
                    tags_block,
                )
            )
        list_block = (
            '      <ul class="post-list">\n' + "\n".join(items) + "\n      </ul>"
        )
    else:
        list_block = (
            '      <div class="empty-note">\n'
            '        <p class="e-t">文章正在路上</p>\n'
            '        <p class="e-d">这里还空空如也 —— 稍后就会有第一篇文章。<br>'
            '          <span class="tr">No posts yet. The first one is on its way.</span></p>\n'
            '      </div>'
        )

    count_meta = ""
    if posts:
        count_meta = (
            '      <span>共 %d 篇 · %d posts</span>\n' % (len(posts), len(posts))
        )

    return """<!DOCTYPE html>
<html lang="%(lang)s">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%(title)s</title>
<meta name="description" content="%(desc)s">
<meta name="author" content="%(author)s">
<link rel="alternate" type="application/rss+xml" title="%(title)s" href="%(base)s/feed.xml">
<link rel="canonical" href="%(base)s/">
<meta property="og:type" content="website">
<meta property="og:title" content="%(title)s">
<meta property="og:description" content="%(desc)s">
<meta property="og:url" content="%(base)s/">
<link rel="icon" href="%(base)s/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="%(base)s/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="%(base)s/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="%(base)s/apple-touch-icon.png">
%(fonts)s
<style>
%(base_css)s
%(home_css)s
</style>
</head>
<body>

%(bar)s

<main class="wrap">

  <section class="blog-hero">
    <h1 class="rise d1">%(title)s</h1>
    <p class="tagline rise d2">%(desc)s</p>
    <div class="hero-meta rise d3">
      <a class="rss-btn" href="%(base)s/feed.xml" type="application/rss+xml">%(rss_icon)s 订阅 RSS</a>
%(count_meta)s
    </div>
  </section>

  <section class="section" id="posts">
    <div class="section-head">
      <h2>文章</h2><span class="en">Posts</span><span class="rule"></span>
    </div>
%(list_block)s
  </section>

  <section class="section" id="sites">
    <div class="section-head">
      <h2>站点集群</h2><span class="en">Site cluster</span><span class="rule"></span>
    </div>
    <p class="extra-label" style="margin:0 0 14px;font-size:.8rem;color:var(--faint);letter-spacing:.03em;">我的其他网站 · 点击直达<span class="tr-b">Other sites · tap to visit</span></p>
%(cluster)s
  </section>

</main>

<footer class="blog-foot">
  <div class="wrap">
    <div class="f-row">
      <span>© %(year)d %(author)s</span>
      <span>最后更新于 %(month)d 月 · Last updated: %(monthname)s %(year)d</span>
    </div>
    <div class="f-links">
      <a class="link" href="https://retter.wang/">个人主页</a>
      <a class="link" href="%(base)s/feed.xml">RSS</a>
      <a class="link" href="mailto:%(email)s">%(email)s</a>
    </div>
  </div>
</footer>

</body>
</html>
""" % {
        "lang": SITE_LANG,
        "title": esc(SITE_TITLE),
        "desc": esc(SITE_DESCRIPTION),
        "author": esc(SITE_AUTHOR),
        "base": SITE_BASE,
        "email": AUTHOR_EMAIL,
        "fonts": FONT_LINK,
        "base_css": BASE_CSS,
        "home_css": HOME_CSS,
        "bar": site_bar(current="home"),
        "list_block": list_block,
        "cluster": cluster_html(),
        "rss_icon": RSS_ICON,
        "count": len(posts),
        "count_meta": count_meta,
        "year": datetime.date.today().year,
        "month": datetime.date.today().month,
        "monthname": datetime.date.today().strftime("%B"),
    }


def build_post(p, prev_post, next_post):
    md = markdown.Markdown(
        extensions=["extra", "sane_lists", "toc", "admonition", "nl2br"],
        extension_configs={"toc": {"permalink": False}},
        output_format="html5",
    )
    content = md.convert(p["body"])

    # 表格外包横向滚动容器，避免宽表（如 DNS 记录表）在窄屏撑破页面
    content = re.sub(
        r"<table>(.*?)</table>",
        lambda m: '<div class="table-wrap"><table>%s</table></div>' % m.group(1),
        content,
        flags=re.DOTALL,
    )

    # 阅读时间（按中文 400 字/分钟、英文 200 词/分钟估算）
    plain = re.sub(r"[#*`>\-\[\]()!#]", "", p["body"])
    cjk = len(re.findall(r"[\u4e00-\u9fff]", plain))
    words = len(re.findall(r"[A-Za-z0-9]+", plain))
    minutes = max(1, int(round(cjk / 400.0 + words / 200.0)))

    tags = ""
    if p["tags"]:
        tags = (
            '      <div class="p-tags">\n'
            + "\n".join("        <span>%s</span>" % esc(t) for t in p["tags"])
            + "\n      </div>"
        )

    # 内容来源标识
    _atype = p.get("author_type", "human")
    flag = flag_badge(_atype)
    note = flag_note(_atype)
    flag_meta = "ai-generated" if _atype == "ai" else "human-authored"

    nav = []
    if prev_post:
        nav.append(
            '        <a class="prev" href="%s/%s/">\n'
            '          <span class="lbl">上一篇 · Previous</span>%s\n'
            '        </a>' % (SITE_BASE, esc(prev_post["slug"]), esc(prev_post["title"]))
        )
    else:
        nav.append('        <span></span>')
    if next_post:
        nav.append(
            '        <a class="next" href="%s/%s/">\n'
            '          <span class="lbl">下一篇 · Next</span>%s\n'
            '        </a>' % (SITE_BASE, esc(next_post["slug"]), esc(next_post["title"]))
        )
    else:
        nav.append('        <span></span>')

    return """<!DOCTYPE html>
<html lang="%(lang)s">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%(title)s · %(site_title)s</title>
<meta name="description" content="%(desc)s">
<meta name="author" content="%(author)s">
<meta name="aigc" content="%(flag_meta)s">
<link rel="alternate" type="application/rss+xml" title="%(site_title)s" href="%(base)s/feed.xml">
<link rel="canonical" href="%(base)s/%(slug)s/">
<meta property="og:type" content="article">
<meta property="og:title" content="%(title)s">
<meta property="og:description" content="%(desc)s">
<meta property="og:url" content="%(base)s/%(slug)s/">
<meta property="article:published_time" content="%(iso)s">
<link rel="icon" href="%(base)s/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="%(base)s/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="%(base)s/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="%(base)s/apple-touch-icon.png">
%(fonts)s
<style>
%(base_css)s
%(post_css)s
</style>
</head>
<body>

%(bar)s

<main class="wrap">

  <article>
    <header class="post-head">
      <a class="back" href="%(base)s/">← 返回博客</a>
      <h1>%(title)s</h1>
      <div class="p-meta">
        <time datetime="%(iso)s">%(date)s</time>
        <span>约 %(minutes)d 分钟阅读 · %(minutes)d min read</span>
        %(flag)s
        %(tags)s
      </div>
    </header>

    <div class="post-body prose">
%(note)s%(content)s
    </div>

    <footer class="post-foot">
      <nav class="p-nav" aria-label="文章导航 Post navigation">
%(nav)s
      </nav>
    </footer>
  </article>

</main>

<footer class="blog-foot">
  <div class="wrap">
    <div class="f-row">
      <span>© %(year)d %(author)s</span>
      <span>最后更新于 %(month)d 月 · Last updated: %(monthname)s %(year)d</span>
    </div>
    <div class="f-links">
      <a class="link" href="%(base)s/">博客首页</a>
      <a class="link" href="%(base)s/feed.xml">RSS</a>
      <a class="link" href="https://retter.wang/">个人主页</a>
    </div>
  </div>
</footer>

</body>
</html>
""" % {
        "lang": SITE_LANG,
        "title": esc(p["title"]),
        "site_title": esc(SITE_TITLE),
        "desc": esc(p["desc"] or p["title"]),
        "author": esc(SITE_AUTHOR),
        "base": SITE_BASE,
        "slug": esc(p["slug"]),
        "iso": p["date"].isoformat(),
        "date": p["date"].strftime("%Y 年 %m 月 %d 日"),
        "minutes": minutes,
        "tags": tags,
        "content": content,
        "nav": "\n".join(nav),
        "bar": site_bar(current="post"),
        "fonts": FONT_LINK,
        "base_css": BASE_CSS,
        "flag": flag,
        "flag_meta": flag_meta,
        "note": note,
        "post_css": POST_CSS,
        "year": datetime.date.today().year,
        "month": datetime.date.today().month,
        "monthname": datetime.date.today().strftime("%B"),
    }


def build_feed(posts):
    """RSS 2.0"""
    now = datetime.datetime.now().astimezone()
    items = []
    for p in posts:
        link = "%s/%s/" % (SITE_BASE, p["slug"])
        desc = p["desc"] or p["title"]
        cats = "".join(
            "<category>%s</category>" % esc(t) for t in p["tags"]
        )
        guid = link
        items.append(
            "    <item>\n"
            "      <title>%s</title>\n"
            "      <link>%s</link>\n"
            "      <guid isPermaLink=\"true\">%s</guid>\n"
            "      <pubDate>%s</pubDate>\n"
            "      <description>%s</description>\n"
            "      %s\n"
            "    </item>"
            % (
                esc(p["title"]),
                esc(link),
                esc(guid),
                email.utils.format_datetime(
                    datetime.datetime.combine(p["date"], datetime.time(9, 0)).replace(tzinfo=now.tzinfo)
                ),
                esc(desc),
                cats,
            )
        )
    body = "\n".join(items)
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>%(title)s</title>
    <link>%(base)s/</link>
    <atom:link href="%(base)s/feed.xml" rel="self" type="application/rss+xml"/>
    <description>%(desc)s</description>
    <language>%(lang)s</language>
    <managingEditor>%(email)s (%(author)s)</managingEditor>
    <webMaster>%(email)s (%(author)s)</webMaster>
    <lastBuildDate>%(lastbuild)s</lastBuildDate>
    <generator>retter.wang blog build.py</generator>
%(items)s
  </channel>
</rss>
""" % {
        "title": esc(SITE_TITLE),
        "base": SITE_BASE,
        "desc": esc(SITE_DESCRIPTION),
        "lang": SITE_LANG,
        "email": AUTHOR_EMAIL,
        "author": esc(SITE_AUTHOR),
        "lastbuild": email.utils.format_datetime(now),
        "items": body,
    }


def main():
    posts = collect_posts()
    print("找到文章 %d 篇" % len(posts))

    # 首页
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_home(posts))
    print("生成 index.html")

    # RSS
    with open(os.path.join(HERE, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(build_feed(posts))
    print("生成 feed.xml")

    # 文章页
    for i, p in enumerate(posts):
        prev_post = posts[i + 1] if i + 1 < len(posts) else None
        next_post = posts[i - 1] if i > 0 else None
        out_dir = os.path.join(HERE, p["slug"])
        if os.path.isdir(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir)
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(build_post(p, prev_post, next_post))
        print("生成 %s/index.html" % p["slug"])

    # 索引信息（便于外部脚本读取）
    with open(os.path.join(HERE, "posts.json"), "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "slug": p["slug"],
                    "title": p["title"],
                    "date": p["date"].isoformat(),
                    "desc": p["desc"],
                    "tags": p["tags"],
                    "url": "%s/%s/" % (SITE_BASE, p["slug"]),
                }
                for p in posts
            ],
            f,
            ensure_ascii=False,
            indent=2,
        )
    print("生成 posts.json")


if __name__ == "__main__":
    import email.utils  # noqa: E402  (build_feed 使用)
    main()
