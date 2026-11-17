# -*- coding: utf-8 -*-
"""博客本地渲染验证：DOM 检查 + 文本溢出检测 + 截图 + 链接检查

用法：python verify.py
输出：同目录 verify-report.txt（UTF-8）、shot-*.png
"""
import os
import io
import sys
import json
import urllib.parse

from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "index.html")
FEED = os.path.join(HERE, "feed.xml")
REPORT = os.path.join(HERE, "verify-report.txt")

out = []


def log(s):
    out.append(s)


# ---------- 静态文件检查 ----------
log("=" * 70)
log("1. 静态文件检查")
log("=" * 70)

for name in ("index.html", "feed.xml", "favicon.ico"):
    p = os.path.join(HERE, name)
    log("  %-16s %s  (%d bytes)" % (
        name,
        "OK " if os.path.exists(p) else "MISSING",
        os.path.getsize(p) if os.path.exists(p) else 0,
    ))

with open(INDEX, "r", encoding="utf-8") as f:
    html_src = f.read()

CHECKS = {
    "lang=zh-CN": 'lang="zh-CN"' in html_src,
    "charset UTF-8": 'charset="UTF-8"' in html_src,
    "viewport meta": 'name="viewport"' in html_src,
    "title 非空": "<title>王文昊的博客</title>" in html_src,
    "description meta": 'name="description"' in html_src,
    "canonical": 'rel="canonical"' in html_src,
    "og:title": 'property="og:title"' in html_src,
    "og:url": 'property="og:url"' in html_src,
    "RSS alternate link": 'type="application/rss+xml"' in html_src,
    "rss href feed.xml": 'href="https://retter.wang/blog/feed.xml"' in html_src,
    "站点集群区块": "站点集群" in html_src,
    "Gallery 卡片": "abetterplace2.live" in html_src,
    "Metro 子路径": "abetterplace2.live/metro/" in html_src,
    "Marathon 子域": "marathon.abetterplace2.live" in html_src,
    "PEDAL 子域": "pedal.abetterplace2.live" in html_src,
    "CAMCOP 子域": "camera.abetterplace2.live" in html_src,
    "无 Intro 卡片": "abetterplace2.live/intro/" not in html_src and ">Intro<" not in html_src,
    "无 metro 旧域名": "metro.abetterplace2.live" not in html_src,
    "无 intro 旧域名": "intro.abetterplace2.live" not in html_src,
    "空状态提示": "文章正在路上" in html_src,
    "backlink 主页": 'href="https://retter.wang/"' in html_src,
    "邮箱链接": "mailto:me@retter.wang" in html_src,
    "favicon link": 'href="https://retter.wang/blog/favicon.ico"' in html_src,
}
log("\n  静态检查项：")
for k, v in CHECKS.items():
    log("    [%s] %s" % ("PASS" if v else "FAIL", k))

# ---------- RSS 结构检查 ----------
log("\n" + "=" * 70)
log("2. RSS feed.xml 结构检查")
log("=" * 70)
with open(FEED, "r", encoding="utf-8") as f:
    feed_src = f.read()
feed_checks = {
    "XML 声明": feed_src.startswith('<?xml version="1.0" encoding="UTF-8"?>'),
    "rss version 2.0": '<rss version="2.0"' in feed_src,
    "atom:link self": 'rel="self"' in feed_src,
    "channel title": "<title>王文昊的博客</title>" in feed_src,
    "channel link": "<link>https://retter.wang/blog/</link>" in feed_src,
    "description": "<description>" in feed_src,
    "language": "<language>zh-CN</language>" in feed_src,
    "managingEditor": "<managingEditor>" in feed_src,
    "lastBuildDate": "<lastBuildDate>" in feed_src,
    "generator": "<generator>" in feed_src,
}
for k, v in feed_checks.items():
    log("    [%s] %s" % ("PASS" if v else "FAIL", k))

# 尝试 XML 解析
try:
    import xml.etree.ElementTree as ET

    ET.fromstring(feed_src)
    log("    [PASS] XML 格式可解析")
except Exception as e:
    log("    [FAIL] XML 解析失败: %s" % e)

# ---------- 渲染检查 ----------
log("\n" + "=" * 70)
log("3. 浏览器渲染检查（Playwright / Chromium）")
log("=" * 70)

url = "file:///" + INDEX.replace("\\", "/")

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    results = {}

    # --- 桌面 ---
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(800)

    dom = page.evaluate(
        """() => {
        const q = s => document.querySelector(s);
        const qa = s => Array.from(document.querySelectorAll(s));
        const overflow = [];
        // 文本溢出检测：用 Range 量实际文本宽度 vs 容器宽度
        qa('body *').forEach(el => {
            if (!el.children.length && el.textContent.trim()) {
                const r = document.createRange();
                r.selectNodeContents(el);
                const rects = r.getClientRects();
                if (!rects.length) return;
                const maxRight = Math.max(...Array.from(rects).map(x => x.right));
                const cw = el.clientWidth;
                if (cw > 0 && maxRight - el.getBoundingClientRect().left > cw + 1.5) {
                    overflow.push({
                        tag: el.tagName.toLowerCase(),
                        cls: el.className.toString().slice(0, 40),
                        text: el.textContent.trim().slice(0, 46),
                        over: Math.round(maxRight - el.getBoundingClientRect().left - cw)
                    });
                }
            }
        });
        const links = qa('a[href]').map(a => ({
            href: a.href, text: a.textContent.trim().slice(0,30)
        }));
        return {
            title: document.title,
            h1: q('h1') ? q('h1').textContent.trim() : null,
            h2s: qa('.section-head h2').map(x => x.textContent.trim()),
            siteCards: qa('.site-card').length,
            postItems: qa('.post-item').length,
            emptyNote: !!q('.empty-note'),
            docHeight: document.documentElement.scrollHeight,
            bodyOverflowX: document.documentElement.scrollWidth > window.innerWidth + 1,
            scrollWidth: document.documentElement.scrollWidth,
            innerWidth: window.innerWidth,
            overflow: overflow,
            links: links,
            fontFamily: getComputedStyle(document.body).fontFamily,
            bg: getComputedStyle(document.body).backgroundColor,
            color: getComputedStyle(document.body).color
        };
    }"""
    )
    results["desktop"] = results.get("desktop", {})
    results["desktop"].update(dom)

    log("  标题: %s" % results["desktop"]["title"])
    log("  H1  : %s" % results["desktop"]["h1"])
    log("  区块: %s" % " / ".join(results["desktop"]["h2s"]))
    log("  站点卡片数: %d" % results["desktop"]["siteCards"])
    log("  文章条目数: %d（空状态: %s）" % (results["desktop"]["postItems"], results["desktop"]["emptyNote"]))
    log("  整页高度: %d px" % results["desktop"]["docHeight"])
    log("  背景色: %s   正文色: %s" % (results["desktop"]["bg"], results["desktop"]["color"]))
    log("  横向溢出: %s (scrollWidth=%d / innerWidth=%d)"
        % (results["desktop"]["bodyOverflowX"], results["desktop"]["scrollWidth"], results["desktop"]["innerWidth"]))
    log("  文本溢出元素: %d" % len(results["desktop"]["overflow"]))
    for o in results["desktop"]["overflow"][:12]:
        log("     - <%s class=%s> %r 超出 %dpx" % (o["tag"], o["cls"], o["text"], o["over"]))

    page.screenshot(path=os.path.join(HERE, "shot-desktop.png"), full_page=True)

    # --- 移动端 ---
    m = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    m.goto(url, wait_until="networkidle")
    m.wait_for_timeout(800)
    mob = m.evaluate(
        """() => {
        const overflow = [];
        Array.from(document.querySelectorAll('body *')).forEach(el => {
            if (!el.children.length && el.textContent.trim()) {
                const r = document.createRange();
                r.selectNodeContents(el);
                const rects = r.getClientRects();
                if (!rects.length) return;
                const maxRight = Math.max(...Array.from(rects).map(x => x.right));
                const cw = el.clientWidth;
                if (cw > 0 && maxRight - el.getBoundingClientRect().left > cw + 1.5) {
                    overflow.push({
                        tag: el.tagName.toLowerCase(),
                        cls: el.className.toString().slice(0, 40),
                        text: el.textContent.trim().slice(0, 40)
                    });
                }
            }
        });
        return {
            docHeight: document.documentElement.scrollHeight,
            overflowX: document.documentElement.scrollWidth > window.innerWidth + 1,
            scrollWidth: document.documentElement.scrollWidth,
            innerWidth: window.innerWidth,
            overflow: overflow
        };
    }"""
    )
    log("\n  移动端 390px：")
    log("    整页高度: %d px" % mob["docHeight"])
    log("    横向溢出: %s (scrollWidth=%d / innerWidth=%d)"
        % (mob["overflowX"], mob["scrollWidth"], mob["innerWidth"]))
    log("    文本溢出元素: %d" % len(mob["overflow"]))
    for o in mob["overflow"][:12]:
        log("       - <%s class=%s> %r" % (o["tag"], o["cls"], o["text"]))
    m.screenshot(path=os.path.join(HERE, "shot-mobile.png"), full_page=True)

    # --- 链接检查 ---
    log("\n" + "=" * 70)
    log("4. 链接检查")
    log("=" * 70)
    internal, external = [], []
    for l in results["desktop"]["links"]:
        if l["href"].startswith("https://retter.wang"):
            internal.append(l)
        else:
            external.append(l)
    log("  内部链接（retter.wang）：")
    for l in internal:
        log("    %-44s %s" % (l["href"], l["text"]))
    log("  外部链接：")
    for l in external:
        log("    %-44s %s" % (l["href"], l["text"]))

    browser.close()

# 汇总
log("\n" + "=" * 70)
log("5. 汇总")
log("=" * 70)
static_fail = [k for k, v in CHECKS.items() if not v]
feed_fail = [k for k, v in feed_checks.items() if not v]
overflow_total = len(results["desktop"]["overflow"]) + len(mob["overflow"])
log("  静态检查失败: %s" % (static_fail if static_fail else "无"))
log("  RSS 检查失败: %s" % (feed_fail if feed_fail else "无"))
log("  文本溢出总数: %d" % overflow_total)
log("  横向溢出: 桌面=%s 移动=%s" % (results["desktop"]["bodyOverflowX"], mob["overflowX"]))
all_ok = not static_fail and not feed_fail and overflow_total == 0 \
    and not results["desktop"]["bodyOverflowX"] and not mob["overflowX"]
log("  最终结论: %s" % ("全部通过" if all_ok else "存在问题，见上方 FAIL 项"))

with open(REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("done ->", REPORT)
