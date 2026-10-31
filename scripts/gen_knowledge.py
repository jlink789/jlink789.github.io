#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_knowledge.py — 生成 /knowledge/ 知识库白皮书栏目（中英双语，10 专题 + 中英文 hub 首页）

每个专题页 = 白皮书式独立页：
- 外链 assets/site.css（全站统一设计系统）
- H1 问句 + 首段直接答案 + H2 分段 + 参数表 + 列表 + 相关阅读
- JSON-LD：TechArticle + FAQPage + BreadcrumbList
- canonical + hreflang（zh / en / x-default→zh）
- 遵守禁用词铁律（工艺用 分散印花/涤纶印花/宽幅数码印花；幅宽 200-320CM 六档；1米起印；不出现旧规格禁用词）

用法：
    python scripts/gen_knowledge.py            # 生成全部页面
    python scripts/gen_knowledge.py --check    # 额外用 geo_content_scorer 跑分（仅本地）
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from company_block import company_block, company_jsonld  # noqa: E402
KB = ROOT / "knowledge"
KB.mkdir(exist_ok=True)
TODAY = "2026-10-17"
SITE = "https://bu6789.com"

SCORER = r"C:\Users\Administrator\.workbuddy\skills\geo-print-factory\scripts\geo_content_scorer.py"
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"

# 英文页共享「核心参数速览」块：统一准确规格，提升参数密度/长度/时效信号（英文 AI 引擎友好）
# 严禁词自检：仅用 320CM / 1-meter minimum / disperse·polyester·wide-format，不出现旧规格禁用词
EN_GLANCE = (
    "\n\n## At a Glance\n"
    "- Six standard widths: 200 / 220 / 240 / 260 / 280 / 320CM, up to 320CM seamless in one piece\n"
    "- Three processes: disperse dye printing, polyester printing and wide-format digital printing\n"
    "- 8 color inks, 16.7M colors, color difference ΔE under 1.5\n"
    "- Grade 4+ color fastness, sun-resistant and wash-resistant\n"
    "- 1-meter minimum, free sampling (1-2 designs on first order), screen-free\n"
    "- 5-7 working days standard lead time, 1-2 days for sampling\n"
    "- 8+ imported high-speed lines running 24 hours, 600k+ meters monthly capacity\n"
    "- Oeko-Tex compliant, SGS cooperation, export-grade; last updated: " + TODAY
)

def page_md(lang, data):
    """返回用于渲染与评分的 markdown（英文追加共享规格块）。"""
    md = data["md"]
    if lang == "en":
        md = md + EN_GLANCE
    return md

# ───────────────────────── Markdown → HTML（受控子集） ─────────────────────────
def _inline(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    def _link(m):
        text, url = m.group(1), m.group(2)
        blank = ' target="_blank" rel="noopener"' if url.startswith("http") else ""
        return f'<a href="{url}"{blank}>{text}</a>'
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+|/[^)]*|#[^)]*)\)", _link, s)
    return s

def md_to_html(md: str) -> str:
    lines = md.split("\n")
    out = []
    in_list = False
    in_table = False
    i = 0
    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>"); in_list = False
    def close_table():
        nonlocal in_table
        if in_table:
            out.append("</tbody></table>"); in_table = False
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            close_list(); close_table(); i += 1; continue
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            sep = all(set(c) <= set("-: ") for c in cells)
            if sep:
                i += 1; continue
            if not in_table:
                out.append('<table class="tech-table"><thead><tr>' +
                           "".join(f"<th>{_inline(c)}</th>" for c in cells) +
                           "</tr></thead><tbody>")
                in_table = True
            else:
                out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>")
            i += 1; continue
        if s.startswith("# "):
            close_list(); close_table(); out.append(f"<h1>{_inline(s[2:])}</h1>"); i += 1; continue
        if s.startswith("## "):
            close_list(); close_table(); out.append(f"<h2>{_inline(s[3:])}</h2>"); i += 1; continue
        if s.startswith("### "):
            close_list(); close_table(); out.append(f"<h3>{_inline(s[4:])}</h3>"); i += 1; continue
        if s.startswith("- ") or s.startswith("* "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{_inline(s[2:])}</li>"); i += 1; continue
        if s.startswith("> "):
            close_list(); close_table(); out.append(f"<blockquote>{_inline(s[2:])}</blockquote>"); i += 1; continue
        close_list(); close_table()
        out.append(f"<p>{_inline(s)}</p>"); i += 1
    close_list(); close_table()
    return "\n".join(out)

# ───────────────────────── 导航 / 页脚（知识库在子目录，资源用 ../） ─────────────────────────
def nav_html(lang: str, topic: dict) -> str:
    if lang == "zh":
        links = [("/", "首页"), ("/#products", "产品中心"), ("/about.html", "关于我们"),
                 ("/news.html", "资讯中心"), ("/knowledge/index.html", "知识库"), ("/#faq", "常见问题")]
        app = ('<li><a href="https://app.bu6789.com:8443/#/books" target="_blank" rel="noopener" class="nav-app">电子画册</a></li>\n'
               '        <li><a href="https://app.bu6789.com:8443" target="_blank" rel="noopener" class="nav-app">图库找图</a></li>')
        cta = '<li><a href="/#contact" class="nav-cta">立即咨询</a></li>'
        en_link = f'<li><a href="{topic["url_en"]}" class="lang-switch">EN</a></li>'
    else:
        links = [("/en.html", "Home"), ("/en.html#products", "Products"), ("/en-about.html", "About"),
                 ("/en-news.html", "News"), ("/knowledge/index-en.html", "Knowledge"), ("/en.html#faq", "FAQ")]
        app = ('<li><a href="https://app.bu6789.com:8443/#/books" target="_blank" rel="noopener" class="nav-app">Catalog</a></li>\n'
               '        <li><a href="https://app.bu6789.com:8443" target="_blank" rel="noopener" class="nav-app">Image Search</a></li>')
        cta = '<li><a href="/en.html#contact" class="nav-cta">Contact</a></li>'
        en_link = f'<li><a href="{topic["url_zh"]}" class="lang-switch">中文</a></li>'
    li = "".join(f'<li><a href="{h}">{t}</a></li>\n        ' for h, t in links)
    return (
        '<nav>\n'
        '  <a class="nav-logo" href="/"><img class="nav-logo-mark" src="../assets/logo-mark-white.png" '
        'alt="匠领纺织 J.LINK TEXTILE" width="38" height="38">'
        '<span class="nav-logo-stack"><b>匠领数码</b><i>J.LINK TEXTILE · 匠领纺织</i></span></a>\n'
        '  <ul class="nav-links">\n    ' + li + app + "\n        " + cta + "\n      " + en_link + "\n  </ul>\n</nav>"
    )

def footer_html() -> str:
    return (
        '<footer><img class="footer-logo" src="../assets/logo-white.png" '
        'alt="匠领纺织 J.LINK TEXTILE · 匠领数码" loading="lazy">\n  <p>\n'
        '    <strong>匠领数码 · 匠领纺织 J.LINK TEXTILE</strong> · 浙江省绍兴市柯桥区 · 专注宽幅数码印花加工<br>\n'
        '    联系人：张先生 17769886009 · 工作时间：周一至周六 08:00-18:00<br><br>\n'
        '    &copy; 2026 匠领数码 版权所有 · 宽幅数码印花加工专家\n'
        '   | <a href="https://beian.miit.gov.cn" target="_blank" rel="noopener">浙ICP备20007773号-3</a></p>\n'
        '  <script src="/seo-push.js"></script>\n</footer>'
    )

# ───────────────────────── JSON-LD ─────────────────────────
def faq_jsonld(faq):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faq
        ],
    }

def article_jsonld(lang, data, url):
    return {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": data["h1"],
        "description": data["meta"],
        "author": {"@type": "Organization", "name": "匠领数码"},
        "publisher": {
            "@type": "Organization", "name": "匠领数码",
            "logo": {"@type": "ImageObject", "url": SITE + "/logo.png"},
        },
        "datePublished": TODAY,
        "dateModified": TODAY,
        "inLanguage": "zh-CN" if lang == "zh" else "en",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "keywords": data["keywords"],
    }

def breadcrumb_jsonld(trail):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u}
            for i, (n, u) in enumerate(trail)
        ],
    }

def build_page(lang, topic, is_hub=False):
    data = topic["zh"] if lang == "zh" else topic["en"]
    url = SITE + (topic["url_zh"] if lang == "zh" else topic["url_en"])
    zh_url = SITE + topic["url_zh"]
    en_url = SITE + topic["url_en"]
    alts = (
        f'<link rel="alternate" hreflang="zh" href="{zh_url}">\n'
        f'  <link rel="alternate" hreflang="en" href="{en_url}">\n'
        f'  <link rel="alternate" hreflang="x-default" href="{zh_url}">'
    )
    body = md_to_html(page_md(lang, data))
    faq_html = ""
    if data.get("faq"):
        faq_html = '<section id="faq"><div class="container"><h2>常见问题</h2><div class="faq-list">'
        for q, a in data["faq"]:
            faq_html += f'<details><summary>{q}</summary><div class="faq-ans"><p>{a}</p></div></details>'
        faq_html += "</div></div></section>"

    if is_hub:
        breadcrumb = [("首页", SITE + "/"), ("知识库", url)]
    else:
        breadcrumb = [("首页", SITE + "/"), ("知识库", SITE + "/knowledge/index.html"), (data["h1"], url)]

    json_blocks = []
    if is_hub:
        json_blocks.append({
            "@context": "https://schema.org", "@type": "WebPage",
            "name": data["h1"], "description": data["meta"],
            "url": url, "inLanguage": "zh-CN" if lang == "zh" else "en",
        })
    else:
        json_blocks.append(article_jsonld(lang, data, url))
        if data.get("faq"):
            json_blocks.append(faq_jsonld(data["faq"]))
    json_blocks.append(breadcrumb_jsonld(breadcrumb))
    json_blocks.append(json.loads(company_jsonld()))
    head_json = "\n  ".join(json.dumps(b, ensure_ascii=False, indent=2) for b in json_blocks)

    breadcrumb_html = '<div class="breadcrumb">'
    for i, (n, u) in enumerate(breadcrumb):
        if i < len(breadcrumb) - 1:
            breadcrumb_html += f'<a href="{u}">{n}</a> &gt; '
        else:
            breadcrumb_html += f'<span>{n}</span>'
    breadcrumb_html += "</div>"

    html = f"""<!DOCTYPE html>
<html lang="{('zh-CN' if lang=='zh' else 'en')}">
<head>
  <meta charset="UTF-8">
  <link rel="stylesheet" href="../assets/site.css">
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
  <link rel="icon" href="../favicon.ico">
  <script type="application/ld+json">
  {head_json}
  </script>
</head>
<body>
{nav_html(lang, topic)}

<div class="page-hero">
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

{company_block(lang)}

<div class="container">
  <div class="cta-box">
    <h2 style="color:#fff">需要宽幅数码印花代工？</h2>
    <p style="color:rgba(255,255,255,.85)">告诉我们您的需求，张先生 24 小时内回复您的询单</p>
    <a href="tel:+8617769886009">📞 立即联系张先生 17769886009</a>
  </div>
</div>

{footer_html()}
</body>
</html>
"""
    return html

# ───────────────────────── 内容数据（10 专题 × 中英双语） ─────────────────────────
T = []

# 1 宽幅数码印花是什么
T.append({
  "slug": "wide-format-digital-printing",
  "url_zh": "/knowledge/wide-format-digital-printing.html",
  "url_en": "/knowledge/en-wide-format-digital-printing.html",
  "zh": {
    "h1": "宽幅数码印花是什么？定义、工艺与 200-320CM 幅宽全解",
    "hero": "宽幅数码印花是无需制版、在 200-320CM 整幅面料上直接喷印图案的印花方式，适合窗帘、墙布、家纺等大幅面软装定制。",
    "meta": "宽幅数码印花定义与工作原理：200-320CM 六大标准幅宽、分散印花/涤纶印花/宽幅数码印花三大工艺、1米起印、5-7天交货，适合窗帘墙布家纺定制。",
    "keywords": "宽幅数码印花,宽幅印花,数码印花,200CM数码印花,320CM数码印花,柯桥数码印花,窗帘印花,墙布印花",
    "md": """宽幅数码印花是采用工业级数码喷印技术、在 200-320CM 整幅面料上直接喷印数字图案的印花方式，无需制版，适合窗帘、墙布、家纺等大幅面软装产品的个性化与小批量生产。它的最大特征是「整幅无拼接」——避免了对花错位与拼缝瑕疵。

## 什么是宽幅数码印花
宽幅数码印花指使用工业级数码印花设备，将数字图案直接喷印到幅宽 200CM 至 320CM 的整幅面料上。与窄幅设备（通常≤180CM）相比，宽幅设备能实现窗帘、墙布等产品的整幅连续印花。匠领数码的宽幅产线覆盖 200/220/240/260/280/320CM 六大标准幅宽，最高 320CM。

## 核心参数
| 项目 | 参数 |
| --- | --- |
| 加工幅宽 | 200/220/240/260/280/320CM（六大标准） |
| 印花工艺 | 分散印花 / 涤纶印花 / 宽幅数码印花 |
| 最小起印 | 1米起印、免费打样 |
| 标准交期 | 5-7 个工作日 |
| 色彩精度 | 8 色墨水、1670 万色、ΔE<1.5 |
| 色牢度 | 4 级以上 |

## 工作原理
宽幅数码印花采用喷头阵列将水性或分散墨水按数字图案逐行喷印到面料，经蒸化、水洗、定型后固色。整个过程由 ICC 色彩管理统一控制，来样复原度高。根据面料成分选择工艺：涤纶与化纤用分散印花，家纺混纺用涤纶印花，整幅大面幅用宽幅数码印花。

## 适用场景
- 整幅窗帘、遮光帘、纱帘的无拼接印花
- 墙布、无缝壁画的大幅面连续印花
- 床品、抱枕、桌布等家纺个性化定制
- 酒店工程、样板间、跨境电商的小批量快反

## 与传统印花对比
传统圆网或平网印花需要制版，起订量高、交期长，适合大批量单一花型；宽幅数码印花无需制版，1米起印，5-7天交货，更适合多花型、小批量、快反订单。根据订单结构选择：大批量稳单走传统，多花型快反走数码。

## 相关阅读
- [窗帘数码印花加工详解](https://bu6789.com/knowledge/curtain-digital-printing.html)
- [320CM 宽幅数码印花能力](https://bu6789.com/knowledge/320cm-wide-format-printing.html)
- [如何选择数码印花工厂](https://bu6789.com/knowledge/how-to-choose-printing-factory.html)

总结：宽幅数码印花以整幅无拼接、1米起印、快反交付，成为窗帘墙布家纺软装定制的主流工艺，选型时按幅宽、面料、起订量匹配工艺即可。""",
    "faq": [
      ("宽幅数码印花最大能做多宽？", "匠领数码宽幅产线覆盖 200/220/240/260/280/320CM 六大标准幅宽，最高 320CM，整幅无拼接，适合窗帘、墙布等大面幅产品。"),
      ("宽幅数码印花需要制版吗？", "不需要制版。宽幅数码印花是数码直喷工艺，按数字文件喷印，因此 1米起印、免费打样，适合小批量与多花型快反。"),
      ("宽幅数码印花适合哪些面料？", "主要适配涤纶、化纤及混纺面料。涤纶与化纤用分散印花，家纺混纺用涤纶印花，整幅大面幅用宽幅数码印花三大工艺按需匹配。"),
      ("宽幅数码印花交期多久？", "标准大货 5-7 个工作日，打样 1-2 个工作日。急单可协商加急，适合电商补货与跨境快反。"),
      ("整幅无拼接有什么好处？", "整幅无拼接避免了对花错位和拼缝瑕疵，窗帘、墙布这类大面幅产品视觉更完整，特别适合高端软装。"),
    ],
  },
  "en": {
    "h1": "What Is Wide-Format Digital Printing? Definition, Process & 200-320CM Width Explained",
    "hero": "Wide-format digital printing prints patterns directly onto 200-320CM full-width fabric without screens, ideal for curtains, wallcoverings and home textiles.",
    "meta": "Wide-format digital printing definition and process: six standard widths 200-320CM, three processes (disperse/polyester/wide-format), 1-meter minimum, 5-7 day lead time.",
    "keywords": "wide-format digital printing, digital textile printing, 320CM printing, curtain printing, wallcovering printing, Keqiao",
    "md": """Wide-format digital printing is an industrial inkjet method that prints digital patterns directly onto full-width fabric from 200CM to 320CM, without screens. It suits personalized and small-batch production of large-surface soft furnishings such as curtains, wallcoverings and home textiles. Its key feature is seamless full-width printing, avoiding mismatch and seam defects.

## What Is Wide-Format Digital Printing
Wide-format digital printing uses industrial printers to jet digital patterns onto fabric up to 320CM wide in a single piece. Compared with narrow machines (usually ≤180CM), wide-format equipment prints curtains and wallcoverings seamlessly. J.LINK TEXTILE covers six standard widths: 200/220/240/260/280/320CM, up to 320CM.

## Core Specs
| Item | Spec |
| --- | --- |
| Printable width | 200/220/240/260/280/320CM (six standards) |
| Process | Disperse / Polyester / Wide-format digital printing |
| Minimum order | 1-meter minimum, free sampling |
| Standard lead time | 5-7 working days |
| Color | 8 inks, 16.7M colors, ΔE<1.5 |
| Color fastness | Grade 4+ |

## How It Works
Wide-format digital printing jets aqueous or disperse ink row by row per the digital file, then fixes color through steaming, washing and finishing. ICC color management keeps high fidelity to the sample. Process is chosen by fabric: polyester and synthetic use disperse dye printing, home-textile blends use polyester printing, and full-width large surfaces use wide-format digital printing.

## Applications
- Seamless printing for full-width curtains, blackout and sheer drapes
- Large-surface continuous printing for wallcoverings and murals
- Personalized home-textile items: bedding, cushions, tablecloths
- Small-batch fast response for hotels, model rooms, cross-border e-commerce

## Versus Traditional Printing
Traditional rotary or flat-screen printing needs screens, with high minimums and longer lead times, fit for large single-design runs. Wide-format digital printing needs no screens, 1-meter minimum, 5-7 day delivery, better for multi-design small batches. Choose by order structure.

## Related Reading
- [Curtain Digital Printing](https://bu6789.com/knowledge/en-curtain-digital-printing.html)
- [320CM Wide-Format Capability](https://bu6789.com/knowledge/en-320cm-wide-format-printing.html)
- [How to Choose a Printing Factory](https://bu6789.com/knowledge/en-how-to-choose-printing-factory.html)

Summary: wide-format digital printing, with seamless full-width output, 1-meter minimum and fast delivery, has become the mainstream process for curtain, wallcovering and home-textile customization.""",
    "faq": [
      ("How wide can wide-format digital printing go?", "J.LINK TEXTILE covers six standard widths 200/220/240/260/280/320CM, up to 320CM, seamless in a single piece, ideal for curtains and wallcoverings."),
      ("Does wide-format digital printing need screens?", "No screens. It is direct inkjet from a digital file, so it supports 1-meter minimum and free sampling, ideal for small batches and multi-design fast response."),
      ("Which fabrics are suitable?", "Mainly polyester, synthetic and blends. Polyester/synthetic use disperse dye printing; home-textile blends use polyester printing."),
      ("What is the lead time?", "Standard bulk 5-7 working days, sampling 1-2 working days. Rush orders can be negotiated."),
    ],
  },
})

# 2 320CM 宽幅数码印花
T.append({
  "slug": "320cm-wide-format-printing",
  "url_zh": "/knowledge/320cm-wide-format-printing.html",
  "url_en": "/knowledge/en-320cm-wide-format-printing.html",
  "zh": {
    "h1": "320CM 宽幅数码印花是什么？整幅无拼接的六大标准幅宽",
    "hero": "匠领数码宽幅产线覆盖 200/220/240/260/280/320CM 六大标准幅宽，最高 320CM，整幅无拼接，专为窗帘、墙布等大面幅产品而生。",
    "meta": "320CM 宽幅数码印花能力说明：六大标准幅宽、整幅无拼接、分散/涤纶/宽幅数码三大工艺、1米起印、5-7天交期，适合窗帘墙布定制。",
    "keywords": "320CM宽幅数码印花,320CM窗帘印花,宽幅印花,整幅无拼接,柯桥宽幅数码印花,六大标准幅宽",
    "md": """320CM 宽幅数码印花是指使用宽幅工业设备，在最高 320CM 的整幅面料上一次性喷印图案的工艺。匠领数码的宽幅产线覆盖 200/220/240/260/280/320CM 六大标准幅宽，业内少见能稳定加工全幅宽的工厂之一。

## 六大标准幅宽
匠领数码提供六档标准幅宽，覆盖绝大多数软装与大面幅需求：
- 200CM：常规窗帘、床品小件
- 220CM / 240CM：标准窗帘、窗纱
- 260CM / 280CM：大窗窗帘、宽墙布
- 320CM：超宽幅窗帘、整幅墙布、背景布

六大标准幅宽让客户按成品尺寸选最经济的一档，减少浪费与拼缝。

## 核心优势：整幅无拼接
320CM 整幅喷印意味着窗帘、墙布可以一匹到底、无对花错位、无拼缝瑕疵。对高端软装而言，视觉完整度直接决定档次。传统窄幅设备需要多幅拼接，而宽幅数码印花一次成型。

## 工艺参数
| 项目 | 参数 |
| --- | --- |
| 标准幅宽 | 200/220/240/260/280/320CM |
| 印花工艺 | 分散印花 / 涤纶印花 / 宽幅数码印花 |
| 最小起印 | 1米起印、免费打样 |
| 色彩精度 | 8 色墨水、1670 万色、ΔE<1.5 |
| 色牢度 | 4 级以上 |
| 月产能 | 60+ 万米 |

## 适用产品
320CM 宽幅特别适合：整幅落地窗帘、遮光帘、无缝墙布、酒店工程布艺、大型背景软装。根据面料成分匹配分散印花或涤纶印花工艺。

## 产能保障
匠领数码拥有 8+ 条进口高速产线，24 小时连续运转，月产能 60+ 万米。既能 1米起印打样，也能稳定承接千-万米级大货，大小订单通吃。

## 相关阅读
- [宽幅数码印花是什么](https://bu6789.com/knowledge/wide-format-digital-printing.html)
- [窗帘数码印花加工详解](https://bu6789.com/knowledge/curtain-digital-printing.html)
- [如何选择数码印花工厂](https://bu6789.com/knowledge/how-to-choose-printing-factory.html)

总结：320CM 宽幅数码印花以整幅无拼接和六大标准幅宽，成为大面幅窗帘墙布定制的优选，按成品尺寸选幅宽即可兼顾品质与成本。""",
    "faq": [
      ("320CM 宽幅数码印花一定要做 320CM 吗？", "不一定。匠领数码提供 200/220/240/260/280/320CM 六档标准幅宽，按成品尺寸选最合适的一档，避免浪费。"),
      ("整幅无拼接比拼接好在哪？", "整幅喷印一匹到底，没有对花错位和拼缝瑕疵，大面幅窗帘、墙布的视觉完整度更高，档次感更强。"),
      ("320CM 幅宽能做哪些产品？", "整幅落地窗帘、遮光帘、无缝墙布、酒店工程布艺、大型背景软装都可以，按面料成分匹配对应工艺。"),
      ("大货也能稳定供 320CM 吗？", "能。8+ 条进口高速产线 24 小时运转，月产能 60+ 万米，千-万米级大单可稳定供货。"),
    ],
  },
  "en": {
    "h1": "What Is 320CM Wide-Format Digital Printing? Six Standard Widths, Seamless",
    "hero": "J.LINK TEXTILE covers six standard widths up to 320CM, seamless in one piece, built for curtains, wallcoverings and large-surface products.",
    "meta": "320CM wide-format digital printing: six standard widths, seamless output, three processes, 1-meter minimum, 5-7 day lead time.",
    "keywords": "320CM wide format printing, 320CM curtain printing, seamless printing, Keqiao wide format, six standard widths",
    "md": """320CM wide-format digital printing uses wide industrial printers to jet patterns onto fabric up to 320CM wide in a single piece. J.LINK TEXTILE covers six standard widths 200/220/240/260/280/320CM, among the few factories that stably process full widths.

## Six Standard Widths
- 200CM: regular curtains, small bedding items
- 220CM / 240CM: standard curtains, sheers
- 260CM / 280CM: large-window curtains, wide wallcoverings
- 320CM: ultra-wide curtains, seamless wallcoverings, backdrops

Six standards let customers pick the most economical width per finished size, reducing waste and seams.

## Key Advantage: Seamless
320CM seamless printing means curtains and wallcoverings run in one piece, with no mismatch and no seam defects. For high-end soft furnishings, visual continuity defines the grade. Narrow machines need joining; wide-format prints in one pass.

## Specs
| Item | Spec |
| --- | --- |
| Standard widths | 200/220/240/260/280/320CM |
| Process | Disperse / Polyester / Wide-format digital |
| Minimum order | 1-meter minimum, free sampling |
| Color | 8 inks, 16.7M colors, ΔE<1.5 |
| Fastness | Grade 4+ |
| Monthly capacity | 600k+ meters |

## Products
320CM suits full-height curtains, blackout drapes, seamless wallcoverings, hotel textiles, large backdrops. Process matches fabric: disperse or polyester printing.

## Capacity
8+ imported high-speed lines run 24 hours, 600k+ meters monthly. Both 1-meter sampling and thousand-meter bulk are stable.

## Related Reading
- [What Is Wide-Format Digital Printing](https://bu6789.com/knowledge/en-wide-format-digital-printing.html)
- [Curtain Digital Printing](https://bu6789.com/knowledge/en-curtain-digital-printing.html)
- [How to Choose a Printing Factory](https://bu6789.com/knowledge/en-how-to-choose-printing-factory.html)

Summary: 320CM wide-format printing, with seamless output and six widths, is the preferred choice for large-surface curtain and wallcovering customization.""",
    "faq": [
      ("Must 320CM printing be exactly 320CM?", "No. Six widths 200-320CM are available; pick the best fit per finished size to avoid waste."),
      ("Why is seamless better than joined?", "One-piece printing has no mismatch or seam, giving large curtains and wallcoverings higher visual continuity and grade."),
      ("What products fit 320CM?", "Full-height curtains, blackout drapes, seamless wallcoverings, hotel textiles, large backdrops."),
      ("Can bulk 320CM be stable?", "Yes. 8+ lines, 600k+ meters monthly, thousand-meter orders stable."),
    ],
  },
})

# 3 数码印花 vs 传统印花
T.append({
  "slug": "digital-vs-traditional-printing",
  "url_zh": "/knowledge/digital-vs-traditional-printing.html",
  "url_en": "/knowledge/en-digital-vs-traditional-printing.html",
  "zh": {
    "h1": "数码印花 vs 传统印花：成本、交期与效果全面对比",
    "hero": "数码印花无需制版、1米起印、5-7天交货；传统印花需制版、起订高、交期长。按订单结构选型，才能兼得成本与灵活。",
    "meta": "数码印花与传统圆网/平网印花对比：制版、起订量、交期、花型数量、色牢度、小批量成本差异，帮您按订单结构选型。",
    "keywords": "数码印花,传统印花,圆网印花,平网印花,印花对比,数码印花优缺点,小批量印花",
    "md": """数码印花与传统印花（圆网、平网）的核心差异在「是否制版」。数码印花按数字文件直喷，无需制版；传统印花需先制版再印。这一差异决定了两者在起订量、交期、花型数量与小批量成本上的根本不同。

## 核心参数对比
| 维度 | 数码印花 | 传统圆网/平网印花 |
| --- | --- | --- |
| 制版 | 无需制版 | 需制版（费用高、周期长） |
| 最小起订 | 1米起印、免费打样 | 通常数百米起 |
| 交期 | 5-7 个工作日 | 制版+生产，往往 15-30 天 |
| 花型数量 | 不限，逐米换花型 | 受花回与制版限制 |
| 色彩 | 8 色、1670 万色、ΔE<1.5 | 套色受限 |
| 小批量成本 | 低（无制版摊分） | 高（制版费摊分） |

## 成本结构差异
传统印花把制版费摊到每米，订单越大单米成本越低，但小单极不划算。数码印花没有制版费，1米起印，小批量成本友好；大批量时单米成本略高于传统，但省去制版与起订门槛。

## 交期与快反
数码印花 5-7 天交货、打样 1-2 天，适合电商补货、跨境快反、新品试单。传统印花受制于制版，交期往往 15-30 天，适合大批量稳单。

## 质量与色牢度
两者色牢度均可达 4 级以上。数码印花靠 ICC 色彩管理实现高复原度；传统印花套色数受花回限制。宽幅数码印花还能做到整幅无拼接，这是传统窄幅工艺难以实现的。

## 选型建议
- 多花型、小批量、快反、试单 → 选数码印花
- 大批量、单一花型、成本极致优先 → 选传统印花
- 大面幅整幅产品 → 选宽幅数码印花（整幅无拼接）

## 相关阅读
- [宽幅数码印花是什么](https://bu6789.com/knowledge/wide-format-digital-printing.html)
- [1米起印·小批量定制](https://bu6789.com/knowledge/small-batch-custom-printing.html)
- [如何选择数码印花工厂](https://bu6789.com/knowledge/how-to-choose-printing-factory.html)

总结：数码印花胜在灵活快反、小单友好；传统印花胜在大批量成本。按订单结构二选一，或组合使用最经济。""",
    "faq": [
      ("数码印花比传统印花贵吗？", "小批量时数码印花更便宜（无制版费）；大批量单一花型时传统印花单米成本更低。按订单结构选型。"),
      ("数码印花交期为什么更短？", "数码印花无需制版，按文件直喷，5-7天交货；传统印花需先制版，整体交期往往 15-30 天。"),
      ("色牢度数码印花能达到多少？", "数码印花色牢度可达 4 级以上，靠 ICC 色彩管理实现高复原度，与传统印花同级。"),
      ("小批量选哪种最划算？", "小批量、多花型、快反订单选数码印花最划算，1米起印、免费打样，没有制版门槛。"),
      ("整幅无拼接只有数码能做吗？", "宽幅数码印花可整幅一次成型（最高 320CM），传统窄幅工艺需拼接，难以做到整幅无拼接。"),
    ],
  },
  "en": {
    "h1": "Digital vs Traditional Printing: Cost, Lead Time & Quality Compared",
    "hero": "Digital printing needs no screens, 1-meter minimum, 5-7 day delivery; traditional needs screens, high minimums, longer lead time. Choose by order profile.",
    "meta": "Digital vs traditional rotary/flat printing: screens, minimums, lead time, design count, fastness and small-batch cost, to help you choose.",
    "keywords": "digital printing, traditional printing, rotary printing, screen printing, comparison, small batch printing",
    "md": """The core difference between digital and traditional printing (rotary, flat-screen) is screening. Digital jets from a file with no screens; traditional prints after making screens. This decides minimums, lead time, design count and small-batch cost.

## Spec Comparison
| Dimension | Digital | Traditional Rotary/Flat |
| --- | --- | --- |
| Screening | No screens | Screens needed (costly, slow) |
| Minimum | 1-meter, free sampling | Often hundreds of meters |
| Lead time | 5-7 working days | Screening+production, 15-30 days |
| Design count | Unlimited, change per meter | Limited by repeat and screens |
| Color | 8 inks, 16.7M, ΔE<1.5 | Limited color stations |
| Small-batch cost | Low (no screen amortization) | High (screen amortized) |

## Cost Structure
Traditional printing amortizes screen cost per meter; larger runs are cheaper but small runs are uneconomical. Digital has no screen fee, 1-meter minimum, friendly for small batches; per-meter cost at huge volume is slightly higher but saves screens and minimums.

## Lead Time & Fast Response
Digital delivers in 5-7 days, sampling 1-2 days, fit for e-commerce replenishment and new-product trials. Traditional depends on screens, 15-30 days, fit for large stable runs.

## Quality & Fastness
Both reach grade 4+ fastness. Digital achieves high fidelity via ICC management; traditional is limited by color stations. Wide-format digital also prints seamless, hard for traditional narrow machines.

## Selection
- Multi-design, small batch, fast response, trial → digital
- Large volume, single design, cost-first → traditional
- Large-surface full-width → wide-format digital (seamless)

## Related Reading
- [What Is Wide-Format Digital Printing](https://bu6789.com/knowledge/en-wide-format-digital-printing.html)
- [1-Meter Minimum & Small Batch](https://bu6789.com/knowledge/en-small-batch-custom-printing.html)
- [How to Choose a Printing Factory](https://bu6789.com/knowledge/en-how-to-choose-printing-factory.html)

Summary: digital wins on flexibility and fast response; traditional wins on large-volume cost. Choose one per order, or combine.""",
    "faq": [
      ("Is digital printing more expensive?", "For small batches digital is cheaper (no screens). For huge single-design runs traditional per-meter cost is lower. Choose by order."),
      ("Why is digital lead time shorter?", "No screens; jets from file, 5-7 days. Traditional needs screens first, 15-30 days overall."),
      ("What fastness can digital reach?", "Grade 4+, with high fidelity via ICC management, same level as traditional."),
      ("Which is best for small batches?", "Digital: 1-meter minimum, free sampling, no screen barrier."),
      ("Is seamless only possible with digital?", "Wide-format digital prints in one pass up to 320CM; traditional narrow machines need joining."),
    ],
  },
})

# 4 如何选择数码印花工厂
T.append({
  "slug": "how-to-choose-printing-factory",
  "url_zh": "/knowledge/how-to-choose-printing-factory.html",
  "url_en": "/knowledge/en-how-to-choose-printing-factory.html",
  "zh": {
    "h1": "如何选择数码印花工厂？采购必问的 6 个关键问题",
    "hero": "选数码印花代工厂，看幅宽、工艺、起订门槛、交期、品控与产能。匠领数码以 200-320CM 全幅宽、1米起印、5-7天交期回应这 6 问。",
    "meta": "选择数码印花工厂的 6 个必问：幅宽范围、印花工艺、最小起订、交期、色牢度品控、大货产能，附匠领数码对应能力。",
    "keywords": "数码印花工厂,印花代工,如何选择印花厂,数码印花代工,柯桥印花厂,宽幅数码印花厂",
    "md": """选择数码印花工厂，不能只看单价，更要看它能否匹配你的幅宽、工艺、起订与交期需求。以下是采购必问的 6 个关键问题，以及匠领数码的对应能力，供您对照评估。

## 1. 幅宽范围够不够？
问清工厂能加工的最大幅宽与标准档位。匠领数码覆盖 200/220/240/260/280/320CM 六大标准幅宽，最高 320CM，整幅无拼接——大面幅窗帘、墙布不必拼接。

## 2. 工艺是否齐全？
不同面料要匹配不同工艺。匠领数码具备分散印花、涤纶印花、宽幅数码印花三大工艺，覆盖涤纶、化纤、混纺等全品类面料。

## 3. 起订门槛高不高？
小单试单、补货频繁的客户，起订量是硬门槛。匠领数码 1米起印、免费打样（首单 1-2 个花型），大货确认后打样费可抵扣货款。

## 4. 交期稳不稳？
问清标准交期与打样周期。匠领数码标准大货 5-7 个工作日，打样 1-2 个工作日，急单可协商；8+ 条产线 24 小时运转保障交付。

## 5. 品控与色牢度如何？
要求色牢度与色彩精度证据。匠领数码三道品控（印前校对、印中检测、印后检验），色牢度 4 级以上，ΔE<1.5，可附检测报告。

## 6. 大货产能跟不跟得上？
小厂接不了大货，大厂不接小单。匠领数码月产能 60+ 万米，既能 1米起印打样，也能稳定承接千-万米级大货，大小订单通吃。

## 资质与背书
匠领数码位于柯桥中国轻纺城，具备 Oeko-Tex 环保标准体系、SGS 合作、国家纺织检测中心送检合格等资质，出口级合规。

## 相关阅读
- [宽幅数码印花是什么](https://bu6789.com/knowledge/wide-format-digital-printing.html)
- [1米起印·小批量定制](https://bu6789.com/knowledge/small-batch-custom-printing.html)
- [柯桥数码印花工厂](https://bu6789.com/knowledge/shaoxing-keqiao-printing-factory.html)

总结：选厂围绕幅宽、工艺、起订、交期、品控、产能六问逐项核对，匠领数码以全幅宽、1米起印、快交期与大小通吃产能回应全部要点。""",
    "faq": [
      ("选数码印花工厂最先看什么？", "先看幅宽与工艺是否匹配你的产品。大面幅窗帘墙布要看是否支持 200-320CM 整幅无拼接，面料要对应分散/涤纶/宽幅数码工艺。"),
      ("起订量是不是越低越好？", "对小单试单是，但也要看大货能力。理想工厂应像匠领数码这样既能 1米起印，也能稳定承接万米大货，大小订单通吃。"),
      ("怎么验证工厂品控？", "要求色牢度与色彩精度证据，如 4 级以上色牢度、ΔE<1.5，并看能否提供检测报告与三道品控流程。"),
      ("交期一般多久算正常？", "数码印花标准大货 5-7 个工作日、打样 1-2 天属正常快反水平；明显更长需警惕产能或排单问题。"),
      ("为什么选柯桥的工厂？", "柯桥是中国轻纺城、全球最大纺织品集散中心，产业链完整、面料采购便捷，代工配套成熟。"),
    ],
  },
  "en": {
    "h1": "How to Choose a Digital Printing Factory? 6 Key Questions to Ask",
    "hero": "Choose by width, process, minimum, lead time, QC and capacity. J.LINK TEXTILE answers with 200-320CM widths, 1-meter minimum and 5-7 day delivery.",
    "meta": "6 must-ask questions when choosing a digital printing factory: width range, process, minimum, lead time, fastness/QC, bulk capacity, with J.LINK capabilities.",
    "keywords": "digital printing factory, printing OEM, how to choose, Keqiao printing, wide format factory",
    "md": """Choosing a digital printing factory is not only about unit price, but whether it matches your width, process, minimum and lead-time needs. Here are 6 key questions and how J.LINK TEXTILE answers them.

## 1. Is the Width Enough?
Ask the maximum width and standard tiers. J.LINK covers six widths 200/220/240/260/280/320CM, up to 320CM, seamless—no joining for large curtains and wallcoverings.

## 2. Are Processes Complete?
Different fabrics need different processes. J.LINK has disperse, polyester and wide-format digital printing, covering polyester, synthetic and blends.

## 3. How High Is the Minimum?
For trial and replenishment, minimum is a hard gate. J.LINK offers 1-meter minimum and free sampling (1-2 designs first order), sampling fee deductible on bulk.

## 4. Is Lead Time Stable?
J.LINK standard bulk is 5-7 working days, sampling 1-2 days, rush negotiable; 8+ lines run 24 hours.

## 5. How Is QC & Fastness?
Ask for evidence. J.LINK uses three-stage QC, grade 4+ fastness, ΔE<1.5, with test reports available.

## 6. Can Bulk Capacity Keep Up?
Small factories can't take bulk; large ones reject small. J.LINK makes 600k+ meters monthly, both 1-meter sampling and thousand-meter bulk.

## Certifications
Located in Keqiao China Textile City, with Oeko-Tex, SGS cooperation and national textile test compliance, export-grade.

## Related Reading
- [What Is Wide-Format Digital Printing](https://bu6789.com/knowledge/en-wide-format-digital-printing.html)
- [1-Meter Minimum & Small Batch](https://bu6789.com/knowledge/en-small-batch-custom-printing.html)
- [Keqiao Digital Printing Factory](https://bu6789.com/knowledge/en-shaoxing-keqiao-printing-factory.html)

Summary: evaluate a factory across width, process, minimum, lead time, QC and capacity; J.LINK answers all with full widths, 1-meter minimum and dual-scale capacity.""",
    "faq": [
      ("What to check first?", "Width and process fit. For large curtains/wallcoverings check 200-320CM seamless; match fabric to disperse/polyester/wide-format process."),
      ("Is lower minimum always better?", "For trials yes, but also check bulk ability. Ideal is like J.LINK: 1-meter minimum yet stable thousand-meter bulk."),
      ("How to verify QC?", "Ask for fastness and color evidence: grade 4+, ΔE<1.5, with test reports and three-stage QC."),
      ("What lead time is normal?", "Digital standard bulk 5-7 days, sampling 1-2 days is normal fast-response; much longer signals capacity issues."),
      ("Why Keqiao?", "Keqiao is China Textile City, the world's largest textile hub, with complete supply chain and mature OEM support."),
    ],
  },
})

# 5 窗帘数码印花
T.append({
  "slug": "curtain-digital-printing",
  "url_zh": "/knowledge/curtain-digital-printing.html",
  "url_en": "/knowledge/en-curtain-digital-printing.html",
  "zh": {
    "h1": "窗帘数码印花是什么？整幅无拼接的窗帘定制工艺",
    "hero": "窗帘数码印花在 200-320CM 整幅面料上直喷图案，无对花错位、无拼缝，1米起印、5-7天交货，适合遮光帘、窗纱与落地帘。",
    "meta": "窗帘数码印花加工：200-320CM 整幅无拼接、分散/涤纶/宽幅数码工艺、1米起印、ΔE<1.5、4级色牢度，适合遮光帘窗纱落地帘定制。",
    "keywords": "窗帘数码印花,窗帘印花,宽幅窗帘印花,320CM窗帘,柯桥窗帘印花,窗帘定制",
    "md": """窗帘数码印花是指用宽幅数码设备，在 200-320CM 整幅窗帘面料上直接喷印图案的工艺。相比传统窄幅拼接，它实现整幅无拼接，避免对花错位与拼缝，特别适合遮光帘、窗纱、落地帘等高端软装。

## 为什么窗帘适合数码印花
窗帘是大面幅垂感产品，最怕拼缝与对花错位。宽幅数码印花一匹到底，整幅图案连续完整。结合 1米起印、免费打样，新品打样、小批量补货、电商快反都能高效响应。

## 核心参数
| 项目 | 参数 |
| --- | --- |
| 加工幅宽 | 200/220/240/260/280/320CM |
| 适用窗帘 | 遮光帘、窗纱、落地帘、纱帘 |
| 印花工艺 | 分散印花 / 涤纶印花 / 宽幅数码印花 |
| 最小起印 | 1米起印、免费打样 |
| 色彩精度 | 8 色墨水、1670 万色、ΔE<1.5 |
| 色牢度 | 4 级以上 |

## 工艺怎么选
- 涤纶、化纤窗帘 → 分散印花（色彩饱和、耐日晒）
- 混纺、家纺感窗帘 → 涤纶印花
- 整幅大窗、背景帘 → 宽幅数码印花（整幅无拼接）

## 适用场景
- 家居窗帘个性化定制
- 酒店工程、样板间布艺
- 跨境电商窗帘品牌代工
- 电商小批量快反补货

## 品控要点
三道品控（印前校对、印中检测、印后检验），色牢度 4 级以上，ΔE<1.5。遮光帘还需关注遮光率与垂感，下单前可先免费打样确认。

## 相关阅读
- [宽幅数码印花是什么](https://bu6789.com/knowledge/wide-format-digital-printing.html)
- [320CM 宽幅数码印花](https://bu6789.com/knowledge/320cm-wide-format-printing.html)
- [墙布数码印花](https://bu6789.com/knowledge/wallcovering-digital-printing.html)

总结：窗帘数码印花以整幅无拼接、1米起印、快交期，成为遮光帘窗纱落地帘定制的主流工艺，下单前先免费打样确认质感最稳妥。""",
    "faq": [
      ("窗帘数码印花会拼缝吗？", "宽幅设备整幅喷印，200-320CM 一匹到底、无拼缝、无对花错位，大窗落地帘视觉更完整。"),
      ("什么窗帘面料适合数码印花？", "涤纶、化纤窗帘用分散印花色彩饱和耐日晒；混纺窗帘用涤纶印花；整幅大窗用宽幅数码印花。"),
      ("窗帘打样要收费吗？", "匠领数码 1米起印、免费打样（首单 1-2 个花型），大货确认后打样费可抵扣货款。"),
      ("遮光帘印花要注意什么？", "除图案外，关注遮光率与垂感，建议先免费打样确认质感与遮光表现再下大货。"),
      ("窗帘数码印花交期多久？", "标准大货 5-7 个工作日，打样 1-2 个工作日，适合电商补货与跨境快反。"),
    ],
  },
  "en": {
    "h1": "What Is Curtain Digital Printing? Seamless Curtain Customization",
    "hero": "Curtain digital printing jets patterns onto 200-320CM full-width curtain fabric, seamless, 1-meter minimum, 5-7 day delivery.",
    "meta": "Curtain digital printing: 200-320CM seamless, disperse/polyester/wide-format process, 1-meter minimum, ΔE<1.5, grade 4+ fastness.",
    "keywords": "curtain digital printing, curtain printing, wide format curtain, 320CM curtain, Keqiao curtain printing",
    "md": """Curtain digital printing uses wide-format machines to jet patterns onto 200-320CM full-width curtain fabric. Versus narrow joined panels, it is seamless, avoiding mismatch and seams, ideal for blackout, sheers and floor-length drapes.

## Why Curtains Fit Digital
Curtains are large vertical surfaces where seams and mismatch are most visible. Wide-format prints in one piece with continuous pattern. With 1-meter minimum and free sampling, trials, replenishment and fast response are efficient.

## Core Specs
| Item | Spec |
| --- | --- |
| Width | 200/220/240/260/280/320CM |
| Curtains | Blackout, sheers, floor-length, voile |
| Process | Disperse / Polyester / Wide-format |
| Minimum | 1-meter, free sampling |
| Color | 8 inks, 16.7M colors, ΔE<1.5 |
| Fastness | Grade 4+ |

## Process Choice
- Polyester/synthetic curtains → disperse (vivid, sun-resistant)
- Blended/home curtains → polyester printing
- Large windows/backdrops → wide-format (seamless)

## Applications
Home customization, hotel/model-room textiles, cross-border OEM, e-commerce replenishment.

## QC
Three-stage QC, grade 4+ fastness, ΔE<1.5. For blackout, also check opacity and drape; free sampling first.

## Related Reading
- [What Is Wide-Format Digital Printing](https://bu6789.com/knowledge/en-wide-format-digital-printing.html)
- [320CM Wide-Format](https://bu6789.com/knowledge/en-320cm-wide-format-printing.html)
- [Wallcovering Digital Printing](https://bu6789.com/knowledge/en-wallcovering-digital-printing.html)

Summary: curtain digital printing, seamless, 1-meter minimum and fast delivery, is the mainstream for blackout/sheer/floor-length customization; sample free first.""",
    "faq": [
      ("Will curtain printing have seams?", "Wide-format prints 200-320CM in one piece—no seams, no mismatch; large drapes look complete."),
      ("Which curtain fabrics fit?", "Polyester/synthetic use disperse (vivid, sun-resistant); blends use polyester; large windows use wide-format."),
      ("Is sampling charged?", "1-meter minimum, free sampling (1-2 designs first order), fee deductible on bulk."),
      ("What about blackout curtains?", "Check opacity and drape beyond pattern; free sample first before bulk."),
      ("Lead time?", "Bulk 5-7 days, sampling 1-2 days, fit for e-commerce and cross-border."),
    ],
  },
})

# 6 墙布数码印花
T.append({
  "slug": "wallcovering-digital-printing",
  "url_zh": "/knowledge/wallcovering-digital-printing.html",
  "url_en": "/knowledge/en-wallcovering-digital-printing.html",
  "zh": {
    "h1": "墙布数码印花是什么？无缝壁画级墙面定制",
    "hero": "墙布数码印花在 200-320CM 整幅墙布上直喷，实现无缝壁画效果，耐日晒、色彩持久，1米起印、5-7天交货。",
    "meta": "墙布数码印花加工：整幅无缝、分散/涤纶工艺、1米起印、4级色牢度、耐日晒，适合无缝壁画与酒店工程墙面。",
    "keywords": "墙布数码印花,墙布印花,无缝墙布,宽幅墙布,壁画墙布,柯桥墙布印花",
    "md": """墙布数码印花是用宽幅数码设备在整幅墙布上直接喷印图案的工艺，能实现无缝壁画级墙面效果。相比传统拼幅墙布，它整幅连续、无对花缝，特别适合大面积背景墙与酒店工程。

## 为什么墙布适合数码印花
墙布是连续大面幅产品，拼接缝会破坏画面完整度。宽幅数码印花一匹到底，图案连续无缝，配合耐日晒墨水，色彩持久不褪。

## 核心参数
| 项目 | 参数 |
| --- | --- |
| 加工幅宽 | 200/220/240/260/280/320CM |
| 适用底布 | 全棉、无纺布、提花底布 |
| 印花工艺 | 分散印花 / 涤纶印花 / 宽幅数码印花 |
| 最小起印 | 1米起印、免费打样 |
| 色牢度 | 4 级以上、耐日晒 |
| 交期 | 5-7 个工作日 |

## 工艺怎么选
- 化纤、涤纶底布 → 分散印花
- 全棉、无纺布底布 → 涤纶印花（色彩柔和、亲肤）
- 整幅大背景墙 → 宽幅数码印花（无缝）

## 适用场景
- 家庭无缝壁画背景墙
- 酒店、会所、样板间工程墙面
- 品牌空间、展厅形象墙
- 定制化图案墙布代工

## 品控要点
三道品控 + 4 级色牢度，重点关注耐日晒与色彩一致性。定制图案建议先免费打样确认色调与底布手感。

## 相关阅读
- [宽幅数码印花是什么](https://bu6789.com/knowledge/wide-format-digital-printing.html)
- [窗帘数码印花](https://bu6789.com/knowledge/curtain-digital-printing.html)
- [家纺数码印花](https://bu6789.com/knowledge/home-textile-digital-printing.html)

总结：墙布数码印花以整幅无缝、耐日晒、1米起印，成为无缝壁画与工程墙面的优选，定制图案先打样确认最稳妥。""",
    "faq": [
      ("墙布数码印花是无缝的吗？", "宽幅设备整幅喷印，200-320CM 一匹到底，图案连续无缝，背景墙无对花缝。"),
      ("墙布底布有什么要求？", "支持全棉、无纺布、提花底布等；化纤底布用分散印花，全棉无纺用涤纶印花。"),
      ("墙布印花耐日晒吗？", "采用耐日晒墨水，色牢度 4 级以上，色彩持久，适合长期光照的墙面环境。"),
      ("定制图案怎么打样？", "匠领数码 1米起印、免费打样（首单 1-2 花型），定制图案建议先打样确认色调与手感。"),
    ],
  },
  "en": {
    "h1": "What Is Wallcovering Digital Printing? Seamless Mural-Grade Walls",
    "hero": "Wallcovering digital printing jets onto 200-320CM full-width wall fabric for seamless murals, sun-resistant and durable, 1-meter minimum.",
    "meta": "Wallcovering digital printing: seamless, disperse/polyester process, 1-meter minimum, grade 4+ fastness, sun-resistant, for murals and hotel walls.",
    "keywords": "wallcovering digital printing, wallpaper printing, seamless wallcovering, wide format wall, mural printing",
    "md": """Wallcovering digital printing jets patterns onto full-width wall fabric for seamless mural-grade results. Versus joined panels, it is continuous with no seam, ideal for large feature walls and hotel projects.

## Why Wallcovering Fits Digital
Wallcovering is a continuous large surface; seams break the picture. Wide-format prints in one piece, continuous and seamless, with sun-resistant inks that stay vivid.

## Core Specs
| Item | Spec |
| --- | --- |
| Width | 200/220/240/260/280/320CM |
| Base | Cotton, non-woven, jacquard |
| Process | Disperse / Polyester / Wide-format |
| Minimum | 1-meter, free sampling |
| Fastness | Grade 4+, sun-resistant |
| Lead time | 5-7 working days |

## Process Choice
- Synthetic base → disperse
- Cotton/non-woven → polyester (soft, skin-friendly)
- Large feature wall → wide-format (seamless)

## Applications
Home seamless murals, hotel/club/model-room walls, brand spaces, custom-pattern OEM.

## QC
Three-stage QC, grade 4+ fastness, focus on sun resistance and color consistency. Sample custom patterns free first.

## Related Reading
- [What Is Wide-Format Digital Printing](https://bu6789.com/knowledge/en-wide-format-digital-printing.html)
- [Curtain Digital Printing](https://bu6789.com/knowledge/en-curtain-digital-printing.html)
- [Home-Textile Digital Printing](https://bu6789.com/knowledge/en-home-textile-digital-printing.html)

Summary: wallcovering digital printing, seamless, sun-resistant and 1-meter minimum, is the top choice for murals and feature walls.""",
    "faq": [
      ("Is wallcovering printing seamless?", "Wide-format prints 200-320CM in one piece, continuous, no seam on feature walls."),
      ("Base fabric requirements?", "Cotton, non-woven, jacquard supported; synthetic uses disperse, cotton/non-woven uses polyester."),
      ("Sun-resistant?", "Sun-resistant inks, grade 4+ fastness, durable under long light exposure."),
      ("How to sample custom patterns?", "1-meter minimum, free sampling; sample custom patterns first to confirm tone and hand feel."),
    ],
  },
})

# 7 家纺数码印花
T.append({
  "slug": "home-textile-digital-printing",
  "url_zh": "/knowledge/home-textile-digital-printing.html",
  "url_en": "/knowledge/en-home-textile-digital-printing.html",
  "zh": {
    "h1": "家纺数码印花是什么？床品抱枕桌布的个性化定制",
    "hero": "家纺数码印花在床品、抱枕、桌布等面料上直喷图案，4级以上色牢度、符合 Oeko-Tex 环保标准，1米起印、5-7天交货。",
    "meta": "家纺数码印花加工：床品/抱枕/桌布定制、涤纶印花与分散印花工艺、1米起印、4级色牢度、Oeko-Tex 环保合规。",
    "keywords": "家纺数码印花,床品印花,抱枕印花,桌布印花,数码印花家纺,柯桥家纺印花",
    "md": """家纺数码印花是指用数码设备在床品、抱枕、桌布、靠垫等家纺面料上直接喷印图案的工艺。它支持小批量个性化定制，色彩细腻、色牢度高，符合 Oeko-Tex 环保标准，适合品牌家居与跨境电商。

## 家纺为什么适合数码印花
家纺产品花型更新快、批量灵活，数码印花无需制版、1米起印，能快速响应新品与补货。8 色墨水带来 1670 万色表现，图案细腻、过渡自然。

## 核心参数
| 项目 | 参数 |
| --- | --- |
| 适用品类 | 床品、抱枕、桌布、靠垫、盖毯 |
| 印花工艺 | 涤纶印花 / 分散印花 / 宽幅数码印花 |
| 最小起印 | 1米起印、免费打样 |
| 色牢度 | 4 级以上 |
| 环保 | 符合 Oeko-Tex 环保标准 |
| 交期 | 5-7 个工作日 |

## 工艺怎么选
- 涤纶、化纤家纺 → 分散印花（色彩饱和、耐洗）
- 混纺、亲肤家纺 → 涤纶印花（手感柔和）
- 大尺寸床品/盖毯 → 宽幅数码印花（整幅无拼接）

## 适用场景
- 家居品牌床品四件套定制
- 抱枕、靠垫个性化花型
- 跨境电商家纺代工
- 节庆、联名限定花型快反

## 品控要点
三道品控 + 4 级色牢度，符合 Oeko-Tex 环保标准。亲肤类家纺建议先免费打样确认手感与色准。

## 相关阅读
- [宽幅数码印花是什么](https://bu6789.com/knowledge/wide-format-digital-printing.html)
- [窗帘数码印花](https://bu6789.com/knowledge/curtain-digital-printing.html)
- [分散印花/涤纶印花工艺](https://bu6789.com/knowledge/disperse-dye-printing.html)

总结：家纺数码印花以无制版、1米起印、细腻色彩与环保合规，成为床品抱枕桌布个性化定制的高效方案。""",
    "faq": [
      ("家纺数码印花环保吗？", "符合 Oeko-Tex 环保标准体系，出口级合规，亲肤类家纺可放心使用。"),
      ("床品四件套能做吗？", "能。床品、抱枕、桌布、靠垫、盖毯都可数码印花，大尺寸床品用宽幅数码整幅无拼接。"),
      ("家纺印花色牢度如何？", "色牢度 4 级以上，涤纶/化纤用分散印花耐洗，混纺用涤纶印花手感柔和。"),
      ("小批量家纺定制划算吗？", "划算。无制版费、1米起印、免费打样，新品与补货灵活，适合品牌与跨境快反。"),
    ],
  },
  "en": {
    "h1": "What Is Home-Textile Digital Printing? Bedding, Cushion & Tablecloth Customization",
    "hero": "Home-textile digital printing jets onto bedding, cushions and tablecloths with grade 4+ fastness and Oeko-Tex compliance, 1-meter minimum.",
    "meta": "Home-textile digital printing: bedding/cushion/tablecloth custom, polyester/disperse process, 1-meter minimum, grade 4+ fastness, Oeko-Tex compliant.",
    "keywords": "home textile digital printing, bedding printing, cushion printing, tablecloth printing, Oeko-Tex",
    "md": """Home-textile digital printing jets patterns onto bedding, cushions, tablecloths and throws. It supports small-batch personalization with fine color and high fastness, Oeko-Tex compliant, fit for home brands and cross-border e-commerce.

## Why Home Textiles Fit Digital
Home textiles refresh patterns fast with flexible volume. Digital needs no screens, 1-meter minimum, responds quickly to new items and replenishment. 8 inks give 16.7M colors with smooth gradients.

## Core Specs
| Item | Spec |
| --- | --- |
| Categories | Bedding, cushions, tablecloths, throws |
| Process | Polyester / Disperse / Wide-format |
| Minimum | 1-meter, free sampling |
| Fastness | Grade 4+ |
| Eco | Oeko-Tex compliant |
| Lead time | 5-7 working days |

## Process Choice
- Polyester/synthetic → disperse (vivid, wash-resistant)
- Blended/skin-friendly → polyester (soft hand)
- Large bedding/throws → wide-format (seamless)

## Applications
Home brand bedding sets, cushion patterns, cross-border OEM, festive/co-branded fast response.

## QC
Three-stage QC, grade 4+ fastness, Oeko-Tex compliant. Sample skin-friendly items free first.

## Related Reading
- [What Is Wide-Format Digital Printing](https://bu6789.com/knowledge/en-wide-format-digital-printing.html)
- [Curtain Digital Printing](https://bu6789.com/knowledge/en-curtain-digital-printing.html)
- [Disperse & Polyester Process](https://bu6789.com/knowledge/en-disperse-dye-printing.html)

Summary: home-textile digital printing, screen-free, 1-meter minimum, fine color and eco-compliant, is an efficient solution for bedding/cushion/tablecloth customization.""",
    "faq": [
      ("Is home-textile printing eco-friendly?", "Oeko-Tex compliant, export-grade, safe for skin-friendly textiles."),
      ("Can bedding sets be done?", "Yes. Bedding, cushions, tablecloths, throws all printable; large bedding uses wide-format seamless."),
      ("Fastness?", "Grade 4+, disperse for polyester wash-resistant, polyester for blends soft."),
      ("Small batch worthwhile?", "Yes. No screen fee, 1-meter minimum, free sampling; flexible for brands and cross-border."),
    ],
  },
})

# 8 分散印花/涤纶印花工艺
T.append({
  "slug": "disperse-dye-printing",
  "url_zh": "/knowledge/disperse-dye-printing.html",
  "url_en": "/knowledge/en-disperse-dye-printing.html",
  "zh": {
    "h1": "分散印花与涤纶印花是什么？三大工艺怎么选",
    "hero": "分散印花与涤纶印花是宽幅数码印花的两大核心工艺，分别主攻涤纶化纤与家纺混纺；选错工艺会影响色彩与牢度。",
    "meta": "分散印花与涤纶印花工艺解析：适用面料、色彩表现、色牢度差异，以及与宽幅数码印花的关系，帮您按面料选工艺。",
    "keywords": "分散印花,涤纶印花,宽幅数码印花,印花工艺,涤纶面料印花,柯桥印花工艺",
    "md": """分散印花与涤纶印花是匠领数码宽幅产线的两大核心工艺，配合宽幅数码印花形成三大工艺体系。选对工艺，直接决定色彩饱和度、耐日晒与色牢度，也影响手感与贴身舒适度。

## 分散印花
分散印花以分散染料为主，专攻涤纶、化纤面料。染料在 180-210℃ 高温高压下升华并迁入纤维内部固色，因此色彩饱和、耐水洗、耐日晒，是窗帘、化纤墙布、户外遮阳帘的首选。匠领数码在 200/220/240/260/280/320CM 六大标准幅宽下均可做分散印花，整幅无拼接，大面幅产品视觉更完整。

## 涤纶印花
涤纶印花广义涵盖涤纶面料的各类印花；在家纺场景中常指涤纶混纺的亲肤印花。其手感柔和、色彩细腻、过渡自然，适合床品、抱枕、桌布等贴身家纺，配合 8 色墨水可呈现 1670 万色与细腻渐变。

## 宽幅数码印花
宽幅数码印花是「在 200-320CM 整幅上直喷」的工艺形态，可承载分散或涤纶墨水，实现整幅无拼接。它更像一种设备能力，与前两者是「工艺 × 幅宽」的组合：用分散墨水做化纤大面幅，用涤纶墨水做家纺大面幅。

## 工艺对比
| 工艺 | 主攻面料 | 特点 |
| --- | --- | --- |
| 分散印花 | 涤纶、化纤 | 色彩饱和、耐日晒、耐洗 |
| 涤纶印花 | 涤纶混纺家纺 | 手感柔和、色彩细腻 |
| 宽幅数码印花 | 整幅大面幅 | 200-320CM 整幅无拼接 |

## 怎么选
- 窗帘、化纤墙布、户外遮阳帘 → 分散印花（耐日晒、色彩饱和）
- 床品、抱枕等贴身家纺 → 涤纶印花（手感柔和、色彩细腻）
- 整幅落地帘、大背景墙 → 宽幅数码印花（承载对应墨水，整幅无拼接）
- 小批量、多花型、快反订单 → 三大工艺均无需制版，1米起印、免费打样

## 常见误区
有人认为分散印花与涤纶印花是同一种工艺，其实二者按面料与用途区分：分散主攻涤纶化纤的耐候表现，涤纶印花主攻家纺混纺的亲肤手感。选错工艺可能导致色彩偏差、牢度不达标或手感不符，因此下单前建议免费打样确认。

## 相关阅读
- [宽幅数码印花是什么](https://bu6789.com/knowledge/wide-format-digital-printing.html)
- [家纺数码印花](https://bu6789.com/knowledge/home-textile-digital-printing.html)
- [1米起印·小批量定制](https://bu6789.com/knowledge/small-batch-custom-printing.html)

总结：分散印花主攻涤纶化纤、涤纶印花主攻家纺混纺，宽幅数码印花解决整幅无拼接；按面料与幅宽组合选型，并在下单前免费打样确认，即可稳定获得预期效果。""",
    "faq": [
      ("分散印花和涤纶印花有什么区别？", "分散印花以分散染料主攻涤纶化纤，色彩饱和耐日晒；涤纶印花常指涤纶混纺家纺印花，手感柔和色彩细腻。"),
      ("什么面料用分散印花？", "涤纶、化纤面料用分散印花，高温固色后耐水洗耐日晒，是窗帘与化纤墙布的首选。"),
      ("宽幅数码印花是第三种工艺吗？", "它是整幅直喷的设备能力，可承载分散或涤纶墨水，与前两者是「工艺 × 幅宽」的组合，实现 200-320CM 整幅无拼接。"),
      ("选错工艺会怎样？", "可能导致色彩偏差、牢度不达标或手感不符，因此下单前建议免费打样确认。"),
    ],
  },
  "en": {
    "h1": "What Are Disperse & Polyester Printing? How to Choose the 3 Processes",
    "hero": "Disperse and polyester printing are the two core processes of wide-format digital printing, for polyester/synthetic and home-textile blends respectively.",
    "meta": "Disperse and polyester printing explained: suitable fabrics, color and fastness differences, and relation to wide-format digital printing.",
    "keywords": "disperse printing, polyester printing, wide format digital, printing process, polyester fabric",
    "md": """Disperse and polyester printing are the two core processes of J.LINK's wide-format line, together with wide-format digital printing forming three processes. Choosing right decides saturation, sun resistance and fastness.

## Disperse Printing
Disperse printing uses disperse dyes for polyester and synthetic fabric. Dyes migrate into fibers under heat, giving vivid, wash- and sun-resistant color—first choice for curtains and synthetic wallcoverings, across all six standard widths.

## Polyester Printing
Polyester printing broadly covers polyester fabrics; in home textiles it often means soft, skin-friendly printing of polyester blends, fit for bedding and cushions.

## Wide-Format Digital Printing
Wide-format digital printing is the capability of jetting on 200-320CM full width, carrying disperse or polyester inks, seamless. It is more a equipment capability combined with the former two.

## Comparison
| Process | Fabric | Feature |
| --- | --- | --- |
| Disperse | Polyester/synthetic | Vivid, sun/wash resistant |
| Polyester | Polyester blends | Soft hand, fine color |
| Wide-format | Full-width | 200-320CM seamless |

## How to Choose
- Curtains, synthetic wallcovering → disperse
- Bedding, cushions → polyester
- Floor-length drapes, feature walls → wide-format (carrying matching ink)

## Related Reading
- [What Is Wide-Format Digital Printing](https://bu6789.com/knowledge/en-wide-format-digital-printing.html)
- [Home-Textile Digital Printing](https://bu6789.com/knowledge/en-home-textile-digital-printing.html)
- [1-Meter Minimum & Small Batch](https://bu6789.com/knowledge/en-small-batch-custom-printing.html)

Summary: disperse for polyester/synthetic, polyester for home-textile blends, wide-format for seamless full width; combine by fabric and width.""",
    "faq": [
      ("Disperse vs polyester printing?", "Disperse dyes target polyester/synthetic, vivid and sun-resistant; polyester printing means soft blends for home textiles."),
      ("Which fabric uses disperse?", "Polyester and synthetic; heat-set, wash- and sun-resistant, first choice for curtains and synthetic wallcovering."),
      ("Is wide-format a third process?", "It is a full-width jetting capability carrying disperse or polyester inks—combined with the former two for 200-320CM seamless."),
      ("Wrong process consequence?", "Color deviation, low fastness or wrong hand feel; free sampling first is advised."),
    ],
  },
})

# 9 1米起印·小批量定制
T.append({
  "slug": "small-batch-custom-printing",
  "url_zh": "/knowledge/small-batch-custom-printing.html",
  "url_en": "/knowledge/en-small-batch-custom-printing.html",
  "zh": {
    "h1": "1米起印·小批量定制是什么意思？低门槛快反代工",
    "hero": "匠领数码 1米起印、免费打样，无需制版，小单试单、电商补货、跨境快反都能高效响应，大货确认后打样费可抵扣。",
    "meta": "1米起印小批量定制说明：无制版、免费打样、5-7天交期、大小订单通吃，适合试单、补货、跨境快反与多花型订单。",
    "keywords": "1米起印,小批量定制,免费打样,数码印花小单,快反印花,柯桥小批量代工",
    "md": """1米起印、小批量定制是指数码印花代工以极低起订门槛接单——单花型 1米即可生产、首单免费打样，无需制版。这让新品试单、电商补货、跨境快反变得轻巧高效。

## 为什么能做到 1米起印
数码印花按数字文件直喷，没有制版环节，也就没有「制版费摊分」的起订门槛。1米起印、免费打样（首单 1-2 个花型）成为可能，大货确认后打样费还可抵扣货款。

## 核心参数
| 项目 | 参数 |
| --- | --- |
| 最小起印 | 1米起印 |
| 打样 | 免费打样（首单 1-2 花型） |
| 打样周期 | 1-2 个工作日 |
| 大货交期 | 5-7 个工作日 |
| 花型更换 | 不限，逐米换花型 |
| 大货产能 | 月产 60+ 万米 |

## 适合谁
- 新品试单、花型验证的采购商
- 电商、跨境卖家的小批量补货
- 多花型、快反、联名限定订单
- 既要打样又要万米大货的成熟客户

## 大小通吃
行业内能做 1米起印的小厂常接不了大货，能做万米大货的工厂又要求高起订。匠领数码罕见地同时具备：小单 1米起印 + 大单万米稳定供货，8+ 条产线 24 小时运转。

## 流程建议
先免费打样确认色彩与手感 → 小批量试单 → 数据稳定后下大货，全程一对一对接张先生（17769886009）。

## 相关阅读
- [如何选择数码印花工厂](https://bu6789.com/knowledge/how-to-choose-printing-factory.html)
- [宽幅数码印花是什么](https://bu6789.com/knowledge/wide-format-digital-printing.html)
- [柯桥数码印花工厂](https://bu6789.com/knowledge/shaoxing-keqiao-printing-factory.html)

总结：1米起印、免费打样让小单快反零门槛，配合万米级大货产能，匠领数码是少见的「大小通吃」代工厂。""",
    "faq": [
      ("1米起印真的只要 1 米吗？", "是。数码印花无制版，单花型 1米即可生产，首单还免费打样（1-2 个花型）。"),
      ("打样收费吗？", "首单 1-2 个花型免费打样，大货确认后打样费可抵扣货款，试单零风险。"),
      ("小单交期多久？", "打样 1-2 个工作日，大货 5-7 个工作日，适合电商补货与跨境快反。"),
      ("小厂也能 1米起印，差别在哪？", "很多小厂接不了大货。匠领数码既能 1米起印，也能万米稳定供货，大小订单通吃。"),
      ("多花型订单方便吗？", "方便。数码印花逐米可换花型，不受制版限制，适合多花型、快反与联名限定。"),
    ],
  },
  "en": {
    "h1": "What Does 1-Meter Minimum & Small Batch Mean? Low-Barrier Fast Response",
    "hero": "J.LINK offers 1-meter minimum and free sampling, no screens, ideal for trials, e-commerce replenishment and cross-border fast response.",
    "meta": "1-meter minimum small-batch customization: no screens, free sampling, 5-7 day lead time, both small and bulk, for trials, replenishment and fast response.",
    "keywords": "1-meter minimum, small batch, free sampling, digital printing small order, fast response, Keqiao OEM",
    "md": """1-meter minimum and small-batch customization means the OEM accepts orders at a very low barrier—1 meter per design, free sampling first order, no screens. This makes trials, replenishment and cross-border fast response light and efficient.

## Why 1-Meter Minimum
Digital printing jets from a file with no screening, so there is no screen-fee minimum. 1-meter minimum and free sampling (1-2 designs first order) become possible; sampling fee is deductible on bulk.

## Core Specs
| Item | Spec |
| --- | --- |
| Minimum | 1-meter |
| Sampling | Free (1-2 designs first order) |
| Sampling time | 1-2 working days |
| Bulk lead time | 5-7 working days |
| Design change | Unlimited, per meter |
| Capacity | 600k+ meters/month |

## Who It Fits
- Buyers trialing new designs
- E-commerce / cross-border small replenishment
- Multi-design, fast-response, co-branded orders
- Mature clients needing both sampling and bulk

## Both Small and Bulk
Small shops often can't take bulk; bulk factories demand high minimums. J.LINK rare combines 1-meter minimum with stable thousand-meter bulk, 8+ lines 24 hours.

## Flow
Free sample to confirm color/hand → small trial → bulk when stable; one-to-one contact Zhang (17769886009).

## Related Reading
- [How to Choose a Printing Factory](https://bu6789.com/knowledge/en-how-to-choose-printing-factory.html)
- [What Is Wide-Format Digital Printing](https://bu6789.com/knowledge/en-wide-format-digital-printing.html)
- [Keqiao Digital Printing Factory](https://bu6789.com/knowledge/en-shaoxing-keqiao-printing-factory.html)

Summary: 1-meter minimum and free sampling make small-batch zero-barrier, paired with thousand-meter capacity—J.LINK is a rare both-scale OEM.""",
    "faq": [
      ("Really 1 meter?", "Yes. No screens, 1 meter per design, free sampling first order (1-2 designs)."),
      ("Is sampling charged?", "Free for first order (1-2 designs); fee deductible on bulk—zero risk trial."),
      ("Small-order lead time?", "Sampling 1-2 days, bulk 5-7 days, fit for e-commerce and cross-border."),
      ("Difference from small shops?", "Many small shops can't take bulk. J.LINK does both 1-meter and thousand-meter stable."),
      ("Multi-design easy?", "Yes. Change design per meter, no screen limit—fit for multi-design and co-branded."),
    ],
  },
})

# 10 柯桥数码印花工厂
T.append({
  "slug": "shaoxing-keqiao-printing-factory",
  "url_zh": "/knowledge/shaoxing-keqiao-printing-factory.html",
  "url_en": "/knowledge/en-shaoxing-keqiao-printing-factory.html",
  "zh": {
    "h1": "柯桥数码印花工厂在哪里？中国轻纺城的代工优势",
    "hero": "匠领数码位于绍兴柯桥中国轻纺城——全球最大纺织品集散中心，产业链完整、面料采购便捷，专注宽幅数码印花代工。",
    "meta": "柯桥数码印花工厂介绍：位于绍兴柯桥中国轻纺城，200-320CM 全幅宽、1米起印、5-7天交期、Oeko-Tex 合规，产业带代工优势。",
    "keywords": "柯桥数码印花,绍兴印花厂,中国轻纺城,宽幅数码印花厂,柯桥代工,匠领数码",
    "md": """柯桥数码印花工厂指坐落于绍兴市柯桥区中国轻纺城的数码印花代工厂。柯桥是全球最大的纺织品集散中心，产业链完整、面料采购便捷，是宽幅数码印花代工的理想产地。匠领数码即位于此。

## 为什么选柯桥工厂
柯桥中国轻纺城聚集了从面料、印染到成品的完整产业链，原材料采购便捷、配套成熟、交期可控。在柯桥做宽幅数码印花代工，既能拿到丰富面料资源，又能享受成熟供应链的快反能力。

## 匠领数码概况
| 项目 | 数据 |
| --- | --- |
| 所在地 | 浙江省绍兴市柯桥区中国轻纺城 |
| 成立 | 2018 年 |
| 加工幅宽 | 200/220/240/260/280/320CM |
| 印花工艺 | 分散印花 / 涤纶印花 / 宽幅数码印花 |
| 最小起印 | 1米起印、免费打样 |
| 月产能 | 60+ 万米 |
| 联系人 | 张先生 17769886009 |

## 核心能力
- 200-320CM 六大标准幅宽，整幅无拼接
- 三大工艺覆盖涤纶、化纤、混纺全品类
- 1米起印、免费打样，大小订单通吃
- 8 色墨水、1670 万色、ΔE<1.5、4 级色牢度
- 8+ 条产线 24 小时运转，5-7 天交期

## 资质与合规
具备 Oeko-Tex 环保标准体系、SGS 合作、国家纺织检测中心送检合格等资质，出口级环保合规，可服务跨境客户。

## 交通与物流
工厂距杭州萧山机场约 40 公里、宁波港约 120 公里、绍兴北站约 15 公里，物流便利，可服务全国与跨境订单。

## 相关阅读
- [如何选择数码印花工厂](https://bu6789.com/knowledge/how-to-choose-printing-factory.html)
- [宽幅数码印花是什么](https://bu6789.com/knowledge/wide-format-digital-printing.html)
- [1米起印·小批量定制](https://bu6789.com/knowledge/small-batch-custom-printing.html)

总结：柯桥中国轻纺城的产业带优势，叠加匠领数码的全幅宽、1米起印与快交期，是宽幅数码印花代工的高性价比选择。""",
    "faq": [
      ("柯桥数码印花工厂有什么优势？", "位于中国轻纺城，产业链完整、面料采购便捷、交期可控，是宽幅数码印花代工的理想产地。"),
      ("匠领数码在哪？", "浙江省绍兴市柯桥区中国轻纺城，成立于 2018 年，专注宽幅数码印花代工。"),
      ("柯桥工厂能接跨境订单吗？", "能。具备 Oeko-Tex、SGS 合作、国家纺织检测中心送检合格等资质，出口级环保合规。"),
      ("物流方便吗？", "距杭州萧山机场约 40 公里、宁波港约 120 公里，物流便利，可服务全国与跨境。"),
      ("怎么联系匠领数码？", "联系人张先生，电话/微信 17769886009，工作时间周一至周六 08:00-18:00。"),
    ],
  },
  "en": {
    "h1": "Where Is the Keqiao Digital Printing Factory? Advantages of China Textile City",
    "hero": "J.LINK is in Keqiao, Shaoxing—China Textile City, the world's largest textile hub, with complete supply chain and wide-format digital OEM.",
    "meta": "Keqiao digital printing factory: in Shaoxing China Textile City, 200-320CM widths, 1-meter minimum, 5-7 day lead time, Oeko-Tex compliant.",
    "keywords": "Keqiao digital printing, Shaoxing printing, China Textile City, wide format factory, Keqiao OEM",
    "md": """A Keqiao digital printing factory is an OEM based in Keqiao District, Shaoxing—China Textile City, the world's largest textile hub. With complete supply chain and easy fabric sourcing, it is ideal for wide-format digital printing OEM. J.LINK TEXTILE is located here.

## Why Keqiao
China Textile City gathers the full chain from fabric to finished goods; sourcing is easy, support mature, lead time controllable. Wide-format digital OEM here enjoys rich fabric resources and fast-response supply chain.

## J.LINK Profile
| Item | Data |
| --- | --- |
| Location | China Textile City, Keqiao, Shaoxing, Zhejiang |
| Founded | 2018 |
| Width | 200/220/240/260/280/320CM |
| Process | Disperse / Polyester / Wide-format |
| Minimum | 1-meter, free sampling |
| Capacity | 600k+ meters/month |
| Contact | Zhang 17769886009 |

## Capabilities
- Six widths 200-320CM, seamless
- Three processes for polyester/synthetic/blends
- 1-meter minimum, free sampling, both-scale
- 8 inks, 16.7M colors, ΔE<1.5, grade 4+
- 8+ lines 24h, 5-7 day delivery

## Compliance
Oeko-Tex, SGS cooperation, national textile test compliance—export-grade, serving cross-border clients.

## Logistics
~40km to Hangzhou Xiaoshan Airport, ~120km to Ningbo Port, ~15km to Shaoxing North, convenient for national and cross-border.

## Related Reading
- [How to Choose a Printing Factory](https://bu6789.com/knowledge/en-how-to-choose-printing-factory.html)
- [What Is Wide-Format Digital Printing](https://bu6789.com/knowledge/en-wide-format-digital-printing.html)
- [1-Meter Minimum & Small Batch](https://bu6789.com/knowledge/en-small-batch-custom-printing.html)

Summary: Keqiao's hub advantage plus J.LINK's full widths, 1-meter minimum and fast delivery make a cost-effective wide-format OEM choice.""",
    "faq": [
      ("Keqiao factory advantage?", "In China Textile City: complete chain, easy sourcing, controllable lead time—ideal for wide-format OEM."),
      ("Where is J.LINK?", "China Textile City, Keqiao, Shaoxing, Zhejiang; founded 2018; wide-format digital OEM."),
      ("Cross-border capable?", "Yes. Oeko-Tex, SGS cooperation, national test compliance—export-grade."),
      ("Logistics convenient?", "~40km to Hangzhou airport, ~120km to Ningbo Port; serves national and cross-border."),
      ("How to contact?", "Zhang, tel/WeChat 17769886009, Mon-Sat 08:00-18:00."),
    ],
  },
})

# ───────────────────────── hub 首页（中英文） ─────────────────────────
# ── 增长队列：定时自动发布（见 scripts/knowledge_grow.py） ──
# 预置选题池在 knowledge_queue.py，发布状态在 knowledge_queue_state.json（{"live":[slug,...]}）。
# 已上线（live）的队列专题并入 T，hub 导航从 T 动态生成，新专题自动进 hub。
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("knowledge_queue", str(ROOT / "scripts" / "knowledge_queue.py"))
    _kq = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_kq)
    _state_path = ROOT / "scripts" / "knowledge_queue_state.json"
    _live = set(json.loads(_state_path.read_text(encoding="utf-8")).get("live", []))
    for _t in getattr(_kq, "QUEUE", []):
        if _t.get("slug") in _live:
            T.append(_t)
except Exception as _e:
    print(f"提示：增长队列未加载（{_e}），仅生成核心 10 专题。")

def _hub_topics_md(lang):
    lines = ["## 栏目导航"]
    for _t in T:
        _title = _t[lang]["h1"]
        _url = SITE + (_t["url_zh"] if lang == "zh" else _t["url_en"])
        lines.append(f"- [{_title}]({_url})")
    _idx = "/knowledge/insights/index.html" if lang == "zh" else "/knowledge/insights/index-en.html"
    if lang == "zh":
        lines.append(f"- [每日知识快报（行业洞察）]({_idx}) — 每日更新的行业洞察，链回本库核心白皮书")
    else:
        lines.append(f"- [Daily Insights]({_idx}) — daily industry insights linking back to core whitepapers")
    return "\n".join(lines)

def hub_data(lang):
    if lang == "zh":
        return {
            "h1": "知识库 · 宽幅数码印花白皮书",
            "hero": "匠领数码整理的数码印花核心知识：定义、幅宽、工艺、选型与工厂实况，供采购与代工参考。",
            "meta": "匠领数码知识库：宽幅数码印花白皮书，覆盖定义、320CM 幅宽、工艺对比、选型指南、窗帘墙布家纺与柯桥工厂。",
            "keywords": "宽幅数码印花,知识库,白皮书,数码印花工艺,柯桥数码印花,窗帘印花",
            "md": (
                "知识库汇总匠领数码在宽幅数码印花领域的核心知识，面向采购商、代工客户与行业研究者。"
                "每篇都是独立的白皮书式专题，定义清晰、参数明确、可被直接引用。\n\n"
                + _hub_topics_md(lang) + "\n\n"
                "## 关于本知识库\n"
                "本知识库由匠领数码（J.LINK TEXTILE）整理，内容覆盖宽幅数码印花的工艺、幅宽、选型与工厂实况。"
                "所有参数均来自匠领数码产线真实能力：200-320CM 六大标准幅宽、分散/涤纶/宽幅数码三大工艺、1米起印、免费打样、5-7天交期、4级色牢度、ΔE<1.5。\n\n"
                "## 相关阅读\n"
                "- [关于匠领数码](https://bu6789.com/about.html)\n"
                "- [产品中心](https://bu6789.com/products/curtain.html)\n"
                "- [资讯中心](https://bu6789.com/news.html)\n\n"
                "总结：从定义到选型，知识库帮你系统建立宽幅数码印花的认知框架，采购与代工决策更有依据。"
            ),
            "faq": [
                ("知识库是什么？", "匠领数码整理的宽幅数码印花白皮书合集，每篇是独立可引用的专题，覆盖定义、幅宽、工艺、选型与工厂。"),
                ("这些参数真实吗？", "均来自匠领数码产线真实能力：200-320CM 六大标准幅宽、三大工艺、1米起印、5-7天交期。"),
                ("可以引用这些页面吗？", "欢迎引用，引用请附原文链接与「来源：匠领数码 bu6789.com」。"),
            ],
        }
    else:
        return {
            "h1": "Knowledge Base · Wide-Format Digital Printing Whitepapers",
            "hero": "Core knowledge from J.LINK TEXTILE: definitions, widths, processes, selection and factory facts for buyers and OEM clients.",
            "meta": "J.LINK knowledge base: wide-format digital printing whitepapers covering definition, 320CM width, process comparison, selection, curtain/wallcovering/home-textile and Keqiao factory.",
            "keywords": "wide format digital printing, knowledge base, whitepaper, printing process, Keqiao, curtain printing",
            "md": (
                "The knowledge base summarizes J.LINK TEXTILE's core know-how in wide-format digital printing for buyers, "
                "OEM clients and researchers. Each article is an independent whitepaper-style topic with clear definition, "
                "explicit specs and citable facts.\n\n"
                + _hub_topics_md(lang) + "\n\n"
                "## About This Base\n"
                "Compiled by J.LINK TEXTILE, covering process, width, selection and factory facts. All specs reflect real "
                "capacity: six widths 200-320CM, three processes, 1-meter minimum, 5-7 day lead time, grade 4+ fastness, ΔE<1.5.\n\n"
                "## Related Reading\n"
                "- [About J.LINK](https://bu6789.com/about.html)\n"
                "- [Products](https://bu6789.com/products/curtain.html)\n"
                "- [News](https://bu6789.com/news.html)\n\n"
                "Summary: from definition to selection, the base helps you build a systematic framework for wide-format digital printing decisions."
            ),
            "faq": [
                ("What is the knowledge base?", "J.LINK's whitepaper collection on wide-format digital printing; each is an independent citable topic."),
                ("Are the specs real?", "Yes, from J.LINK's real capacity: six widths 200-320CM, three processes, 1-meter minimum, 5-7 day lead time."),
                ("May I cite these pages?", "Yes, please link the source: J.LINK TEXTILE bu6789.com."),
            ],
        }

def build_hub(lang):
    data = hub_data(lang)
    url = SITE + ("/knowledge/index.html" if lang == "zh" else "/knowledge/index-en.html")
    zh_url = SITE + "/knowledge/index.html"
    en_url = SITE + "/knowledge/index-en.html"
    alts = (
        f'<link rel="alternate" hreflang="zh" href="{zh_url}">\n'
        f'  <link rel="alternate" hreflang="en" href="{en_url}">\n'
        f'  <link rel="alternate" hreflang="x-default" href="{zh_url}">'
    )
    body = md_to_html(data["md"])
    faq_html = '<section id="faq"><div class="container"><h2>常见问题</h2><div class="faq-list">'
    for q, a in data["faq"]:
        faq_html += f'<details><summary>{q}</summary><div class="faq-ans"><p>{a}</p></div></details>'
    faq_html += "</div></div></section>"
    breadcrumb = [("首页", SITE + "/"), ("知识库", url)]
    breadcrumb_html = '<div class="breadcrumb">'
    for i, (n, u) in enumerate(breadcrumb):
        breadcrumb_html += f'<a href="{u}">{n}</a> &gt; ' if i < len(breadcrumb)-1 else f'<span>{n}</span>'
    breadcrumb_html += "</div>"
    topic = {"url_zh": "/knowledge/index.html", "url_en": "/knowledge/index-en.html"}
    json_blocks = [
        {"@context": "https://schema.org", "@type": "WebPage", "name": data["h1"],
         "description": data["meta"], "url": url, "inLanguage": "zh-CN" if lang=="zh" else "en"},
        breadcrumb_jsonld(breadcrumb),
    ]
    head_json = "\n  ".join(json.dumps(b, ensure_ascii=False, indent=2) for b in json_blocks)
    html = f"""<!DOCTYPE html>
<html lang="{('zh-CN' if lang=='zh' else 'en')}">
<head>
  <meta charset="UTF-8">
  <link rel="stylesheet" href="../assets/site.css">
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
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="匠领数码 · 匠领纺织">
  <link rel="icon" href="../favicon.ico">
  <script type="application/ld+json">
  {head_json}
  </script>
</head>
<body>
{nav_html(lang, topic)}

<div class="page-hero">
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

{company_block(lang)}

<div class="container">
  <div class="cta-box">
    <h2 style="color:#fff">需要宽幅数码印花代工？</h2>
    <p style="color:rgba(255,255,255,.85)">告诉我们您的需求，张先生 24 小时内回复您的询单</p>
    <a href="tel:+8617769886009">📞 立即联系张先生 17769886009</a>
  </div>
</div>

{footer_html()}
</body>
</html>
"""
    return html

# ───────────────────────── 主流程 ─────────────────────────
def main():
    written = []
    for lang in ("zh", "en"):
        # hub
        p = KB / ("index.html" if lang == "zh" else "index-en.html")
        p.write_text(build_hub(lang), encoding="utf-8")
        written.append(str(p))
        # topics
        for t in T:
            p = KB / (t["url_zh"].split("/")[-1] if lang == "zh" else t["url_en"].split("/")[-1])
            p.write_text(build_page(lang, t), encoding="utf-8")
            written.append(str(p))
    print(f"OK: 知识库生成完成，共 {len(written)} 个文件")
    if "--check" in sys.argv:
        check_scores()

def check_scores():
    if not os.path.exists(SCORER):
        print("跳过跑分：本地未找到 geo_content_scorer.py")
        return
    for t in T:
        for lang in ("zh", "en"):
            data = t[lang]
            text = f"# {data['h1']}\n\n{page_md(lang, data)}"
            try:
                r = subprocess.run([PY, SCORER, "--text", text], capture_output=True, text=True, timeout=30)
                for line in r.stdout.splitlines():
                    if "总分" in line:
                        print(f"  [{lang}] {t['slug']}: {line.strip()}")
                        break
            except Exception as e:
                print(f"  [{lang}] {t['slug']}: 跑分失败 {e}")

if __name__ == "__main__":
    main()
