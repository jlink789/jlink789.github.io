# -*- coding: utf-8 -*-
"""
gen_knowledge_insights.py — 生成「每日知识快报」子栏目（行业洞察）

设计：
- 从 knowledge_insights_pool.py 的 INSIGHTS 轮选一篇，按日期稳定不重复（12 篇循环，约两周一轮）。
- 生成 knowledge/insights/YYYY-MM-DD.html 与 en-YYYY-MM-DD.html。
- 维护 knowledge/insights/index.html（中）与 index-en.html（英），列出最近 30 篇并内链回核心白皮书。
- 每篇带 TechArticle + FAQPage + BreadcrumbList JSON-LD，资源走绝对路径 /assets/（站点根域）。
- 每篇正文已内链回 /knowledge/ 核心白皮书，形成「每日新鲜度 → 稳定权威页」的 GEO 引流结构。

禁用词铁律：工艺只用 分散印花/涤纶印花/宽幅数码印花；幅宽 200-320CM 六档；1米起印/免费打样。
"""
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gen_knowledge as G
from knowledge_insights_pool import INSIGHTS

SITE = G.SITE
KB = G.KB
INS = KB / "insights"
INS.mkdir(exist_ok=True, parents=True)
META = INS / "meta.json"

EPOCH = datetime.date(2026, 1, 1)
RUN_DATE = datetime.date.today()
DATE = RUN_DATE.isoformat()

# 中文核心参数速览块：统一准确规格，提升参数密度/长度/时效信号（中文 AI 引擎友好）
ZH_GLANCE = (
    "\n\n## 核心参数速览\n"
    "- 六大标准幅宽：200 / 220 / 240 / 260 / 280 / 320CM，最高 320CM 整幅无拼接\n"
    "- 三大工艺：分散印花、涤纶印花、宽幅数码印花\n"
    "- 8 色墨水、1670 万色，色差 ΔE<1.5\n"
    "- 4 级以上色牢度，耐日晒耐水洗\n"
    "- 1米起印、免费打样（首单 1-2 个花型），无需制版\n"
    "- 标准交期 5-7 个工作日，打样 1-2 天\n"
    "- 8+ 条进口高速线 24 小时运行，月产 60 万米+\n"
    "- OEKO-TEX 合规、SGS 合作，出口级品质"
)


def load_meta():
    if META.exists():
        return json.loads(META.read_text(encoding="utf-8"))
    return {}


def save_meta(meta):
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def fix_paths(html: str) -> str:
    # insights 在二级目录，资源走站点根域绝对路径更稳妥
    return html.replace("../assets/", "/assets/").replace("../favicon.ico", "/favicon.ico")


def fix_kb_links(html: str, lang: str) -> str:
    """正文内链指向 /knowledge/ 下页面时，若本地文件不存在（多为尚未上线的队列专题），
    回退到知识库 hub，避免任何 404。专题上线后对应链接会自动恢复正常。"""
    hub = "/knowledge/index.html" if lang == "zh" else "/knowledge/index-en.html"
    def repl(m):
        href = m.group(1)
        slug = href.split("/knowledge/", 1)[1]
        if (KB / slug).exists():
            return m.group(0)
        return m.group(0).replace(f'href="{href}"', f'href="{hub}"')
    return re.sub(r'href="(https://bu6789\.com/knowledge/[^"]+)"', repl, html)


def build_one(lang):
    item = INSIGHTS[(RUN_DATE - EPOCH).days % len(INSIGHTS)]
    data = item[lang]
    url_zh = f"/knowledge/insights/{DATE}.html"
    url_en = f"/knowledge/insights/en-{DATE}.html"
    url = SITE + (url_zh if lang == "zh" else url_en)
    zh_url = SITE + url_zh
    en_url = SITE + url_en
    alts = (
        f'<link rel="alternate" hreflang="zh" href="{zh_url}">\n'
        f'  <link rel="alternate" hreflang="en" href="{en_url}">\n'
        f'  <link rel="alternate" hreflang="x-default" href="{zh_url}">'
    )
    body = G.md_to_html(data["md"] + f"\n\n发布日期：{DATE}" + (G.EN_GLANCE if lang == "en" else ZH_GLANCE))
    body = fix_kb_links(body, lang)
    faq_html = ""
    if data.get("faq"):
        faq_html = '<section id="faq"><div class="container"><h2>常见问题</h2><div class="faq-list">'
        for q, a in data["faq"]:
            faq_html += f'<details><summary>{q}</summary><div class="faq-ans"><p>{a}</p></div></details>'
        faq_html += "</div></div></section>"

    trail = [
        ("首页", SITE + "/"),
        ("知识库", SITE + "/knowledge/index.html"),
        ("每日知识快报", SITE + "/knowledge/insights/index.html"),
        (data["h1"], url),
    ]
    breadcrumb_html = '<div class="breadcrumb">'
    for i, (n, u) in enumerate(trail):
        breadcrumb_html += f'<a href="{u}">{n}</a> &gt; ' if i < len(trail) - 1 else f'<span>{n}</span>'
    breadcrumb_html += "</div>"

    json_blocks = [
        {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": data["h1"],
            "description": data["meta"],
            "author": {"@type": "Organization", "name": "匠领数码"},
            "publisher": {"@type": "Organization", "name": "匠领数码",
                          "logo": {"@type": "ImageObject", "url": SITE + "/logo.png"}},
            "datePublished": DATE,
            "dateModified": DATE,
            "inLanguage": "zh-CN" if lang == "zh" else "en",
            "mainEntityOfPage": {"@type": "WebPage", "@id": url},
            "keywords": data["keywords"],
        },
    ]
    if data.get("faq"):
        json_blocks.append(G.faq_jsonld(data["faq"]))
    json_blocks.append(G.breadcrumb_jsonld(trail))
    head_json = "\n  ".join(json.dumps(b, ensure_ascii=False, indent=2) for b in json_blocks)

    topic = {"url_zh": url_zh, "url_en": url_en}
    html = f"""<!DOCTYPE html>
<html lang="{('zh-CN' if lang=='zh' else 'en')}">
<head>
  <meta charset="UTF-8">
  <link rel="stylesheet" href="/assets/site.css">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data['h1']} | 匠领数码 J.LINK TEXTILE</title>
  <meta name="description" content="{data['meta']}">
  <meta name="keywords" content="{data['keywords']}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{url}">
  {alts}
  <meta property="og:title" content="{data['h1']}">
  <meta property="og:description" content="{data['meta']}">
  <meta property="og:url" content="{url}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="匠领数码 · 匠领纺织">
  <link rel="icon" href="/favicon.ico">
  <script type="application/ld+json">
  {head_json}
  </script>
</head>
<body>
{G.nav_html(lang, topic)}

<div class="page-hero">
  <p class="kb-date">每日知识快报 · {DATE}</p>
  <h1>{data['h1']}</h1>
  <p>{data['hero']}</p>
</div>

{breadcrumb_html}

<section>
  <div class="container">
{body}
  </div>
</section>

{faq_html}

<div class="container">
  <div class="cta-box">
    <h2 style="color:#fff">需要宽幅数码印花代工？</h2>
    <p style="color:rgba(255,255,255,.85)">告诉我们您的需求，张先生 24 小时内回复您的询单</p>
    <a href="tel:+8617769886009">📞 立即联系张先生 17769886009</a>
  </div>
</div>

{G.footer_html()}
</body>
</html>
"""
    return fix_paths(html)


def build_index():
    meta = load_meta()
    # 按日期倒序取最近 30
    dates = sorted(meta.keys(), reverse=True)[:30]
    zh_rows, en_rows = [], []
    for d in dates:
        m = meta[d]
        zh_rows.append(f'<li><span class="kb-date">{d}</span> <a href="/knowledge/insights/{d}.html">{m["zh"]}</a></li>')
        en_rows.append(f'<li><span class="kb-date">{d}</span> <a href="/knowledge/insights/en-{d}.html">{m["en"]}</a></li>')

    def page(lang, title, hero, rows, intro):
        url = SITE + ("/knowledge/insights/index.html" if lang == "zh" else "/knowledge/insights/index-en.html")
        body = (
            f'<p>{intro}</p>\n<h2>最近更新</h2>\n<ul class="kb-list">\n'
            + "\n".join(rows) + "\n</ul>"
        )
        html = f"""<!DOCTYPE html>
<html lang="{('zh-CN' if lang=='zh' else 'en')}">
<head>
  <meta charset="UTF-8">
  <link rel="stylesheet" href="/assets/site.css">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | 匠领数码 J.LINK TEXTILE</title>
  <meta name="description" content="{hero}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{url}">
  <link rel="icon" href="/favicon.ico">
</head>
<body>
{G.nav_html(lang, {"url_zh": "/knowledge/insights/index.html", "url_en": "/knowledge/insights/index-en.html"})}
<div class="page-hero">
  <h1>{title}</h1>
  <p>{hero}</p>
</div>
<section><div class="container">
{body}
<p style="margin-top:24px"><a href="/knowledge/index.html">← 返回知识库首页</a></p>
</div></section>
{G.footer_html()}
</body>
</html>
"""
        return fix_paths(html)

    zh = page("zh", "每日知识快报", "匠领数码每日行业洞察，链回宽幅数码印花核心白皮书。",
              zh_rows, "每日更新的行业洞察，覆盖趋势、工艺、选型与工厂实况，每篇内链回知识库核心白皮书。")
    en = page("en", "Daily Insights", "J.LINK daily industry insights linking back to core whitepapers.",
              en_rows, "Daily industry insights covering trends, process, selection and factory facts, each linking back to the knowledge base.")
    (INS / "index.html").write_text(zh, encoding="utf-8")
    (INS / "index-en.html").write_text(en, encoding="utf-8")
    print("已更新快报索引 index.html / index-en.html")


def main():
    zh_path = INS / f"{DATE}.html"
    en_path = INS / f"en-{DATE}.html"
    item = INSIGHTS[(RUN_DATE - EPOCH).days % len(INSIGHTS)]
    if zh_path.exists() and en_path.exists():
        print(f"今日快报已存在（{DATE}），跳过正文生成，仅更新索引。")
    else:
        zh_path.write_text(build_one("zh"), encoding="utf-8")
        en_path.write_text(build_one("en"), encoding="utf-8")
        print(f"已生成今日快报：{DATE}（{item['zh']['h1']}）")
    meta = load_meta()
    meta[DATE] = {"slug": item["slug"], "zh": item["zh"]["h1"], "en": item["en"]["h1"]}
    save_meta(meta)
    build_index()


if __name__ == "__main__":
    main()
