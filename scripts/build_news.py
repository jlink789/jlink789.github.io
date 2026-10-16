#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_news.py
扫描 articles/ 目录，生成 news.html（中文）与 en-news.html（英文界面，文章列表仍为中文）。
供 GH Actions 调用，每天文章生成完后自动重跑。

样式：统一沿用官网 assets/site.css 设计系统（.page-header / .stats-bar / .cat-filter-row
/ .anchor-bar / .news-list 等），导航与全站核心页一致（含图库找图、语言切换、资讯中心）。

输出：
- news.html  (中文资讯中心)
- en-news.html (英文界面资讯中心)
- index.html (news 区块更新为最新 10 篇)
- sitemap.xml (加 news.html 入口 + 最新文章 lastmod)
"""
import json
import re
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

ROOT = Path(__file__).parent.parent  # 项目根
ARTICLES = ROOT / "articles"
NEWS_HTML = ROOT / "news.html"
EN_NEWS_HTML = ROOT / "en-news.html"
INDEX_HTML = ROOT / "index.html"
SITEMAP = ROOT / "sitemap.xml"

# 分类规则（与 auto_article.py 保持一致）
CATEGORY_RULES = [
    ("环保与品质", ["环保", "品质", "绿色", "低碳", "Oeko", "色牢度", "oeko", "OEKO", "环保与品质"]),
    ("采购指南", ["采购", "指南", "选购", "怎么选", "如何选", "选择", "挑选", "采购商"]),
    ("市场趋势", ["趋势", "市场", "需求", "增长", "行情", "动态", "观察", "分析", "数据", "解读", "现状"]),
    ("应用案例", ["案例", "应用", "实战", "解析", "工艺", "技术", "方法", "参数", "技巧", "操作", "流程"]),
]

CAT_COLOR = {
    "应用案例": ("#1a73e8", "#e8f0fe"),
    "采购指南": ("#0d904f", "#e6f4ea"),
    "市场趋势": ("#e37400", "#fef7e0"),
    "环保与品质": ("#0f9d58", "#e6f4ea"),
}

# 英文界面下，分类按钮可见文案（data-cat 仍为中文，供筛选 JS 匹配）
CAT_EN = {
    "应用案例": "Case Studies",
    "采购指南": "Buying Guides",
    "市场趋势": "Market Trends",
    "环保与品质": "Eco & Quality",
}


def categorize(title: str) -> str:
    for cat, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw in title:
                return cat
    return "应用案例"


def collect_articles() -> list:
    """扫描 articles/ 目录，提取每篇的标题/日期/分类。"""
    result = []
    for f in sorted(ARTICLES.glob("*.html"), reverse=True):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        m = re.search(r"<title>(.*?)</title>", content)
        if m:
            parts = [p.strip() for p in m.group(1).split("|")]
            title = parts[0] if parts else f.stem
        else:
            title = f.stem
        stem = f.stem
        date_short = stem[:10]  # 2026-06-22
        result.append({
            "file": f.name,
            "stem": stem,
            "date": date_short,
            "title": title,
            "category": categorize(title),
        })
    return result


# ── 导航（与全站核心页一致：图库找图 + 语言切换 + 资讯中心）──
ZH_NAV = '''<nav>
  <a class="nav-logo" href="/"><img class="nav-logo-mark" src="assets/logo-mark-white.png" alt="匠领纺织 J.LINK TEXTILE" width="38" height="38"><span class="nav-logo-stack"><b>匠领数码</b><i>J.LINK TEXTILE · 匠领纺织</i></span></a>
  <ul class="nav-links">
    <li><a href="/">首页</a></li>
    <li><a href="/#products">产品中心</a></li>
    <li><a href="applications.html">应用领域</a></li>
    <li><a href="/about.html">关于我们</a></li>
    <li><a href="/news.html">资讯中心</a></li>
    <li><a href="/#faq">常见问题</a></li>
        <li><a href="https://app.bu6789.com" target="_blank" rel="noopener" class="nav-app">图库找图</a></li>
<li><a href="/#contact" class="nav-cta">立即咨询</a></li>
      <li><a href="en-news.html" class="lang-switch">EN</a></li>
  </ul>
</nav>'''

EN_NAV = '''<nav>
  <a class="nav-logo" href="/en.html"><img class="nav-logo-mark" src="assets/logo-mark-white.png" alt="J.LINK TEXTILE 匠领纺织" width="38" height="38"><span class="nav-logo-stack"><b>J.LINK TEXTILE</b><i>匠领数码 · 匠领纺织</i></span></a>
  <ul class="nav-links">
    <li><a href="/en.html">Home</a></li>
    <li><a href="/en.html#products">Products</a></li>
    <li><a href="en-applications.html">Applications</a></li>
    <li><a href="/en.html#about">About</a></li>
    <li><a href="en-news.html" style="color:var(--brand);font-weight:600">News</a></li>
    <li><a href="/en.html#faq">FAQ</a></li>
        <li><a href="https://app.bu6789.com" target="_blank" rel="noopener" class="nav-app">Image Search</a></li>
<li><a href="/en.html#contact" class="nav-cta">Get Quote</a></li>
      <li><a href="news.html" class="lang-switch">中文</a></li>
  </ul>
</nav>'''

ZH_FOOTER = '''<footer>
  <img class="footer-logo" src="assets/logo-white.png" alt="匠领纺织 J.LINK TEXTILE · 匠领数码" loading="lazy">
  <p><strong>匠领数码 · J.LINK TEXTILE</strong></p>
  <p>浙江省绍兴市柯桥区齐贤镇兴浦路88号盛超针纺园区二幢南面五楼</p>
  <p>📞 张先生 17769886009</p>
  <p>© 2026 匠领数码 · 主营 200-320CM 宽幅数码印花 · 分散印花 · 涤纶印花 · 1米起印</p>
</footer>'''

EN_FOOTER = '''<footer>
  <img class="footer-logo" src="assets/logo-white.png" alt="J.LINK TEXTILE 匠领数码 · 匠领纺织" loading="lazy">
  <p><strong>J.LINK TEXTILE · 匠领数码</strong></p>
  <p>No.88 Xingpu Road, Qixian Town, Keqiao District, Shaoxing, Zhejiang</p>
  <p>📞 Mr. Zhang +86-177-6988-6009</p>
  <p>© 2026 J.LINK TEXTILE · Wide-width digital printing 200-320CM · disperse & polyester printing · MOQ 1m</p>
</footer>'''

STRINGS = {
    "zh": {
        "lang_attr": "zh-CN",
        "title": "资讯中心 | 宽幅数码印花行业干货 - 匠领数码",
        "description": "匠领数码资讯中心：宽幅数码印花、分散印花、涤纶印花等 B 端加工知识 · 工厂实拍 · 采购指南 · 每天 6 篇自动更新。",
        "canonical": "https://bu6789.com/news.html",
        "hreflang_zh": "https://bu6789.com/news.html",
        "hreflang_en": "https://bu6789.com/en-news.html",
        "og_title": "资讯中心 | 匠领数码",
        "og_desc": "宽幅数码印花行业干货 · 每天 6 篇自动更新",
        "hero_badge": "绍兴柯桥 · 中国轻纺城",
        "hero_h1": "资讯中心",
        "hero_sub": "宽幅数码印花行业干货 · 每天 6 篇自动更新",
        "stat_total": "文章总数",
        "stat_days": "更新天数",
        "stat_cases": "应用案例",
        "stat_guide": "采购指南",
        "filter_label": "筛选：",
        "all_label": "全部",
        "anchor_label": "快速跳转：",
        "top_label": "↑ 顶部",
        "articles_unit": "篇",
        "foot_text": "— 已是全部 {total} 篇文章 —",
        "jsonld_name": "匠领数码资讯中心",
        "jsonld_desc": "宽幅数码印花行业干货 · 每天自动更新",
        "nav": ZH_NAV,
        "footer": ZH_FOOTER,
    },
    "en": {
        "lang_attr": "en",
        "title": "News Center | Wide-Width Digital Printing Insights | J.LINK TEXTILE",
        "description": "J.LINK TEXTILE News Center: wide-width digital printing, disperse printing, polyester printing B2B knowledge, factory insights and buying guides — 6 new articles auto-published daily.",
        "canonical": "https://bu6789.com/en-news.html",
        "hreflang_zh": "https://bu6789.com/news.html",
        "hreflang_en": "https://bu6789.com/en-news.html",
        "og_title": "News Center | J.LINK TEXTILE",
        "og_desc": "Wide-width digital printing industry insights · 6 new articles daily",
        "hero_badge": "Shaoxing Keqiao · China Textile City",
        "hero_h1": "News Center",
        "hero_sub": "Wide-width digital printing industry insights · 6 new articles auto-published daily",
        "stat_total": "Total Articles",
        "stat_days": "Days Updated",
        "stat_cases": "Case Studies",
        "stat_guide": "Buying Guides",
        "filter_label": "Filter:",
        "all_label": "All",
        "anchor_label": "Jump to:",
        "top_label": "↑ Top",
        "articles_unit": "articles",
        "foot_text": "— That's all {total} articles —",
        "jsonld_name": "J.LINK TEXTILE News Center",
        "jsonld_desc": "Wide-width digital printing industry insights · 6 new articles daily",
        "nav": EN_NAV,
        "footer": EN_FOOTER,
    },
}


def build_news_html(data: list, lang: str = "zh") -> str:
    S = STRINGS[lang]
    by_date = defaultdict(list)
    for r in data:
        by_date[r["date"]].append(r)
    cat_count = Counter(r["category"] for r in data)
    total = len(data)
    sorted_dates = sorted(by_date.keys(), reverse=True)

    # 日期分组 HTML
    groups_html = []
    for d in sorted_dates:
        items = sorted(by_date[d], key=lambda x: x["stem"], reverse=True)
        items_li = []
        for r in items:
            title = r["title"].replace("&", "&amp;")
            items_li.append(
                f'          <li><span class="news-tag">{r["category"]}</span>'
                f'<a href="articles/{r["file"]}">{title}</a></li>'
            )
        groups_html.append(
            f'      <section class="date-group" id="d-{d}" data-date="{d}">\n'
            f'        <h3>{d} <span class="news-date">{len(items)} {S["articles_unit"]}</span></h3>\n'
            f'        <ul class="news-list">\n' + "\n".join(items_li) + '\n        </ul>\n'
            f'      </section>'
        )

    # 顶部日期锚点
    date_anchors = []
    for d in sorted_dates[:10]:
        n = len(by_date[d])
        date_anchors.append(
            f'<a href="#d-{d}">{d}<span class="news-date">{n}</span></a>'
        )

    # 分类筛选按钮（data-cat 用中文，供 JS 匹配；英文界面仅可见文案翻译）
    cat_filters = []
    for cat, n in sorted(cat_count.items(), key=lambda x: -x[1]):
        label = CAT_EN.get(cat, cat) if lang == "en" else cat
        cat_filters.append(
            f'<button class="cat-filter" data-cat="{cat}">{label} ({n})</button>'
        )

    # JSON-LD
    jsonld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": S["jsonld_name"],
        "description": S["jsonld_desc"],
        "numberOfItems": total,
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "url": f"https://bu6789.com/articles/{r['file']}",
                "name": r["title"],
            }
            for i, r in enumerate(data[:20])
        ],
    }

    html = f"""<!DOCTYPE html>
<html lang="{S['lang_attr']}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{S['title']}</title>
  <meta name="description" content="{S['description']}">
  <link rel="canonical" href="{S['canonical']}">
  <link rel="alternate" hreflang="zh" href="{S['hreflang_zh']}">
  <link rel="alternate" hreflang="en" href="{S['hreflang_en']}">
  <meta name="robots" content="index,follow">
  <meta property="og:title" content="{S['og_title']}">
  <meta property="og:description" content="{S['og_desc']}">
  <meta property="og:url" content="{S['canonical']}">
  <meta property="og:image" content="https://bu6789.com/og-image.png">
  <meta property="og:type" content="website">
  <meta name="theme-color" content="#14171c">
  <link rel="icon" href="favicon.ico" sizes="any">
  <link rel="icon" type="image/png" sizes="32x32" href="favicon-32x32.png">
  <link rel="icon" type="image/png" sizes="16x16" href="favicon-16x16.png">
  <link rel="apple-touch-icon" sizes="180x180" href="apple-touch-icon.png">
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>

{S['nav']}

<header class="page-header">
  <div class="hero-badge">{S['hero_badge']}</div>
  <h1>{S['hero_h1']}</h1>
  <p>{S['hero_sub']}</p>
</header>

<div class="container">
  <div class="stats-bar">
    <div class="stat-item"><div class="stat-num">{total}</div><div class="stat-label">{S['stat_total']}</div></div>
    <div class="stat-item"><div class="stat-num">{len(by_date)}</div><div class="stat-label">{S['stat_days']}</div></div>
    <div class="stat-item"><div class="stat-num">{cat_count.get('应用案例', 0)}</div><div class="stat-label">{S['stat_cases']}</div></div>
    <div class="stat-item"><div class="stat-num">{cat_count.get('采购指南', 0)}</div><div class="stat-label">{S['stat_guide']}</div></div>
  </div>

  <div class="cat-filter-row" id="catFilterRow">
    <span class="filter-label">{S['filter_label']}</span>
    <button class="cat-filter active" data-cat="all">{S['all_label']} ({total})</button>
    {''.join(cat_filters)}
  </div>

  <div class="anchor-bar">
    <span class="anchor-label">{S['anchor_label']}</span>
    {''.join(date_anchors)}
    <a href="#bottom">{S['top_label']}</a>
  </div>

  <div id="articleList">
{chr(10).join(groups_html)}
  </div>

  <p id="bottom" class="news-foot">{S['foot_text'].format(total=total)}</p>
</div>

{S['footer']}

<script>
  document.querySelectorAll('.cat-filter').forEach(btn => {{
    btn.addEventListener('click', () => {{
      const cat = btn.dataset.cat;
      document.querySelectorAll('.cat-filter').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const groups = document.querySelectorAll('.date-group');
      let visible = 0;
      groups.forEach(g => {{
        const lis = g.querySelectorAll('li');
        let hasVisible = false;
        lis.forEach(li => {{
          const tag = li.querySelector('.news-tag');
          if (cat === 'all' || (tag && tag.textContent.includes(cat))) {{
            li.style.display = '';
            hasVisible = true; visible++;
          }} else {{
            li.style.display = 'none';
          }}
        }});
        g.style.display = hasVisible ? '' : 'none';
      }});
      const numEl = document.querySelector('.stat-item .num');
      if (numEl) numEl.textContent = cat === 'all' ? '{total}' : visible;
    }});
  }});
</script>

<script type="application/ld+json">
{json.dumps(jsonld, ensure_ascii=False, indent=2)}
</script>

</body>
</html>"""
    return html


def update_index_news(data: list) -> int:
    """同步首页 news 区块为最新 10 篇。返回是否实际改动。"""
    if not INDEX_HTML.exists():
        return 0
    content = INDEX_HTML.read_text(encoding="utf-8")
    top10 = data[:10]
    items_html = []
    for r in top10:
        title = r["title"].replace("&", "&amp;").replace('"', "&quot;")
        items_html.append(
            f'        <li><span class="news-tag" style="background:{CAT_COLOR.get(r["category"], ("#666","#eee"))[1]};color:{CAT_COLOR.get(r["category"], ("#666","#eee"))[0]}">{r["category"]}</span> '
            f'<a href="articles/{r["file"]}">{title}</a> '
            f'<span class="news-date" style="color:#999;font-size:.85em">· {r["date"]}</span></li>'
        )
    new_section = f'''<section id="news" style="padding:60px 20px;max-width:900px;margin:0 auto;background:#fafbfc;border-radius:12px;margin-top:40px">
  <h2 style="font-size:1.6em;color:#1a1a2e;margin-bottom:8px">📰 最新资讯</h2>
  <p style="color:#666;margin-bottom:24px;font-size:.95em">工厂实拍、行业干货、面料趋势 · 每天自动更新</p>
  <ul style="list-style:none;padding:0;margin:0;line-height:2">
{chr(10).join(items_html)}
  </ul>
  <div style="text-align:center;margin-top:28px">
    <a href="news.html" class="btn-primary" style="display:inline-block;text-decoration:none">查看全部 {len(data)} 篇 →</a>
  </div>
</section>'''
    m = re.search(r'<section id="news".*?</section>', content, re.DOTALL)
    if not m:
        return 0
    if m.group(0) == new_section:
        return 0
    INDEX_HTML.write_text(content.replace(m.group(0), new_section, 1), encoding="utf-8")
    return 1


def update_sitemap(data: list) -> int:
    """确保 sitemap.xml 里有 news.html 入口。返回是否实际改动。"""
    if not SITEMAP.exists():
        return 0
    content = SITEMAP.read_text(encoding="utf-8")
    if "news.html" in content:
        return 0
    new_url = f'''  <url>
    <loc>https://bu6789.com/news.html</loc>
    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
'''
    SITEMAP.write_text(content.replace("</urlset>", new_url + "</urlset>"), encoding="utf-8")
    return 1


def main():
    data = collect_articles()
    if not data:
        print("FAIL: 无文章可处理")
        sys.exit(1)
    for lang in ("zh", "en"):
        html = build_news_html(data, lang)
        target = NEWS_HTML if lang == "zh" else EN_NEWS_HTML
        target.write_text(html, encoding="utf-8")
        print(f"OK: {len(data)} 篇 → {target.name} ({lang})")
    idx_changed = update_index_news(data)
    sm_changed = update_sitemap(data)
    print(f"首页{'已更新' if idx_changed else '无变化'} | sitemap{'已更新' if sm_changed else '无变化'}")


if __name__ == "__main__":
    main()
