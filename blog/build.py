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
SITE_AUTHOR = "王文昊 · Wang Wenhao"
AUTHOR_EMAIL = "me@retter.wang"

# ============================================================
# 多语言：与个人主页同一套语言集合与按钮标签
# ============================================================
LANGS = ["zh-CN", "zh-Hant", "en", "ja", "ko", "fr", "es", "de"]
DEFAULT_LANG = "zh-CN"
# 语言按钮上的短标记
LANG_BADGE = {
    "zh-CN": "中", "zh-Hant": "繁", "en": "EN", "ja": "日",
    "ko": "한", "fr": "FR", "es": "ES", "de": "DE",
}
# 语言下拉里的自称
LANG_NAME = {
    "zh-CN": "简体中文", "zh-Hant": "繁體中文", "en": "English", "ja": "日本語",
    "ko": "한국어", "fr": "Français", "es": "Español", "de": "Deutsch",
}

# 站点集群（品牌名不译，描述逐语言）
SITES = [
    ("Gallery", "abetterplace2.live", "https://abetterplace2.live"),
    ("Metro", "abetterplace2.live/metro/", "https://abetterplace2.live/metro/"),
    ("Marathon", "marathon.abetterplace2.live", "https://marathon.abetterplace2.live"),
    ("PEDAL", "pedal.abetterplace2.live", "https://pedal.abetterplace2.live"),
    ("CAMCOP", "camera.abetterplace2.live", "https://camera.abetterplace2.live"),
]

# ------------------------------------------------------------
# 界面文案（8 语言）。文章正文不在此处 —— 正文本就是独立静态页。
# ------------------------------------------------------------
UI = {
    "zh-CN": {
        "site_title": "王文昊的博客",
        "site_desc": "数据、工具与独立开发 —— 王文昊的个人博客。",
        "nav_home": "个人主页",
        "nav_blog": "博客首页",
        "subscribe": "订阅 RSS",
        "sec_posts": "文章", "sec_sites": "站点集群",
        "cluster_label": "我的其他网站",
        "empty_t": "文章正在路上",
        "empty_d": "这里还空空如也，稍后就会有第一篇文章。",
        "no_lang_t": "暂无该语言的文章",
        "no_lang_d": "这篇文章还没有这个语言的版本，点此阅读中文原文。",
        "count": "共 %d 篇",
        "back": "← 返回博客",
        "minutes": "约 %d 分钟",
        "prev": "上一篇", "next": "下一篇",
        "updated": "最后更新于 %s",
        "theme_to_dark": "切换到深色模式",
        "theme_to_light": "切换到浅色模式",
        "lang_switch": "切换语言 · Change language",
        "site_nav": "站点导航 Site navigation",
        "post_nav": "文章导航 Post navigation",
        "sites_desc": [
            "摄影作品集 · 主站",
            "Windows Phone 风格磁贴画廊",
            "个人马拉松赛历与成绩",
            "车辆加速感速度模拟器",
            "相机对比工具 · 网页版",
        ],
    },
    "zh-Hant": {
        "site_title": "王文昊的部落格",
        "site_desc": "資料、工具與獨立開發 —— 王文昊的個人部落格。",
        "nav_home": "個人主頁",
        "nav_blog": "部落格首頁",
        "subscribe": "訂閱 RSS",
        "sec_posts": "文章", "sec_sites": "站點集群",
        "cluster_label": "我的其他網站",
        "empty_t": "文章正在路上",
        "empty_d": "這裡還空空如也，稍後就會有第一篇文章。",
        "no_lang_t": "暫無該語言的文章",
        "no_lang_d": "這篇文章還沒有這個語言的版本，點此閱讀中文原文。",
        "count": "共 %d 篇",
        "back": "← 返回部落格",
        "minutes": "約 %d 分鐘",
        "prev": "上一篇", "next": "下一篇",
        "updated": "最後更新於 %s",
        "theme_to_dark": "切換到深色模式",
        "theme_to_light": "切換到淺色模式",
        "lang_switch": "切換語言 · Change language",
        "site_nav": "站點導覽 Site navigation",
        "post_nav": "文章導覽 Post navigation",
        "sites_desc": [
            "攝影作品集 · 主站",
            "Windows Phone 風格磚貼畫廊",
            "個人馬拉松賽曆與成績",
            "車輛加速感速度模擬器",
            "相機對比工具 · 網頁版",
        ],
    },
    "en": {
        "site_title": "Wang Wenhao's Blog",
        "site_desc": "Notes on data, tooling and solo development — the personal blog of Wang Wenhao.",
        "nav_home": "Home",
        "nav_blog": "Blog home",
        "subscribe": "Subscribe",
        "sec_posts": "Posts", "sec_sites": "Site cluster",
        "cluster_label": "My other websites",
        "empty_t": "Posts are on the way",
        "empty_d": "Nothing here yet — the first post is coming soon.",
        "no_lang_t": "No posts in this language",
        "no_lang_d": "This post hasn't been translated yet. Read the Chinese original.",
        "count": "%d post(s)",
        "back": "← Back to blog",
        "minutes": "%d min read",
        "prev": "Previous", "next": "Next",
        "updated": "Last updated %s",
        "theme_to_dark": "Switch to dark mode",
        "theme_to_light": "Switch to light mode",
        "lang_switch": "Change language",
        "site_nav": "Site navigation",
        "post_nav": "Post navigation",
        "sites_desc": [
            "Photography portfolio · main site",
            "Windows Phone style tile gallery",
            "My marathon calendar and results",
            "Vehicle acceleration feel simulator",
            "Camera comparison tool · web version",
        ],
    },
    "ja": {
        "site_title": "王文昊のブログ",
        "site_desc": "データ、ツール、個人開発について —— 王文昊の個人ブログ。",
        "nav_home": "ホーム",
        "nav_blog": "ブログ一覧",
        "subscribe": "RSS を購読",
        "sec_posts": "記事", "sec_sites": "サイト一覧",
        "cluster_label": "運営している他のサイト",
        "empty_t": "記事を準備中です",
        "empty_d": "まだ何もありません。最初の記事をまもなく公開します。",
        "no_lang_t": "この言語の記事はありません",
        "no_lang_d": "この記事の日本語版はまだありません。中国語の原文をご覧ください。",
        "count": "全 %d 件",
        "back": "← ブログに戻る",
        "minutes": "約 %d 分",
        "prev": "前の記事", "next": "次の記事",
        "updated": "最終更新 %s",
        "theme_to_dark": "ダークモードに切り替え",
        "theme_to_light": "ライトモードに切り替え",
        "lang_switch": "言語を切り替え · Change language",
        "site_nav": "サイトナビゲーション",
        "post_nav": "記事ナビゲーション",
        "sites_desc": [
            "写真ポートフォリオ · メインサイト",
            "Windows Phone 風タイルギャラリー",
            "マラソンの記録とカレンダー",
            "加速感を再現するドライブシミュレーター",
            "カメラ比較ツール · Web 版",
        ],
    },
    "ko": {
        "site_title": "왕원하오의 블로그",
        "site_desc": "데이터, 도구, 1인 개발에 관한 기록 — 왕원하오의 개인 블로그.",
        "nav_home": "홈",
        "nav_blog": "블로그 홈",
        "subscribe": "RSS 구독",
        "sec_posts": "글", "sec_sites": "사이트 모음",
        "cluster_label": "운영 중인 다른 사이트",
        "empty_t": "글을 준비 중입니다",
        "empty_d": "아직 비어 있습니다. 곧 첫 글을 올리겠습니다.",
        "no_lang_t": "이 언어로 된 글이 없습니다",
        "no_lang_d": "이 글은 아직 번역되지 않았습니다. 중국어 원문을 읽어 보세요.",
        "count": "총 %d편",
        "back": "← 블로그로 돌아가기",
        "minutes": "약 %d분",
        "prev": "이전 글", "next": "다음 글",
        "updated": "마지막 업데이트 %s",
        "theme_to_dark": "다크 모드로 전환",
        "theme_to_light": "라이트 모드로 전환",
        "lang_switch": "언어 변경 · Change language",
        "site_nav": "사이트 내비게이션",
        "post_nav": "글 내비게이션",
        "sites_desc": [
            "사진 포트폴리오 · 메인 사이트",
            "Windows Phone 스타일 타일 갤러리",
            "마라톤 기록과 일정",
            "가속감 재현 드라이빙 시뮬레이터",
            "카메라 비교 도구 · 웹 버전",
        ],
    },
    "fr": {
        "site_title": "Le blog de Wang Wenhao",
        "site_desc": "Données, outils et développement en solo — le blog personnel de Wang Wenhao.",
        "nav_home": "Accueil",
        "nav_blog": "Le blog",
        "subscribe": "S'abonner",
        "sec_posts": "Articles", "sec_sites": "Mes sites",
        "cluster_label": "Mes autres sites",
        "empty_t": "Les articles arrivent",
        "empty_d": "Rien ici pour l'instant — le premier article ne va pas tarder.",
        "no_lang_t": "Aucun article dans cette langue",
        "no_lang_d": "Cet article n'est pas encore traduit. Lire la version chinoise.",
        "count": "%d article(s)",
        "back": "← Retour au blog",
        "minutes": "%d min de lecture",
        "prev": "Précédent", "next": "Suivant",
        "updated": "Mis à jour en %s",
        "theme_to_dark": "Passer en mode sombre",
        "theme_to_light": "Passer en mode clair",
        "lang_switch": "Changer de langue",
        "site_nav": "Navigation du site",
        "post_nav": "Navigation des articles",
        "sites_desc": [
            "Portfolio photo · site principal",
            "Galerie de tuiles façon Windows Phone",
            "Mon calendrier et mes résultats de marathon",
            "Simulateur de sensations d'accélération",
            "Outil de comparaison d'appareils photo · web",
        ],
    },
    "es": {
        "site_title": "El blog de Wang Wenhao",
        "site_desc": "Datos, herramientas y desarrollo en solitario — el blog personal de Wang Wenhao.",
        "nav_home": "Inicio",
        "nav_blog": "El blog",
        "subscribe": "Suscribirse",
        "sec_posts": "Artículos", "sec_sites": "Mis sitios",
        "cluster_label": "Mis otros sitios",
        "empty_t": "Los artículos están en camino",
        "empty_d": "Aquí no hay nada todavía — el primer artículo llegará pronto.",
        "no_lang_t": "No hay artículos en este idioma",
        "no_lang_d": "Este artículo aún no está traducido. Leer la versión en chino.",
        "count": "%d artículo(s)",
        "back": "← Volver al blog",
        "minutes": "%d min de lectura",
        "prev": "Anterior", "next": "Siguiente",
        "updated": "Actualizado en %s",
        "theme_to_dark": "Cambiar a modo oscuro",
        "theme_to_light": "Cambiar a modo claro",
        "lang_switch": "Cambiar de idioma",
        "site_nav": "Navegación del sitio",
        "post_nav": "Navegación de artículos",
        "sites_desc": [
            "Portafolio fotográfico · sitio principal",
            "Galería de mosaicos estilo Windows Phone",
            "Mi calendario y resultados de maratón",
            "Simulador de sensaciones de aceleración",
            "Herramienta de comparación de cámaras · web",
        ],
    },
    "de": {
        "site_title": "Wang Wenhaos Blog",
        "site_desc": "Daten, Werkzeuge und Solo-Entwicklung — der persönliche Blog von Wang Wenhao.",
        "nav_home": "Startseite",
        "nav_blog": "Blog-Startseite",
        "subscribe": "Abonnieren",
        "sec_posts": "Beiträge", "sec_sites": "Meine Sites",
        "cluster_label": "Meine anderen Websites",
        "empty_t": "Beiträge sind unterwegs",
        "empty_d": "Hier ist noch nichts — der erste Beitrag kommt bald.",
        "no_lang_t": "Keine Beiträge in dieser Sprache",
        "no_lang_d": "Dieser Beitrag ist noch nicht übersetzt. Lies das chinesische Original.",
        "count": "%d Beitrag/Beiträge",
        "back": "← Zurück zum Blog",
        "minutes": "%d Min. Lesezeit",
        "prev": "Vorheriger", "next": "Nächster",
        "updated": "Zuletzt aktualisiert: %s",
        "theme_to_dark": "Zum Dunkelmodus wechseln",
        "theme_to_light": "Zum Hellmodus wechseln",
        "lang_switch": "Sprache wechseln",
        "site_nav": "Website-Navigation",
        "post_nav": "Beitrags-Navigation",
        "sites_desc": [
            "Fotoportfolio · Hauptseite",
            "Kachelgalerie im Windows-Phone-Stil",
            "Mein Marathon-Kalender und meine Ergebnisse",
            "Fahrsimulator für Beschleunigungsgefühl",
            "Kameravergleich · Web-Version",
        ],
    },
}


# 语言下拉里「本文暂无该译文」的提示
LANG_PARTIAL = {
    "zh-CN": "灰显语言表示本文暂无该译文",
    "zh-Hant": "灰顯語言表示本文暫無該譯文",
    "en": "Greyed out = not translated yet",
    "ja": "グレーは未翻訳を示します",
    "ko": "회색은 아직 번역되지 않음을 뜻합니다",
    "fr": "Grisé = pas encore traduit",
    "es": "En gris = aún sin traducir",
    "de": "Ausgegraut = noch nicht übersetzt",
}


def T(lang, key):
    """取界面文案，缺键回退简中"""
    return (UI.get(lang) or UI[DEFAULT_LANG]).get(key) or UI[DEFAULT_LANG].get(key, "")


# ============================================================
# 多语言 URL / 路径
#   zh-CN（默认）：/blog/            /blog/<slug>/            /blog/feed.xml
#   其他语言：     /blog/<lang>/     /blog/<lang>/<slug>/     /blog/<lang>/feed.xml
# ============================================================
def lang_prefix(lang):
    return "" if lang == DEFAULT_LANG else lang + "/"


def home_url(lang):
    return SITE_BASE + "/" + lang_prefix(lang)


def post_url(slug, lang):
    return SITE_BASE + "/" + lang_prefix(lang) + slug + "/"


def feed_url(lang):
    return SITE_BASE + "/" + lang_prefix(lang) + "feed.xml"


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
  color-scheme:light;
  --paper:#FAF9F7;
  --ink:#191817;
  --muted:#6F6B64;
  --faint:#9B968D;
  --line:#E6E3DD;
  --line-strong:#D8D3C9;
  --accent:#4A5D54;
  --accent-soft:#EDEFEA;
  --on-accent:#FFFFFF;
  --bar-bg:rgba(250,249,247,.86);
  --toggle-bg:rgba(250,249,247,.82);
  --card-hover:#FFFFFF;
  --shadow:0 12px 34px rgba(0,0,0,.12);

  --serif:'Spectral','Noto Serif SC','Songti SC','STSong',Georgia,serif;
  --sans:'Hanken Grotesk','Noto Sans SC',-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;

  --measure:36em;
  --w:700px;
  --gutter:clamp(24px,6vw,40px);
  --section-gap:clamp(72px,11vh,116px);
}

/* 深色：与个人主页同一套 token */
:root[data-theme="dark"]{
  color-scheme:dark;
  --paper:#1B1C1E;
  --ink:#E9E7E2;
  --muted:#A9A59D;
  --faint:#8F8B83;
  --line:#34383D;
  --line-strong:#3F444A;
  --accent:#9FBFAB;
  --accent-soft:rgba(159,191,171,.12);
  --on-accent:#12140F;
  --bar-bg:rgba(27,28,30,.86);
  --toggle-bg:rgba(27,28,30,.82);
  --card-hover:#262A2E;
  --shadow:0 12px 34px rgba(0,0,0,.42);
}

/* 日 / 韩：优先本机字形，避免简体字串味 */
:root[lang="ja"]{
  --serif:'Noto Serif JP','Yu Mincho','YuMincho','Hiragino Mincho ProN','Noto Serif SC',Georgia,serif;
  --sans:'Noto Sans JP','Yu Gothic','YuGothic','Hiragino Sans','Noto Sans SC',sans-serif;
}
:root[lang="ko"]{
  --serif:'Noto Serif KR','Nanum Myeongjo','Apple SD Gothic Neo','Noto Serif SC',Georgia,serif;
  --sans:'Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic','Noto Sans SC',sans-serif;
}

*,*::before,*::after{box-sizing:border-box;}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth;}
body{
  margin:0;
  background:var(--paper);
  color:var(--ink);
  font-family:var(--sans);
  font-size:18px;
  line-height:1.85;
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
  color:var(--on-accent);
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
.prose h2{font-size:1.42rem;}
.prose h3{font-size:1.2rem;}
.prose h4{font-size:1.06rem;}
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
  font-size:.82rem;
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
  color:#0F6E56;
  background:#E1F5EE;
  border:1px solid #1D9E75;
}
/* 徽章暗色：保留色相，压低亮度避免刺眼 */
:root[data-theme="dark"] .p-flag-ai{
  color:#F3A7C2;
  background:rgba(214,51,108,.16);
  border-color:rgba(230,73,128,.48);
}
:root[data-theme="dark"] .p-flag-human{
  color:#7FD9BC;
  background:rgba(29,158,117,.16);
  border-color:rgba(29,158,117,.48);
}

/* ============================================================
   明暗切换 + 语言切换（顶部栏右侧，与主页同一套视觉语言）
   ============================================================ */
.bar-tools{display:flex;align-items:center;gap:14px;flex:none;}

.theme-toggle{
  width:30px;height:30px;
  display:grid;
  place-items:center;
  padding:0;
  border:1px solid var(--line-strong);
  border-radius:999px;
  background:var(--toggle-bg);
  color:var(--muted);
  cursor:pointer;
  flex:none;
  transition:color .22s ease,border-color .22s ease,background .22s ease;
}
.theme-toggle:hover{color:var(--accent);border-color:var(--accent);}
.theme-toggle:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
.theme-toggle svg{grid-area:1 / 1;width:14px;height:14px;display:block;}
.theme-toggle .ic-sun{display:none;}
:root[data-theme="dark"] .theme-toggle .ic-sun{display:block;}
:root[data-theme="dark"] .theme-toggle .ic-moon{display:none;}

.lang{position:relative;}
.lang-btn{
  display:inline-flex;
  align-items:center;
  gap:5px;
  height:30px;
  padding:0 10px 0 8px;
  border:1px solid var(--line-strong);
  border-radius:999px;
  background:var(--toggle-bg);
  color:var(--muted);
  font-family:var(--sans);
  font-size:.76rem;
  font-weight:400;
  letter-spacing:.06em;
  cursor:pointer;
  transition:color .22s ease,border-color .22s ease;
}
.lang-btn:hover{color:var(--accent);border-color:var(--accent);}
.lang-btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
.lang-btn svg{width:13px;height:13px;flex:none;}
.lang-btn .code{line-height:1;}

.lang-list{
  position:absolute;
  top:calc(100% + 8px);
  right:0;
  margin:0;
  padding:6px;
  list-style:none;
  min-width:174px;
  background:var(--paper);
  border:1px solid var(--line-strong);
  border-radius:6px;
  box-shadow:var(--shadow);
  z-index:30;
}
.lang-list[hidden]{display:none;}
.lang-list li{margin:0;}
.lang-list a,.lang-list span.off{
  display:flex;
  width:100%;
  align-items:baseline;
  justify-content:space-between;
  gap:12px;
  padding:7px 9px;
  border-radius:4px;
  color:var(--ink);
  font-family:var(--sans);
  font-size:.86rem;
  font-weight:400;
  line-height:1.5;
  text-align:left;
}
.lang-list a{transition:background .18s ease,color .18s ease;}
.lang-list a:hover{background:var(--accent-soft);color:var(--accent);}
.lang-list a:focus-visible{outline:2px solid var(--accent);outline-offset:-2px;}
.lang-list span.off{color:var(--faint);cursor:not-allowed;opacity:.62;}
.lang-list .code{
  font-size:.72rem;
  color:var(--faint);
  letter-spacing:.06em;
  font-variant-numeric:tabular-nums;
}
.lang-list a[aria-current="true"]{color:var(--accent);font-weight:500;}
.lang-list a[aria-current="true"] .code{color:var(--accent);font-weight:400;}
.lang-list .tnote{
  display:block;
  padding:5px 9px 3px;
  font-size:.72rem;
  color:var(--faint);
  letter-spacing:.02em;
  border-top:1px solid var(--line);
  margin-top:4px;
}

@media (max-width:600px){
  .bar-tools{gap:8px;}
  .lang-list{min-width:160px;}
  /* 站名可截断，保证右侧控件不被挤压（提高选择器权重以覆盖 HOME/POST_CSS） */
  .site-bar .bar-inner{gap:10px;}
  .site-bar .bar-left{flex:1 1 auto;min-width:0;}
  .site-bar .bar-left .mark{display:block;overflow:hidden;text-overflow:ellipsis;font-size:.94rem;}
  .site-bar .bar-right{gap:10px;}
  .site-bar .rss-t{display:none;}
  .site-bar .theme-toggle{width:28px;height:28px;}
  .site-bar .lang-btn{height:28px;padding:0 9px 0 7px;}
  .site-bar .lang-list{min-width:160px;}
}
"""

# ============================================================
# 博客首页专用样式
# ============================================================
HOME_CSS = """
/* ---- 顶部栏 ---- */
.site-bar{
  border-bottom:1px solid var(--line);
  background:var(--bar-bg);
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
  font-size:.82rem;
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
.blog-hero .hero-meta .rss-btn:hover{background:var(--accent);color:var(--on-accent);}
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
  font-size:.82rem;
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
  background:var(--card-hover);
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
.site-card .s-url{font-size:.80rem;color:var(--faint);letter-spacing:.01em;overflow-wrap:anywhere;}
.site-card:hover{border-color:var(--accent);background:var(--card-hover);}
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
  body{font-size:17px;}
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
  background:var(--bar-bg);
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
  font-size:.82rem;
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
  font-size:.82rem;
  color:var(--faint);
  border:1px solid var(--line);
  border-radius:2px;
  padding:2px 8px;
  letter-spacing:.02em;
}

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
  font-size:.82rem;
  color:var(--faint);
  letter-spacing:.03em;
  margin-bottom:3px;
}

@media (max-width:600px){
  body{font-size:17px;}
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
# HMGC 的说明部分是自然语言，随界面语言变化；AIGC 为通用缩写不译
FLAG_HUMAN_LABEL = {
    "zh-CN": "HMGC · 人工创作", "zh-Hant": "HMGC · 人工創作",
    "en": "HMGC · Human", "ja": "HMGC · 執筆",
    "ko": "HMGC · 직접 작성", "fr": "HMGC · Humain",
    "es": "HMGC · Humano", "de": "HMGC · Menschlich",
}
FLAG_HINTS = {
    # 正文显式说明块已按要求移除；AIGC 仅以标题下方徽章 + meta 隐式标识呈现。
    # 如需恢复正文提示，在此填写文案即可。
    "ai": "",
    "human": "",
}
_AIGC_ALIASES = {"ai", "aigc", "machine", "llm", "generated"}


def norm_author_type(v):
    """归一化为 'ai' | 'human'；缺省视为人工创作。"""
    s = str(v or "").strip().lower()
    return "ai" if s in _AIGC_ALIASES else "human"


def flag_badge(author_type, lang=DEFAULT_LANG):
    cls = "p-flag-ai" if author_type == "ai" else "p-flag-human"
    label = (FLAG_HUMAN_LABEL.get(lang) or FLAG_LABELS["human"]) \
        if author_type != "ai" else FLAG_LABELS["ai"]
    return '<span class="p-flag %s">%s</span>' % (cls, label)


def flag_note(author_type):
    hint = FLAG_HINTS.get(author_type, "")
    if not hint:
        return ""
    return '    <div class="aigc-note"><b>AIGC 标识</b> · %s</div>\n' % hint


import email.utils as email_utils


def collect_posts():
    """扫描 posts/，按 slug 归并多语言版本。

    文件命名约定：
        <slug>.md            默认语言（简体中文）
        <slug>.<lang>.md     其他语言，如 <slug>.en.md / <slug>.ja.md

    返回：
        [{
           "slug": str,
           "date": date,                    # 以默认语言版本为准
           "author_type": "ai"|"human",
           "langs": {lang: {"title","desc","tags","body","source"}}
        }]
    """
    raw_entries = []
    if not os.path.isdir(POSTS_DIR):
        return []

    for fn in sorted(os.listdir(POSTS_DIR)):
        if not fn.endswith(".md") or fn.startswith("_"):
            continue
        stem = fn[:-3]
        slug, lang = stem, DEFAULT_LANG
        if "." in stem:
            base, _, maybe = stem.rpartition(".")
            if maybe in LANGS:
                slug, lang = base, maybe

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

        raw_entries.append({
            "slug": str(meta.get("slug") or slug).strip(),
            "lang": lang,
            "title": str(meta["title"]),
            "date": d,
            "desc": str(meta.get("desc", "") or ""),
            "tags": [str(t) for t in (meta.get("tags") or [])],
            "body": body,
            "source": fn,
            "author_type": norm_author_type(meta.get("author_type")),
        })

    # 按 slug 归并
    groups = {}
    for e in raw_entries:
        g = groups.setdefault(e["slug"], {"slug": e["slug"], "langs": {}})
        if e["lang"] in g["langs"]:
            print("  [warn] %s 的 %s 版本重复，后出现的覆盖前者" % (e["slug"], e["lang"]))
        g["langs"][e["lang"]] = {
            "title": e["title"],
            "desc": e["desc"],
            "tags": e["tags"],
            "body": e["body"],
            "source": e["source"],
        }
        if e["lang"] == DEFAULT_LANG:
            g["date"] = e["date"]
            g["author_type"] = e["author_type"]

    posts = []
    for slug, g in groups.items():
        if slug in LANGS:
            print("  [skip] slug %r 与语言代码冲突，请改名" % slug)
            continue
        if DEFAULT_LANG not in g["langs"]:
            print("  [skip] %s 缺少默认语言文件 %s.md（其他语言版本无法挂载）"
                  % (slug, slug))
            continue
        base = g["langs"][DEFAULT_LANG]
        posts.append({
            "slug": slug,
            "date": g["date"],
            "author_type": g["author_type"],
            "langs": g["langs"],
            "title": base["title"],
        })

    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
    return posts


def reading_minutes(body):
    """阅读时间：中文 400 字/分钟、西文 200 词/分钟"""
    plain = re.sub(r"[#*`>\-\[\]()!#]", "", body)
    cjk = len(re.findall(r"[\u4e00-\u9fff]", plain))
    words = len(re.findall(r"[A-Za-z0-9]+", plain))
    return max(1, int(round(cjk / 400.0 + words / 200.0)))


# ============================================================
# 日期与月份本地化
# ============================================================
MONTHS_FULL = {
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
           "August", "September", "Oktober", "November", "Dezember"],
}

MONTHS_SHORT = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "fr": ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août",
           "sept.", "oct.", "nov.", "déc."],
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
    "de": ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.",
           "Sept.", "Okt.", "Nov.", "Dez."],
}


def fmt_date(d, lang):
    if lang in ("zh-CN", "zh-Hant"):
        return "%d 年 %d 月 %d 日" % (d.year, d.month, d.day)
    if lang == "ja":
        return "%d年%d月%d日" % (d.year, d.month, d.day)
    if lang == "ko":
        return "%d년 %d월 %d일" % (d.year, d.month, d.day)
    if lang == "en":
        return "%s %d, %d" % (MONTHS_FULL["en"][d.month - 1], d.day, d.year)
    if lang == "fr":
        return "%d %s %d" % (d.day, MONTHS_FULL["fr"][d.month - 1], d.year)
    if lang == "es":
        return "%d de %s de %d" % (d.day, MONTHS_FULL["es"][d.month - 1], d.year)
    if lang == "de":
        return "%d. %s %d" % (d.day, MONTHS_FULL["de"][d.month - 1], d.year)
    return d.isoformat()


def fmt_month_year(d, lang):
    if lang in ("zh-CN", "zh-Hant"):
        return "%d 年 %d 月" % (d.year, d.month)
    if lang == "ja":
        return "%d年%d月" % (d.year, d.month)
    if lang == "ko":
        return "%d년 %d월" % (d.year, d.month)
    name = MONTHS_FULL.get(lang, MONTHS_FULL["en"])[d.month - 1]
    return "%s %d" % (name, d.year)


# ============================================================
# 共享片段：主题引导脚本 / 图标 / 语言切换 / 明暗切换
# ============================================================
THEME_BOOT = """<script>
/* 主题引导：必须早于样式渲染，避免明暗二次闪烁 */
(function () {
  try {
    var saved = localStorage.getItem('theme');
    var theme = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
    var m = document.querySelector('meta[name="theme-color"]');
    if (m) m.setAttribute('content', theme === 'dark' ? '#1B1C1E' : '#FAF9F7');
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'light');
  }
})();
</script>"""

UI_JS = """
/* 明暗切换：写入 data-theme 并记忆；同步 aria 与移动端地址栏色 */
(function () {
  var root = document.documentElement;
  var btn = document.querySelector('.theme-toggle');
  var meta = document.querySelector('meta[name="theme-color"]');
  if (!btn) return;

  function isDark() { return root.getAttribute('data-theme') === 'dark'; }

  function sync() {
    var dark = isDark();
    var label = dark ? btn.getAttribute('data-light-label') : btn.getAttribute('data-dark-label');
    btn.setAttribute('aria-label', label);
    btn.setAttribute('aria-pressed', dark ? 'true' : 'false');
    btn.title = label;
    if (meta) meta.setAttribute('content', dark ? '#1B1C1E' : '#FAF9F7');
  }

  btn.addEventListener('click', function () {
    var next = isDark() ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('theme', next); } catch (e) {}
    sync();
  });

  sync();
})();

/* 语言下拉：真实链接跳转，点击时把选择记到 localStorage('rw.lang')，
   与个人主页共用同一偏好键，回到主页时语言自动一致 */
(function () {
  var btn = document.getElementById('langBtn');
  var list = document.getElementById('langList');
  if (!btn || !list) return;

  function setOpen(open) {
    list.hidden = !open;
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  btn.addEventListener('click', function (e) {
    e.stopPropagation();
    setOpen(list.hidden);
  });

  list.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('a[data-lang-choice]') : null;
    if (!a) return;
    try { localStorage.setItem('rw.lang', a.getAttribute('data-lang-choice')); } catch (err) {}
  });

  document.addEventListener('click', function (e) {
    if (!list.hidden && !(e.target.closest && e.target.closest('.lang'))) setOpen(false);
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !list.hidden) { setOpen(false); btn.focus(); }
  });
})();
"""


GLOBE_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="9"/>'
    '<path d="M3 12h18M12 3c2.5 2.6 3.8 5.7 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.7-3.8-9S9.5 5.6 12 3Z"/>'
    '</svg>'
)

SUN_SVG = (
    '<svg class="ic ic-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="4"/>'
    '<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2'
    'M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
)
MOON_SVG = (
    '<svg class="ic ic-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5a8.5 8.5 0 1 0 11 11Z"/></svg>'
)


def hreflang_links(urls):
    """urls: [(lang, url)]，首个为 x-default"""
    out = []
    for lang, url in urls:
        out.append('<link rel="alternate" hreflang="%s" href="%s">' % (lang, esc(url)))
    if urls:
        out.append('<link rel="alternate" hreflang="x-default" href="%s">' % esc(urls[0][1]))
    return "\n".join(out)


def lang_switcher(lang, current_url, alt_urls=None):
    """语言下拉。

    alt_urls: {lang: url} 表示该语言页面存在；缺键 = 本文暂无该语言译文，
              渲染为不可点击并给出提示。首页传 None 表示全语言可用。
    """
    items = []
    missing = False
    for l in LANGS:
        exists = True if alt_urls is None else (l in alt_urls)
        url = (home_url(l) if alt_urls is None else alt_urls.get(l))
        label = LANG_NAME[l]
        code = LANG_BADGE[l]
        if exists:
            cur = ' aria-current="true"' if l == lang else ""
            items.append(
                '      <li><a href="%s" hreflang="%s" lang="%s" data-lang-choice="%s"%s>'
                '%s<span class="code">%s</span></a></li>'
                % (esc(url), l, l, l, cur, label, code)
            )
        else:
            missing = True
            items.append(
                '      <li><span class="off" lang="%s">%s<span class="code">%s</span></span></li>'
                % (l, label, code)
            )
    if missing:
        items.append('      <li class="tnote">%s</li>' % esc(LANG_PARTIAL.get(lang) or LANG_PARTIAL["zh-CN"]))

    return (
        '<div class="lang" id="lang">\n'
        '  <button class="lang-btn" id="langBtn" type="button" aria-expanded="false" '
        'aria-controls="langList" aria-haspopup="true" aria-label="%s">\n'
        '    %s\n'
        '    <span class="code">%s</span>\n'
        '  </button>\n'
        '  <ul class="lang-list" id="langList" hidden>\n'
        '%s\n'
        '  </ul>\n'
        '</div>'
        % (esc(T(lang, "lang_switch")), GLOBE_SVG, LANG_BADGE[lang], "\n".join(items))
    )


def theme_toggle(lang):
    return (
        '<button class="theme-toggle" type="button" aria-pressed="false" '
        'data-dark-label="%s" data-light-label="%s" aria-label="%s" title="%s">%s%s</button>'
        % (esc(T(lang, "theme_to_dark")), esc(T(lang, "theme_to_light")),
           esc(T(lang, "theme_to_dark")), esc(T(lang, "theme_to_dark")),
           SUN_SVG, MOON_SVG)
    )


def site_bar(current="", lang=DEFAULT_LANG, alt_urls=None):
    """current: 'home' | 'post'"""
    right = [
        '<a class="rss" href="%s" type="application/rss+xml">%s<span class="rss-t">RSS</span></a>'
        % (esc(feed_url(lang)), RSS_ICON)
    ]
    if current == "home":
        home_href = ("https://retter.wang/" if lang == DEFAULT_LANG
                     else "https://retter.wang/?lang=%s" % lang)
        right.append('<a class="nav-link" href="%s">%s</a>'
                     % (esc(home_href), esc(T(lang, "nav_home"))))
    else:
        right.append('<a class="nav-link" href="%s">%s</a>'
                     % (esc(home_url(lang)), esc(T(lang, "nav_blog"))))

    tools = (
        '<div class="bar-tools">\n      %s\n      %s\n    </div>'
        % (lang_switcher(lang, home_url(lang), alt_urls), theme_toggle(lang))
    )

    return (
        '<header class="site-bar">\n'
        '  <div class="bar-inner">\n'
        '    <div class="bar-left">\n'
        '      <a class="mark" href="%s">%s</a>\n'
        '      <span class="bar-sub">%s</span>\n'
        '    </div>\n'
        '    <nav class="bar-right" aria-label="%s">\n'
        '      %s\n'
        '    %s\n'
        '    </nav>\n'
        '  </div>\n'
        '</header>'
        % (esc(home_url(lang)), esc(T(lang, "site_title")), esc(T(lang, "site_desc")),
           esc(T(lang, "site_nav")), "\n      ".join(right), tools)
    )


def cluster_html(lang):
    descs = T(lang, "sites_desc") or []
    cards = []
    for i, (name, url, href) in enumerate(SITES):
        desc = descs[i] if i < len(descs) else ""
        cards.append(
            '        <a class="site-card" href="%s" target="_blank" rel="noopener">\n'
            '          <span class="s-name">%s%s</span>\n'
            '          <span class="s-desc">%s</span>\n'
            '          <span class="s-url">%s</span>\n'
            '        </a>' % (esc(href), esc(name), ARROW_SVG, esc(desc), esc(url))
        )
    return '      <div class="site-cluster">\n' + "\n".join(cards) + "\n      </div>"


# ============================================================
# 页面骨架：head 公共部分
# ============================================================
HEAD_COMMON = """<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#FAF9F7">
%(theme_boot)s
<title>%(title)s</title>
<meta name="description" content="%(desc)s">
<meta name="author" content="%(author)s">
%(extra_meta)s<link rel="alternate" type="application/rss+xml" title="%(site_title)s" href="%(feed)s">
<link rel="canonical" href="%(canonical)s">
%(hreflang)s
<link rel="icon" href="%(base)s/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="%(base)s/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="%(base)s/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="%(base)s/apple-touch-icon.png">
%(fonts)s"""


FOOT_BAR = """<footer class="blog-foot">
  <div class="wrap">
    <div class="f-row">
      <span>© %(year)d %(author)s</span>
      <span>%(updated)s</span>
    </div>
    <div class="f-links">
      <a class="link" href="%(home_href)s">%(label_home)s</a>
      <a class="link" href="%(feed)s">RSS</a>
      <a class="link" href="%(blog_home)s">%(label_blog)s</a>
      <a class="link" href="mailto:%(email)s">%(email)s</a>
    </div>
  </div>
</footer>"""


def footer_html(lang):
    home_href = ("https://retter.wang/" if lang == DEFAULT_LANG
                 else "https://retter.wang/?lang=%s" % lang)
    return FOOT_BAR % {
        "year": datetime.date.today().year,
        "author": esc(SITE_AUTHOR),
        "updated": esc(T(lang, "updated") % fmt_month_year(datetime.date.today(), lang)),
        "home_href": esc(home_href),
        "feed": esc(feed_url(lang)),
        "blog_home": esc(home_url(lang)),
        "label_home": esc(T(lang, "nav_home")),
        "label_blog": esc(T(lang, "nav_blog")),
        "email": AUTHOR_EMAIL,
    }


# ============================================================
# 博客首页
# ============================================================
def build_home(posts, lang):
    localized = [p for p in posts if lang in p["langs"]]

    if localized:
        items = []
        for p in localized:
            e = p["langs"][lang]
            tags = ""
            if e["tags"]:
                tags = (
                    '          <span class="p-tags">\n'
                    + "\n".join('            <span>%s</span>' % esc(t) for t in e["tags"])
                    + "\n          </span>"
                )
            desc_block = ""
            if e["desc"]:
                desc_block = '            <p class="p-desc">%s</p>\n' % esc(e["desc"])
            tags_block = (tags + "\n") if tags else ""
            items.append(
                '        <li>\n'
                '          <a class="post-item" href="%s">\n'
                '            <span class="p-meta">\n'
                '              <time datetime="%s">%s</time>\n'
                '              %s\n'
                '            </span>\n'
                '            <span class="p-title">%s</span>\n'
                '%s%s'
                '          </a>\n'
                '        </li>'
                % (
                    esc(post_url(p["slug"], lang)),
                    p["date"].isoformat(),
                    esc(fmt_date(p["date"], lang)),
                    flag_badge(p["author_type"], lang),
                    esc(e["title"]),
                    desc_block,
                    tags_block,
                )
            )
        list_block = '      <ul class="post-list">\n' + "\n".join(items) + "\n      </ul>"
        count_meta = '      <span>%s</span>\n' % esc(T(lang, "count") % len(localized))
    elif posts:
        # 有其他语言的文章，但没有本语言的
        list_block = (
            '      <div class="empty-note">\n'
            '        <p class="e-t">%s</p>\n'
            '        <p class="e-d"><a class="link" href="%s">%s</a></p>\n'
            '      </div>' % (esc(T(lang, "no_lang_t")), esc(home_url(DEFAULT_LANG)),
                               esc(T(lang, "no_lang_d")))
        )
        count_meta = ""
    else:
        list_block = (
            '      <div class="empty-note">\n'
            '        <p class="e-t">%s</p>\n'
            '        <p class="e-d">%s</p>\n'
            '      </div>' % (esc(T(lang, "empty_t")), esc(T(lang, "empty_d")))
        )
        count_meta = ""

    alt = [(l, home_url(l)) for l in LANGS]
    extra_meta = (
        '<meta property="og:type" content="website">\n'
        '<meta property="og:title" content="%s">\n'
        '<meta property="og:description" content="%s">\n'
        '<meta property="og:url" content="%s">\n'
        '<meta property="og:locale" content="%s">\n'
        % (esc(T(lang, "site_title")), esc(T(lang, "site_desc")),
           esc(home_url(lang)), lang.replace("-", "_"))
    )

    return """<!DOCTYPE html>
<html lang="%(lang)s" data-theme="light">
<head>
%(head)s
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
      <a class="rss-btn" href="%(feed)s" type="application/rss+xml">%(rss_icon)s %(subscribe)s</a>
%(count_meta)s
    </div>
  </section>

  <section class="section" id="posts">
    <div class="section-head">
      <h2>%(sec_posts)s</h2><span class="rule"></span>
    </div>
%(list_block)s
  </section>

  <section class="section" id="sites">
    <div class="section-head">
      <h2>%(sec_sites)s</h2><span class="rule"></span>
    </div>
    <p class="extra-label" style="margin:0 0 14px;font-size:.8rem;color:var(--faint);letter-spacing:.03em;">%(cluster_label)s</p>
%(cluster)s
  </section>

</main>

%(footer)s

<script>
%(js)s
</script>
</body>
</html>
""" % {
        "lang": lang,
        "head": HEAD_COMMON % {
            "theme_boot": THEME_BOOT,
            "title": esc(T(lang, "site_title")),
            "desc": esc(T(lang, "site_desc")),
            "author": esc(SITE_AUTHOR),
            "extra_meta": extra_meta,
            "site_title": esc(T(lang, "site_title")),
            "feed": esc(feed_url(lang)),
            "canonical": esc(home_url(lang)),
            "hreflang": hreflang_links(alt),
            "base": SITE_BASE,
            "fonts": FONT_LINK,
        },
        "base_css": BASE_CSS,
        "home_css": HOME_CSS,
        "bar": site_bar(current="home", lang=lang),
        "title": esc(T(lang, "site_title")),
        "desc": esc(T(lang, "site_desc")),
        "feed": esc(feed_url(lang)),
        "rss_icon": RSS_ICON,
        "subscribe": esc(T(lang, "subscribe")),
        "count_meta": count_meta,
        "sec_posts": esc(T(lang, "sec_posts")),
        "sec_sites": esc(T(lang, "sec_sites")),
        "cluster_label": esc(T(lang, "cluster_label")),
        "list_block": list_block,
        "cluster": cluster_html(lang),
        "footer": footer_html(lang),
        "js": UI_JS,
    }


# ============================================================
# 文章页
# ============================================================
def build_post(group, lang, prev_group, next_group):
    entry = group["langs"][lang]
    md = markdown.Markdown(
        extensions=["extra", "sane_lists", "toc", "admonition", "nl2br"],
        extension_configs={"toc": {"permalink": False}},
        output_format="html5",
    )
    content = md.convert(entry["body"])

    # 表格外包横向滚动容器，避免宽表（如 DNS 记录表）在窄屏撑破页面
    content = re.sub(
        r"<table>(.*?)</table>",
        lambda m: '<div class="table-wrap"><table>%s</table></div>' % m.group(1),
        content,
        flags=re.DOTALL,
    )

    minutes = reading_minutes(entry["body"])

    tags = ""
    if entry["tags"]:
        tags = (
            '        <div class="p-tags">\n'
            + "\n".join('          <span>%s</span>' % esc(t) for t in entry["tags"])
            + "\n        </div>"
        )

    _atype = group.get("author_type", "human")
    flag = flag_badge(_atype, lang)
    flag_meta = "ai-generated" if _atype == "ai" else "human-authored"

    def nav_item(p, cls, lbl_key):
        if not p:
            return '        <span></span>'
        e = p["langs"][lang]
        return (
            '        <a class="%s" href="%s">\n'
            '          <span class="lbl">%s</span>%s\n'
            '        </a>' % (cls, esc(post_url(p["slug"], lang)),
                            esc(T(lang, lbl_key)), esc(e["title"]))
        )

    nav = [nav_item(prev_group, "prev", "prev"), nav_item(next_group, "next", "next")]

    # 本页可用的语言版本
    alt_urls = {l: post_url(group["slug"], l)
                for l in LANGS if l in group["langs"]}
    alt = [(l, alt_urls[l]) for l in LANGS if l in alt_urls]

    extra_meta = (
        '<meta property="og:type" content="article">\n'
        '<meta property="og:title" content="%s">\n'
        '<meta property="og:description" content="%s">\n'
        '<meta property="og:url" content="%s">\n'
        '<meta property="og:locale" content="%s">\n'
        '<meta property="article:published_time" content="%s">\n'
        '<meta name="aigc" content="%s">\n'
        % (esc(entry["title"]), esc(entry["desc"] or entry["title"]),
           esc(post_url(group["slug"], lang)), lang.replace("-", "_"),
           group["date"].isoformat(), flag_meta)
    )

    return """<!DOCTYPE html>
<html lang="%(lang)s" data-theme="light">
<head>
%(head)s
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
      <a class="back" href="%(home)s">%(back)s</a>
      <h1>%(title)s</h1>
      <div class="p-meta">
        <time datetime="%(iso)s">%(date)s</time>
        <span>%(minutes)s</span>
        %(flag)s
%(tags)s
      </div>
    </header>

    <div class="post-body prose">
%(content)s
    </div>

    <footer class="post-foot">
      <nav class="p-nav" aria-label="%(post_nav)s">
%(nav)s
      </nav>
    </footer>
  </article>

</main>

%(footer)s

<script>
%(js)s
</script>
</body>
</html>
""" % {
        "lang": lang,
        "head": HEAD_COMMON % {
            "theme_boot": THEME_BOOT,
            "title": "%s · %s" % (esc(entry["title"]), esc(T(lang, "site_title"))),
            "desc": esc(entry["desc"] or entry["title"]),
            "author": esc(SITE_AUTHOR),
            "extra_meta": extra_meta,
            "site_title": esc(T(lang, "site_title")),
            "feed": esc(feed_url(lang)),
            "canonical": esc(post_url(group["slug"], lang)),
            "hreflang": hreflang_links(alt),
            "base": SITE_BASE,
            "fonts": FONT_LINK,
        },
        "base_css": BASE_CSS,
        "post_css": POST_CSS,
        "bar": site_bar(current="post", lang=lang, alt_urls=alt_urls),
        "home": esc(home_url(lang)),
        "back": esc(T(lang, "back")),
        "title": esc(entry["title"]),
        "iso": group["date"].isoformat(),
        "date": esc(fmt_date(group["date"], lang)),
        "minutes": esc(T(lang, "minutes") % minutes),
        "flag": flag,
        "tags": tags,
        "content": content,
        "nav": "\n".join(nav),
        "post_nav": esc(T(lang, "post_nav")),
        "footer": footer_html(lang),
        "js": UI_JS,
    }


# ============================================================
# RSS
# ============================================================
def build_feed(posts, lang):
    localized = [p for p in posts if lang in p["langs"]]
    now = datetime.datetime.now().astimezone()
    items = []
    for p in localized:
        e = p["langs"][lang]
        link = post_url(p["slug"], lang)
        desc = e["desc"] or e["title"]
        cats = "".join("<category>%s</category>" % esc(t) for t in e["tags"])
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
                esc(e["title"]), esc(link), esc(link),
                email_utils.format_datetime(
                    datetime.datetime.combine(p["date"], datetime.time(9, 0))
                    .replace(tzinfo=now.tzinfo)
                ),
                esc(desc), cats,
            )
        )
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>%(title)s</title>
    <link>%(home)s</link>
    <atom:link href="%(feed)s" rel="self" type="application/rss+xml"/>
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
        "title": esc(T(lang, "site_title")),
        "home": esc(home_url(lang)),
        "feed": esc(feed_url(lang)),
        "desc": esc(T(lang, "site_desc")),
        "lang": lang,
        "email": AUTHOR_EMAIL,
        "author": esc(SITE_AUTHOR),
        "lastbuild": email_utils.format_datetime(now),
        "items": "\n".join(items),
    }


# ============================================================
# 输出路径与主流程
# ============================================================
def out_dir(lang, slug=None):
    parts = [HERE]
    if lang != DEFAULT_LANG:
        parts.append(lang)
    if slug:
        parts.append(slug)
    return os.path.join(*parts)


def write(path, text):
    d = os.path.dirname(path)
    if not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def clean_generated():
    """清掉非默认语言的旧目录，避免语言/文章删除后留下残页"""
    for name in os.listdir(HERE):
        full = os.path.join(HERE, name)
        if os.path.isdir(full) and name in LANGS and name != DEFAULT_LANG:
            shutil.rmtree(full)


def main():
    posts = collect_posts()
    print("找到文章 %d 篇" % len(posts))
    for p in posts:
        print("  · %-28s %s  [%s]" % (p["slug"], p["date"], ", ".join(
            l for l in LANGS if l in p["langs"])))

    clean_generated()

    # 首页 + RSS：每种语言各一份
    for lang in LANGS:
        write(os.path.join(out_dir(lang), "index.html"), build_home(posts, lang))
        write(os.path.join(out_dir(lang), "feed.xml"), build_feed(posts, lang))
        print("生成 %-9s index.html / feed.xml" % (lang or "zh-CN"))

    # 文章页：每种语言 × 每篇有译文的文章
    for lang in LANGS:
        localized = [p for p in posts if lang in p["langs"]]
        for i, p in enumerate(localized):
            prev_post = localized[i + 1] if i + 1 < len(localized) else None
            next_post = localized[i - 1] if i > 0 else None
            d = out_dir(lang, p["slug"])
            if os.path.isdir(d):
                shutil.rmtree(d)
            os.makedirs(d)
            write(os.path.join(d, "index.html"), build_post(p, lang, prev_post, next_post))
            print("生成 %s" % os.path.relpath(os.path.join(d, "index.html"), HERE))

    # 索引信息（便于外部脚本读取）
    write(os.path.join(HERE, "posts.json"), json.dumps(
        [
            {
                "slug": p["slug"],
                "date": p["date"].isoformat(),
                "author_type": p["author_type"],
                "langs": {l: {
                    "title": p["langs"][l]["title"],
                    "desc": p["langs"][l]["desc"],
                    "tags": p["langs"][l]["tags"],
                    "url": post_url(p["slug"], l),
                } for l in LANGS if l in p["langs"]},
            }
            for p in posts
        ],
        ensure_ascii=False, indent=2))
    print("生成 posts.json")


if __name__ == "__main__":
    main()
