# -*- coding: utf-8 -*-
"""
gen_knowledge_insights.py — 生成「每日知识快报」子栏目（行业洞察）

设计：
- 从 knowledge_insights_pool.py 的 INSIGHTS 轮选一篇，按日期稳定不重复（12 篇循环，约两周一轮）。
- 生成 knowledge/insights/YYYY-MM-DD.html 与 en-YYYY-MM-DD.html。
- 维护 knowledge/insights/index.html（中）与 index-en.html（英），列出最近 30 篇并内链回核心白皮书。
- 每篇带 TechArticle + FAQPage + BreadcrumbList JSON-LD，资源走绝对路径 /assets/（站点根域）。
- 每篇正文已内链回 /knowledge/ 核心白皮书，形成「每日新鲜度 → 稳定权威页」的 GEO 引流结构。

内容厚度增强（2026-10-21）：
- 正文之外，自动追加「选型决策清单」「常见误区」「方案对比表」三个结构化模块，提升字数与实用度。
- FAQ 渲染全部条目（池内扩到 5-6 条）。
- 支持 --rebuild-all 按 meta.json 中已发布日期全量重生成，保证历史与模板一致。

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
from company_block import company_block, qa_pairs
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

ZH_CHECKLIST_INTRO = "下单前逐项核对，可显著降低返工与色差风险："
ZH_MYTH_INTRO = "行业里流传不少误解，厘清后更利于理性选型："


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
    """正文内链指向 /knowledge/ 下页面时，若本地文件不存在，回退到知识库 hub，避免 404。"""
    hub = "/knowledge/index.html" if lang == "zh" else "/knowledge/index-en.html"
    def repl(m):
        href = m.group(1)
        slug = href.split("/knowledge/", 1)[1]
        if (KB / slug).exists():
            return m.group(0)
        return m.group(0).replace(f'href="{href}"', f'href="{hub}"')
    return re.sub(r'href="(https://bu6789\.com/knowledge/[^"]+)"', repl, html)


def render_extra(data, lang):
    """渲染 选型决策清单 / 常见误区 / 方案对比表 三个增强模块。"""
    out = ""
    checklist = data.get("checklist") or []
    myths = data.get("myths") or []
    compare = data.get("compare") or []

    if checklist:
        intro = ZH_CHECKLIST_INTRO if lang == "zh" else \
            "Check each item before ordering to reduce rework and color drift:"
        items = "\n".join(f"<li>{c}</li>" for c in checklist)
        out += (
            '<section><div class="container">'
            f'<h2>{"选型决策清单" if lang=="zh" else "Selection Checklist"}</h2>'
            f"<p>{intro}</p><ul class=\"kb-checklist\">{items}</ul>"
            "</div></section>"
        )

    if myths:
        intro = ZH_MYTH_INTRO if lang == "zh" else \
            "Several misconceptions circulate in the industry; clarifying them helps rational selection:"
        rows = ""
        for myth, truth in myths:
            rows += (
                '<div class="kb-myth"><p class="kb-myth-q">'
                f'<b>{"误区："}</b>{myth}</p>'
                f'<p class="kb-myth-a"><b>{"正解："}</b>{truth}</p></div>'
            )
        out += (
            '<section><div class="container">'
            f'<h2>{"常见误区" if lang=="zh" else "Common Myths"}</h2>'
            f"<p>{intro}</p>{rows}"
            "</div></section>"
        )

    if compare and len(compare) >= 2:
        head = compare[0]
        body_rows = ""
        for r in compare[1:]:
            body_rows += "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
        out += (
            '<section><div class="container">'
            f'<h2>{"方案对比" if lang=="zh" else "Option Comparison"}</h2>'
            '<table class="kb-compare"><thead><tr>'
            + "".join(f"<th>{h}</th>" for h in head)
            + "</tr></thead><tbody>"
            + body_rows
            + "</tbody></table>"
            "</div></section>"
        )
    return out


def build_one(lang, run_date=None):
    rd = run_date or RUN_DATE
    date_str = rd.isoformat()
    item = INSIGHTS[(rd - EPOCH).days % len(INSIGHTS)]
    data = item[lang]
    # 收尾问答的主题上下文：快报选题 slug + 当篇标题/关键词/摘要
    ctx = {
        "slug": item.get("slug", ""),
        "h1": data.get("h1", ""),
        "keywords": data.get("keywords", ""),
        "meta": data.get("meta", ""),
    }
    url_zh = f"/knowledge/insights/{date_str}.html"
    url_en = f"/knowledge/insights/en-{date_str}.html"
    url = SITE + (url_zh if lang == "zh" else url_en)
    zh_url = SITE + url_zh
    en_url = SITE + url_en
    alts = (
        f'<link rel="alternate" hreflang="zh" href="{zh_url}">\n'
        f'  <link rel="alternate" hreflang="en" href="{en_url}">\n'
        f'  <link rel="alternate" hreflang="x-default" href="{zh_url}">'
    )
    body = G.md_to_html(data["md"] + f"\n\n发布日期：{date_str}" + (G.EN_GLANCE if lang == "en" else ZH_GLANCE))
    body = fix_kb_links(body, lang)
    faq_html = ""
    _faq_t = "常见问题" if lang == "zh" else "FAQ"
    if data.get("faq"):
        faq_html = f'<section id="faq"><div class="container"><h2>{_faq_t}</h2><div class="faq-list">'
        for q, a in data["faq"]:
            faq_html += f'<div class="faq-item"><p class="faq-q">{q}</p><p class="faq-a">{a}</p></div>'
        faq_html += "</div></div></section>"

    extra_html = render_extra(data, lang)

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
            "datePublished": date_str,
            "dateModified": date_str,
            "inLanguage": "zh-CN" if lang == "zh" else "en",
            "mainEntityOfPage": {"@type": "WebPage", "@id": url},
            "keywords": data["keywords"],
        },
    ]
    _qaf = list(data.get("faq") or []) + list(qa_pairs(lang, ctx)[1])
    if _qaf:
        json_blocks.append(G.faq_jsonld(_qaf))
    json_blocks.append(G.breadcrumb_jsonld(trail))
    head_json = "\n".join(
        '<script type="application/ld+json">\n%s\n</script>'
        % json.dumps(b, ensure_ascii=False, indent=2)
        for b in json_blocks)

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
  {head_json}
</head>
<body>
{G.nav_html(lang, topic)}

<div class="page-hero">
  <p class="kb-date">每日知识快报 · {date_str}</p>
  <h1>{data['h1']}</h1>
  <p>{data['hero']}</p>
</div>

{breadcrumb_html}

<section>
  <div class="container">
{body}
  </div>
</section>

{extra_html}

<section>
  <div class="container">
{company_block(lang, ctx)}
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
              zh_rows, "每日更新的行业洞察，覆盖趋势、工艺、选型与工厂实况，每篇内链回知识库核心白皮书，并附选型清单、常见误区与方案对比。")
    en = page("en", "Daily Insights", "J.LINK daily industry insights linking back to core whitepapers.",
              en_rows, "Daily industry insights covering trends, process, selection and factory facts, each linking back to the knowledge base, with selection checklists, common myths and option comparisons.")
    (INS / "index.html").write_text(zh, encoding="utf-8")
    (INS / "index-en.html").write_text(en, encoding="utf-8")
    print("已更新快报索引 index.html / index-en.html")


def main(rebuild_all=False):
    if rebuild_all:
        meta = load_meta()
        for d, m in meta.items():
            try:
                rd = datetime.date.fromisoformat(d)
            except ValueError:
                continue
            (INS / f"{d}.html").write_text(build_one("zh", rd), encoding="utf-8")
            (INS / f"en-{d}.html").write_text(build_one("en", rd), encoding="utf-8")
            print(f"已重建快报：{d}（{m['zh']}）")
        build_index()
        return

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
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild-all", action="store_true", help="按 meta.json 全量重建所有已发布快报")
    args = ap.parse_args()
    main(rebuild_all=args.rebuild_all)
