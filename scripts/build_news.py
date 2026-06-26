#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_news.py
扫描 articles/ 目录，生成 news.html 资讯中心列表页 + 同步首页 news 区块。
供 GH Actions 调用，每天文章生成完后自动重跑。

输出：
- news.html  (含全部文章)
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


def build_news_html(data: list) -> str:
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
            color, bg = CAT_COLOR.get(r["category"], ("#666", "#eee"))
            title = r["title"].replace("&", "&amp;")
            items_li.append(
                f'      <li style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px dashed #e8e8e8">'
                f'<span class="news-tag" style="background:{bg};color:{color};padding:3px 10px;border-radius:4px;font-size:.8em;white-space:nowrap;flex-shrink:0">{r["category"]}</span>'
                f'<a href="articles/{r["file"]}" style="flex:1;text-decoration:none;color:#1a1a2e">{title}</a>'
                f'</li>'
            )
        groups_html.append(
            f'  <section id="d-{d}" class="date-group" data-date="{d}" style="margin-bottom:40px">\n'
            f'    <h3 style="font-size:1.3em;color:#1a1a2e;border-left:4px solid var(--brand);padding-left:12px;margin-bottom:16px">{d} <span style="color:#999;font-size:.8em;font-weight:400;margin-left:8px">{len(items)} 篇</span></h3>\n'
            f'    <ul style="list-style:none;padding:0;margin:0">\n'
            + "\n".join(items_li) + "\n"
            f'    </ul>\n'
            f'  </section>'
        )

    # 顶部锚点
    date_anchors = []
    for d in sorted_dates[:10]:
        n = len(by_date[d])
        date_anchors.append(
            f'<a href="#d-{d}" style="display:inline-block;padding:6px 12px;background:#f0f4f8;color:#1a1a2e;text-decoration:none;border-radius:6px;font-size:.9em;margin:2px">{d}<span style="color:#999;margin-left:4px">{n}</span></a>'
        )

    # 分类筛选
    cat_filters = []
    for cat, n in sorted(cat_count.items(), key=lambda x: -x[1]):
        color, bg = CAT_COLOR[cat]
        cat_filters.append(
            f'<button class="cat-filter" data-cat="{cat}" style="padding:8px 16px;background:{bg};color:{color};border:1px solid {color}33;border-radius:20px;cursor:pointer;font-size:.9em;margin:4px">{cat} ({n})</button>'
        )

    # JSON-LD ItemList (前 20 篇)
    jsonld_items = []
    for i, r in enumerate(data[:20]):
        title_escaped = r["title"].replace('"', '\\"')
        jsonld_items.append(
            f'    {{"@type": "ListItem", "position": {i+1}, "url": "https://bu6789.com/articles/{r["file"]}", "name": "{title_escaped}"}}'
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>资讯中心 | 宽幅数码印花行业干货 - 匠领数码</title>
  <meta name="description" content="匠领数码资讯中心：宽幅数码印花、分散印花、涤纶印花等 B 端加工知识 · 工厂实拍 · 采购指南 · 每天 6 篇自动更新。">
  <link rel="canonical" href="https://bu6789.com/news.html">
  <meta name="robots" content="index,follow">
  <meta property="og:title" content="资讯中心 | 匠领数码">
  <meta property="og:description" content="宽幅数码印花行业干货 · 每天 6 篇自动更新">
  <meta property="og:url" content="https://bu6789.com/news.html">
  <meta property="og:type" content="website">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E🧵%3C/text%3E%3C/svg%3E">
  <style>
    :root {{ --brand: #1a73e8; --text: #1a1a2e; --muted: #666; --bg: #fafbfc; --bg2: #f0f4f8; }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; color: var(--text); background: #fff; line-height: 1.6; }}
    nav {{ position: sticky; top: 0; background: rgba(255,255,255,.95); backdrop-filter: blur(8px); padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,.05); z-index: 100; }}
    .nav-logo {{ font-size: 1.2rem; font-weight: 700; color: var(--brand); text-decoration: none; display: flex; align-items: center; gap: 8px; }}
    .nav-logo span {{ color: var(--muted); font-size: .8rem; font-weight: 400; }}
    .nav-links {{ display: flex; gap: 24px; list-style: none; }}
    .nav-links a {{ color: var(--text); text-decoration: none; font-size: .95em; }}
    .nav-links a:hover {{ color: var(--brand); }}
    .nav-cta {{ background: var(--brand); color: #fff !important; padding: 8px 16px; border-radius: 6px; }}
    .container {{ max-width: 960px; margin: 0 auto; padding: 0 20px; }}
    .page-header {{ text-align: center; padding: 60px 20px 40px; background: linear-gradient(135deg, #e8f0fe 0%, #f0f4f8 100%); border-radius: 0 0 24px 24px; }}
    .page-header h1 {{ font-size: 2.2em; margin-bottom: 12px; color: var(--text); }}
    .page-header p {{ color: var(--muted); font-size: 1.05em; }}
    .stats-bar {{ display: flex; justify-content: center; gap: 40px; margin-top: 24px; flex-wrap: wrap; }}
    .stat-item .num {{ font-size: 1.6em; font-weight: 700; color: var(--brand); text-align: center; }}
    .stat-item .label {{ color: var(--muted); font-size: .85em; text-align: center; }}
    .cat-filter-row {{ display: flex; flex-wrap: wrap; gap: 4px; margin: 24px 0; padding: 16px; background: var(--bg); border-radius: 12px; }}
    .cat-filter.active {{ background: var(--brand) !important; color: #fff !important; }}
    .anchor-bar {{ position: sticky; top: 65px; background: rgba(255,255,255,.95); padding: 12px 0; z-index: 99; border-bottom: 1px solid #eee; margin-bottom: 24px; text-align: center; }}
    .anchor-bar a:hover {{ background: var(--brand); color: #fff !important; }}
    .date-group {{ scroll-margin-top: 140px; }}
    .news-tag {{ display: inline-block; padding: 3px 10px; border-radius: 4px; font-size: .8em; white-space: nowrap; }}
    footer {{ background: #1a1a2e; color: #999; padding: 40px 20px; text-align: center; margin-top: 80px; }}
    footer a {{ color: #fff; text-decoration: none; margin: 0 8px; }}
  </style>
</head>
<body>

<nav>
  <a class="nav-logo" href="/">🧵 匠领数码 <span>J.LINK TEXTILE</span></a>
  <ul class="nav-links">
    <li><a href="/#products">产品中心</a></li>
    <li><a href="/#about">关于我们</a></li>
    <li><a href="news.html" style="color:var(--brand);font-weight:600">资讯中心</a></li>
    <li><a href="/#faq">常见问题</a></li>
    <li><a href="/#contact" class="nav-cta">立即咨询</a></li>
  </ul>
</nav>

<header class="page-header">
  <h1>📰 资讯中心</h1>
  <p>宽幅数码印花行业干货 · 每天 6 篇自动更新</p>
  <div class="stats-bar">
    <div class="stat-item"><div class="num">{total}</div><div class="label">文章总数</div></div>
    <div class="stat-item"><div class="num">{len(by_date)}</div><div class="label">更新天数</div></div>
    <div class="stat-item"><div class="num">{cat_count.get("应用案例", 0)}</div><div class="label">应用案例</div></div>
    <div class="stat-item"><div class="num">{cat_count.get("采购指南", 0)}</div><div class="label">采购指南</div></div>
  </div>
</header>

<div class="container">

  <div class="cat-filter-row" id="catFilterRow">
    <span style="margin:8px 8px 0 0;color:#666">筛选：</span>
    <button class="cat-filter active" data-cat="all" style="padding:8px 16px;background:#1a73e8;color:#fff;border:none;border-radius:20px;cursor:pointer;font-size:.9em;margin:4px">全部 ({total})</button>
    {chr(10).join(cat_filters)}
  </div>

  <div class="anchor-bar">
    <span style="margin-right:12px;color:#999;font-size:.85em">快速跳转：</span>
    {chr(10).join(date_anchors)}
    <a href="#bottom" style="display:inline-block;padding:6px 12px;background:#f0f4f8;color:#1a1a2e;text-decoration:none;border-radius:6px;font-size:.9em;margin:2px">↑ 顶部</a>
  </div>

  <div id="articleList">
{chr(10).join(groups_html)}
  </div>

  <p id="bottom" style="text-align:center;color:#999;padding:40px 0;border-top:1px solid #eee;margin-top:40px">
    — 已是全部 {total} 篇文章 —<br>
    <a href="/" style="display:inline-block;margin-top:16px;padding:10px 24px;background:var(--brand);color:#fff;text-decoration:none;border-radius:6px">← 返回首页</a>
  </p>

</div>

<footer>
  <p><strong style="color:#fff">匠领数码 · J.LINK TEXTILE</strong></p>
  <p>浙江省绍兴市柯桥区齐贤镇兴浦路88号盛超针纺园区二幢南面五楼</p>
  <p>📞 张先生 17769886009</p>
  <p style="margin-top:16px;font-size:.85em">© 2026 匠领数码 · 主营 200-320CM 宽幅数码印花 · 分散印花 · 涤纶印花 · 1米起印</p>
</footer>

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
{{
  "@context": "https://schema.org",
  "@type": "ItemList",
  "name": "匠领数码资讯中心",
  "description": "宽幅数码印花行业干货 · 每天自动更新",
  "numberOfItems": {total},
  "itemListElement": [
{",".join(jsonld_items)}
  ]
}}
</script>

</body>
</html>"""


def update_index_news(data: list) -> int:
    """同步首页 news 区块为最新 10 篇。返回是否实际改动。"""
    if not INDEX_HTML.exists():
        return 0
    content = INDEX_HTML.read_text(encoding="utf-8")
    top10 = data[:10]
    items_html = []
    for r in top10:
        color, bg = CAT_COLOR.get(r["category"], ("#666", "#eee"))
        title = r["title"].replace("&", "&amp;").replace('"', "&quot;")
        items_html.append(
            f'        <li><span class="news-tag" style="background:{bg};color:{color}">{r["category"]}</span> '
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
    NEWS_HTML.write_text(build_news_html(data), encoding="utf-8")
    idx_changed = update_index_news(data)
    sm_changed = update_sitemap(data)
    print(f"OK: {len(data)} 篇 → news.html | 首页{'已' if idx_changed else '无变化'} | sitemap{'已' if sm_changed else '无变化'}")


if __name__ == "__main__":
    main()
