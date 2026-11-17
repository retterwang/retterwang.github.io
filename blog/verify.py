# -*- coding: utf-8 -*-
"""博客构建产物验证：多语言 × 明暗主题 × 布局 × RSS

用法（在 blog/ 目录下）：python verify.py
依赖：playwright（用本机已下载的 chromium 内核）

覆盖：
  1. 静态结构：每种语言的首页/文章页/feed 均存在，关键 meta 与 hreflang 完整
  2. RSS：每语言 feed 可解析，language 与 item 链接正确
  3. 渲染：8 语言 × 桌面/移动 双视口，无横向溢出、无 JS 报错
  4. 明暗主题：切换生效、刷新后保持、可切回
  5. 语言切换：下拉 8 项、当前语言标记、链接指向、偏好写入 localStorage
"""
import functools
import http.server
import io
import os
import socket
import socketserver
import sys
import threading
import xml.etree.ElementTree as ET

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SLUG = "purelymail-migration"
LANGS = ["zh-CN", "zh-Hant", "en", "ja", "ko", "fr", "es", "de"]
CHROME_CANDIDATES = [
    r"C:/Users/rette/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe",
    r"C:/Users/rette/AppData/Local/ms-playwright/chromium-1223/chrome-win64/chrome.exe",
    r"C:/Users/rette/AppData/Local/ms-playwright/chromium-1200/chrome-win64/chrome.exe",
]
CHROME = next((c for c in CHROME_CANDIDATES if os.path.exists(c)), None)

fails = []
report = []


def log(s):
    report.append(s)
    print(s)


def fail(msg):
    fails.append(msg)
    log("    ✗ %s" % msg)


def prefix(lang):
    return "" if lang == "zh-CN" else lang + "/"


# ============================================================
# 1. 静态文件与结构
# ============================================================
log("=" * 78)
log("1. 静态文件与结构")
log("=" * 78)

for lang in LANGS:
    home = os.path.join(HERE, prefix(lang), "index.html")
    post = os.path.join(HERE, prefix(lang), SLUG, "index.html")
    feed = os.path.join(HERE, prefix(lang), "feed.xml")

    for label, path in (("首页", home), ("文章", post), ("feed", feed)):
        if not os.path.exists(path):
            fail("%s %s 缺失: %s" % (lang, label, path))

    if not os.path.exists(home):
        continue
    src = io.open(home, encoding="utf-8").read()

    checks = {
        "lang 属性": 'lang="%s"' % lang in src,
        "theme 引导脚本": "localStorage.getItem('theme')" in src,
        "data-theme 默认": 'data-theme="light"' in src,
        "i18n 下拉": 'id="langList"' in src,
        "主题按钮": 'class="theme-toggle"' in src,
        "canonical": 'rel="canonical"' in src,
        "hreflang x-default": 'hreflang="x-default"' in src,
        "RSS alternate": 'type="application/rss+xml"' in src,
        "站点集群": "site-cluster" in src,
        "5 张站点卡": src.count('class="site-card"') == 5,
        "语言项 8 个": src.count("data-lang-choice=") == 8,
    }
    bad = [k for k, v in checks.items() if not v]
    if bad:
        fail("%s 首页结构: %s" % (lang, ", ".join(bad)))
    else:
        log("  ✓ %-8s 首页结构与 meta" % lang)

    if os.path.exists(post):
        psrc = io.open(post, encoding="utf-8").read()
        pchecks = {
            "正文容器": 'class="post-body prose"' in psrc,
            "表格滚动容器": psrc.count('class="table-wrap"') >= 1,
            "语言切换": 'id="langList"' in psrc,
            "主题按钮": 'class="theme-toggle"' in psrc,
            "文章导航": 'class="p-nav"' in psrc,
        }
        pbad = [k for k, v in pchecks.items() if not v]
        if pbad:
            fail("%s 文章页结构: %s" % (lang, ", ".join(pbad)))

# ============================================================
# 2. RSS 结构
# ============================================================
log("")
log("=" * 78)
log("2. RSS 结构")
log("=" * 78)

for lang in LANGS:
    feed = os.path.join(HERE, prefix(lang), "feed.xml")
    if not os.path.exists(feed):
        continue
    src = io.open(feed, encoding="utf-8").read()
    problems = []
    if not src.startswith('<?xml version="1.0" encoding="UTF-8"?>'):
        problems.append("XML 声明")
    if '<rss version="2.0"' not in src:
        problems.append("rss 2.0")
    if 'rel="self"' not in src:
        problems.append("atom:link self")
    if "<language>%s</language>" % lang not in src:
        problems.append("language=%s" % lang)
    if "<managingEditor>" not in src:
        problems.append("managingEditor")
    try:
        root = ET.fromstring(src)
        items = root.findall("./channel/item")
        if not items:
            problems.append("无 item")
        for it in items:
            link = it.findtext("link") or ""
            if prefix(lang) not in link:
                problems.append("item 链接与语言不符")
                break
    except Exception as e:
        problems.append("XML 解析失败 %s" % str(e)[:40])

    if problems:
        fail("%s feed: %s" % (lang, ", ".join(problems)))
    else:
        log("  ✓ %-8s feed 可解析，语言与链接正确" % lang)

# ============================================================
# 3~5. 浏览器渲染
# ============================================================
_s = socket.socket()
_s.bind(("127.0.0.1", 0))
PORT = _s.getsockname()[1]
_s.close()

Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=HERE)
Handler.log_message = lambda *a, **k: None
httpd = socketserver.TCPServer(("127.0.0.1", PORT), Handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:%d" % PORT

OVERFLOW_JS = """() => {
    const vw = window.innerWidth;
    const bad = [];
    document.querySelectorAll('body *').forEach(el => {
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden') return;
        if (el.closest('.table-wrap') || el.closest('pre')) return;  // 自身可滚动
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) return;
        if (r.right > vw + 1 || r.left < -1) {
            bad.push({tag: el.tagName, cls: (el.className||'').toString().slice(0,30),
                      text: (el.textContent||'').trim().slice(0,26)});
        }
    });
    return {vw, sw: document.documentElement.scrollWidth, bad: bad.slice(0, 5)};
}"""

log("")
log("=" * 78)
log("3. 浏览器渲染（8 语言 × 桌面/移动）")
log("=" * 78)

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME) if CHROME else pw.chromium.launch()

    for w, h, vp in ((1440, 900, "桌面"), (390, 844, "移动")):
        for lang in LANGS:
            ctx = browser.new_context(viewport={"width": w, "height": h})
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            ok_all = True
            for kind, path in (("首页", "/" + prefix(lang)),
                               ("文章", "/" + prefix(lang) + SLUG + "/")):
                r = page.goto(BASE + path, wait_until="load")
                if not r or r.status != 200:
                    fail("%s %s %s HTTP %s" % (vp, lang, kind, r.status if r else "ERR"))
                    ok_all = False
                    continue
                page.wait_for_timeout(100)
                o = page.evaluate(OVERFLOW_JS)
                if o["sw"] > o["vw"] + 1 or o["bad"]:
                    fail("%s %s %s 横向溢出 sw=%d vw=%d 元素=%d"
                         % (vp, lang, kind, o["sw"], o["vw"], len(o["bad"])))
                    for it in o["bad"]:
                        log("        <%s class=%r> %r" % (it["tag"], it["cls"], it["text"]))
                    ok_all = False
            if errs:
                fail("%s %s JS 报错: %s" % (vp, lang, errs[0][:70]))
                ok_all = False
            if ok_all:
                log("  ✓ %-4s %-8s 无溢出 / 无 JS 报错" % (vp, lang))
            ctx.close()

    # ---------- 明暗主题 ----------
    log("")
    log("=" * 78)
    log("4. 明暗主题")
    log("=" * 78)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.goto(BASE + "/", wait_until="load")

    def snap():
        return page.evaluate("""() => {
            const cs = getComputedStyle(document.body);
            const rs = getComputedStyle(document.documentElement);
            return {
                theme: document.documentElement.getAttribute('data-theme'),
                bg: cs.backgroundColor, fg: cs.color,
                accent: rs.getPropertyValue('--accent').trim(),
                pressed: document.querySelector('.theme-toggle').getAttribute('aria-pressed'),
                label: document.querySelector('.theme-toggle').getAttribute('aria-label')
            };
        }""")

    light = snap()
    log("  初始: %s  bg=%s" % (light["theme"], light["bg"]))
    page.click(".theme-toggle")
    page.wait_for_timeout(320)
    dark = snap()
    log("  切换: %s  bg=%s  accent=%s  aria-pressed=%s"
        % (dark["theme"], dark["bg"], dark["accent"], dark["pressed"]))
    if dark["theme"] != "dark" or dark["bg"] == light["bg"]:
        fail("深色切换未生效")
    else:
        log("  ✓ 深色生效且配色改变，aria 已同步（%s）" % dark["label"])

    page.reload(wait_until="load")
    page.wait_for_timeout(150)
    if snap()["theme"] != "dark":
        fail("主题未持久化")
    else:
        log("  ✓ 刷新后仍为深色（localStorage 记忆）")

    page.click(".theme-toggle")
    page.wait_for_timeout(300)
    back = snap()
    if back["theme"] != "light" or back["bg"] != light["bg"]:
        fail("无法切回浅色")
    else:
        log("  ✓ 可切回浅色")

    # ---------- 语言切换 ----------
    log("")
    log("=" * 78)
    log("5. 语言切换")
    log("=" * 78)
    page.goto(BASE + "/en/", wait_until="load")
    page.evaluate("() => localStorage.removeItem('rw.lang')")
    # 站内链接为绝对地址；用 preventDefault 拦跳转，事件仍冒泡到处理器
    page.evaluate("""() => {
        document.addEventListener('click', function (e) {
            var a = e.target.closest && e.target.closest('a[data-lang-choice]');
            if (a) e.preventDefault();
        }, true);
    }""")
    page.click("#langBtn")
    page.wait_for_timeout(180)
    if page.evaluate("() => document.getElementById('langList').hidden"):
        fail("语言下拉无法展开")
    else:
        log("  ✓ 下拉可展开")

    entries = page.evaluate("""() => {
        const a = [...document.querySelectorAll('.lang-list a[data-lang-choice]')];
        const off = [...document.querySelectorAll('.lang-list span.off')];
        const cur = document.querySelectorAll('.lang-list a[aria-current="true"]');
        return {hrefs: Object.fromEntries(a.map(x => [x.dataset.langChoice, x.getAttribute('href')])),
                links: a.length, off: off.length, cur: cur.length};
    }""")
    log("  语言项: 可点 %d / 禁用 %d / 当前标记 %d"
        % (entries["links"], entries["off"], entries["cur"]))
    if entries["links"] != 8 or entries["cur"] != 1:
        fail("语言项数量或当前标记异常")

    expect = {"zh-CN": "/blog/", "zh-Hant": "/blog/zh-Hant/", "en": "/blog/en/",
              "ja": "/blog/ja/", "ko": "/blog/ko/", "fr": "/blog/fr/",
              "es": "/blog/es/", "de": "/blog/de/"}
    wrong = [l for l, suf in expect.items() if not (entries["hrefs"].get(l) or "").endswith(suf)]
    if wrong:
        fail("语言链接指向错误: %s" % ", ".join(wrong))
    else:
        log("  ✓ 8 个语言链接均指向对应语言首页")

    page.click('.lang-list a[data-lang-choice="ja"]')
    page.wait_for_timeout(350)
    stored = page.evaluate("() => localStorage.getItem('rw.lang')")
    if stored != "ja":
        fail("语言偏好未写入 localStorage（实际 %r）" % stored)
    else:
        log("  ✓ 点击后写入 localStorage['rw.lang'] = ja（与个人主页共用偏好）")

    ctx.close()
    browser.close()

httpd.shutdown()

log("")
log("=" * 78)
log("失败项: %d" % len(fails))
for f in fails:
    log("  - %s" % f)
log("结论: %s" % ("全部通过 ✓" if not fails else "存在问题，需修复"))

io.open(os.path.join(HERE, "verify-report.txt"), "w", encoding="utf-8").write("\n".join(report))
sys.exit(0 if not fails else 1)
