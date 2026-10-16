#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate en-news.html from news.html (works for both the legacy and the
current auto-generated template). Translates the page chrome (head meta, nav,
header, stat labels, filter labels, anchor bar, footer) to English while
preserving the Chinese article list and the category-filter JS (which matches
Chinese .news-tag text against Chinese data-cat values). Article links point
to the same Chinese article pages.
"""
import re, io

SRC = "news.html"
DST = "en-news.html"

with io.open(SRC, encoding="utf-8") as f:
    html = f.read()

# 1. html lang
html = html.replace('<html lang="zh-CN">', '<html lang="en">', 1)

# 2. title
html = html.replace(
    "<title>资讯中心 | 宽幅数码印花行业干货 - 匠领数码</title>",
    "<title>News Center | Wide-Width Digital Printing Insights | J.LINK TEXTILE</title>",
    1)

# 3. description meta
html = html.replace(
    '<meta name="description" content="匠领数码资讯中心：宽幅数码印花、分散印花、涤纶印花等 B 端加工知识 · 工厂实拍 · 采购指南 · 每天 6 篇自动更新。">',
    '<meta name="description" content="J.LINK TEXTILE News Center: wide-width digital printing, disperse printing, polyester printing B2B knowledge, factory insights and buying guides — 6 new articles auto-published daily.">',
    1)

# 4. canonical (keep zh href, add en + hreflang alternates)
html = html.replace(
    '<link rel="canonical" href="https://bu6789.com/news.html">',
    '<link rel="canonical" href="https://bu6789.com/news.html">\n'
    '  <link rel="alternate" hreflang="zh" href="https://bu6789.com/news.html">\n'
    '  <link rel="alternate" hreflang="en" href="https://bu6789.com/en-news.html">',
    1)

# 5. og meta
html = html.replace(
    '<meta property="og:title" content="资讯中心 | 匠领数码">',
    '<meta property="og:title" content="News Center | J.LINK TEXTILE">', 1)
html = html.replace(
    '<meta property="og:description" content="宽幅数码印花行业干货 · 每天 6 篇自动更新">',
    '<meta property="og:description" content="Wide-width digital printing industry insights · 6 new articles daily">', 1)
html = html.replace(
    '<meta property="og:url" content="https://bu6789.com/news.html">',
    '<meta property="og:url" content="https://bu6789.com/en-news.html">', 1)

# 6. nav block -> English
en_nav = '''<nav>
  <a class="nav-logo" href="/en.html">🧵 J.LINK TEXTILE <span>匠领数码</span></a>
  <ul class="nav-links">
    <li><a href="/en.html#products">Products</a></li>
    <li><a href="/en.html#about">About</a></li>
    <li><a href="en-news.html" style="color:var(--brand);font-weight:600">News</a></li>
    <li><a href="/en.html#faq">FAQ</a></li>
    <li><a href="/en.html#contact" class="nav-cta">Get Quote</a></li>
    <li><a href="https://app.bu6789.com" target="_blank" rel="noopener">Image Search</a></li>
    <li><a href="news.html">中文</a></li>
  </ul>
</nav>'''
html = re.sub(r"<nav>.*?</nav>", en_nav, html, count=1, flags=re.S)

# 7. page-header h1 + p
html = html.replace("<h1>📰 资讯中心</h1>", "<h1>📰 News Center</h1>", 1)
html = html.replace(
    "<p>宽幅数码印花行业干货 · 每天 6 篇自动更新</p>",
    "<p>Wide-width digital printing industry insights · 6 new articles auto-published daily</p>", 1)

# 8. stat labels
html = html.replace('<div class="label">文章总数</div>', '<div class="label">Total Articles</div>', 1)
html = html.replace('<div class="label">更新天数</div>', '<div class="label">Days Updated</div>', 1)
html = html.replace('<div class="label">应用案例</div>', '<div class="label">Case Studies</div>', 1)
html = html.replace('<div class="label">采购指南</div>', '<div class="label">Buying Guides</div>', 1)

# 9. filter row labels (translate visible text, keep dynamic counts + data-cat)
html = html.replace('<span style="margin:8px 8px 0 0;color:#666">筛选：</span>',
                    '<span style="margin:8px 8px 0 0;color:#666">Filter:</span>', 1)
html = html.replace(">全部 (", ">All (", 1)
html = html.replace(">应用案例 (", ">Case Studies (", 1)
html = html.replace(">市场趋势 (", ">Market Trends (", 1)
html = html.replace(">环保与品质 (", ">Eco &amp; Quality (", 1)
html = html.replace(">采购指南 (", ">Buying Guides (", 1)

# 10. anchor bar
html = html.replace('<span style="margin-right:12px;color:#999;font-size:.85em">快速跳转：</span>',
                    '<span style="margin-right:12px;color:#999;font-size:.85em">Jump to:</span>', 1)
html = html.replace('>↑ 顶部</a>', '>↑ Top</a>', 1)

# 11. footer "返回首页" -> "Back to Home" (handles both "返回首页" and "← 返回首页")
html = html.replace("返回首页", "Back to Home")

with io.open(DST, "w", encoding="utf-8") as f:
    f.write(html)

print("Wrote", DST, "bytes:", len(html.encode("utf-8")))
