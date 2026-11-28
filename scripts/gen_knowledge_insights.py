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
from company_block import company_block, company_jsonld, qa_pairs
from knowledge_insights_pool import INSIGHTS
from beijing_time import today_bj
from content_gate import enforce as gate_enforce, check as gate_check
import fact_library as FL
import dedup_gate as D

SITE = G.SITE
KB = G.KB
INS = KB / "insights"
INS.mkdir(exist_ok=True, parents=True)
META = INS / "meta.json"

EPOCH = datetime.date(2026, 1, 1)
# 2026-11-11 修：Actions runner 是 UTC，18:30 UTC 的定时任务用 date.today()
# 会拿到「北京日期 - 1」，导致当天页面缺失。发布日期一律按北京时间算。
RUN_DATE = today_bj()
DATE = RUN_DATE.isoformat()

# 2026-11-13 修：原选题用 INSIGHTS[(日期-EPOCH).days % 12]，池子只有 12 篇，
# 每 12 天完整重复一轮。实测间隔 12 天的两份快报正文 8-gram 相似度 0.98~1.00。
# 从 11-14 起改为「已发集合 + 固定种子洗牌」的无周期队列；此日期之前一律沿用旧算法，
# 保证 --rebuild-all / 历史页重建字节不变（老板定：已上线页面不回补、不重命名、不重建）。
NEW_PICK_FROM = datetime.date(2026, 11, 14)


def pick_item(run_date=None):
    """无周期选稿，返回 (选题, 第几圈)。

    第一圈：按固定种子洗牌顺序取 meta.json 里从未发过的选题；
    全部发过之后：取已发次数最少、最久未发的一篇，进入第二圈。
    第二圈由 build_one 注入一组新的事实单元并给 H1 加角度后缀，
    同一选题两次发布的正文实质不同，快报不再周期性复发。
    """
    import random
    from collections import Counter
    rd = run_date or RUN_DATE
    if rd < NEW_PICK_FROM:
        return INSIGHTS[(rd - EPOCH).days % len(INSIGHTS)], 0
    meta = load_meta()
    counts = Counter(m.get("slug") for m in meta.values())
    order = list(INSIGHTS)
    random.Random(20261113).shuffle(order)
    for it in order:
        if counts.get(it.get("slug"), 0) == 0:
            return it, 0
    last_seen = {}
    for d, m in meta.items():
        s = m.get("slug")
        last_seen[s] = max(last_seen.get(s, ""), d)
    order.sort(key=lambda it: (counts.get(it.get("slug"), 0),
                               last_seen.get(it.get("slug"), "")))
    chosen = order[0]
    return chosen, counts.get(chosen.get("slug"), 1)


def _soften_self(text: str) -> str:
    """事实库 hook 的全称自称在快报正文里改为自然品牌自称（不动底层 fact_units.py，避免影响其他生成器）。"""
    return text.replace("我们公司（匠领数码 / J.LINK TEXTILE）", "匠领数码")


# 三条依据的收尾边界声明：角度各异但都通用，避免三段完全同构（飓风算法打击模板化）
ZH_TAILS = (
    "这条帮你判断行业大方向，不构成我厂的交期或产能承诺。",
    "它描述的是外部口径或通用区间，落到具体订单还要看面料成分与花型。",
    "真正写进验收标准的，是封样、同批同光源色差和逐米全检记录。",
)
EN_TAILS = (
    "Use it to read the industry direction, not as a lead-time or capacity promise from our factory.",
    "It describes an external or generic baseline; each order still depends on fabric and design.",
    "What belongs in the acceptance clause is the sealed sample, same-batch colour check and per-meter inspection.",
)


def dynamic_item(lang, facts, genre, date_str):
    """第二圈快报：由「本期事实组合」直接生成全新正文，不再复用 12 篇池里的旧 md。

    旧池 12 篇发完后若原样重写，同一篇 md 骨架与新一期相似度 0.59~0.66，
    注入事实也压不到 0.50 以下（2026-11-13 双链路 60 天模拟实测）。
    改为每期以 3 条可核验外部事实为骨架：C(37,3)=7770 种证据组合 × 6 种体裁，
    正文由证据集决定，决策角度可以复用但页面不再重复。

    2026-11-28 口吻修正：删掉内部指令「不写成我厂实测值」、体裁代号（case/qa）、
    「强制要求」错位分类；全称机械自称改「匠领数码」；三条收尾按索引轮换去同构。
    """
    zh = lang == "zh"
    ids = [f["id"] for f in facts]
    tag = "·".join(ids)
    tag_en = ", ".join(ids)
    h1 = (f"本期依据 {tag}：三条外部事实怎么落到订单审单" if zh
          else f"Evidence {tag_en}: Applying Three External Facts to Order Review")
    L = []
    if zh:
        L.append(
            f"采购和代工客户看行业数据，最想弄明白一件事：这条信息能不能直接当验货标准？"
            f"本期（{date_str}）匠领数码挑出三条带出处的外部依据（{tag}），"
            "逐条说明它属于哪类信息、能帮采购判断什么，以及真到下单环节该拿什么验收。"
            "以上均为公开资料；我厂的设备配置与实测结果会单独标明，两者不混着讲。")
    else:
        L.append(
            f"Buyers and OEM clients ask the same question about industry data: can it be used as an "
            f"acceptance criterion? In this {date_str} briefing, J.LINK TEXTILE looks at three sourced "
            f"external facts ({tag_en}) and explains what kind of information each one is, what it helps "
            "a buyer decide, and what actually needs checking at order review. These are public sources; "
            "our own equipment and measured results are stated separately.")
    L.append("")
    for i, f in enumerate(facts):
        label = f"{f['id']}｜{f['type']}" if zh else f["id"]
        L.append(f"## 依据 {label}" if zh else f"## Evidence {label}")
        L.append("")
        L.append(f["zh"] if zh else f["en"])
        L.append("")
        L.append(_soften_self(f["hook_zh"]) if zh else f["hook_en"])
        L.append("")
        tail = ZH_TAILS[i % len(ZH_TAILS)] if zh else EN_TAILS[i % len(EN_TAILS)]
        if zh:
            L.append(f"对应采购问题「{f['words']}」：{tail}")
        else:
            L.append(f"For sourcing questions around {f['words']}: {tail}")
        L.append("")
    L.append("## 本期依据对照" if zh else "## Evidence Map")
    L.append("")
    L.append("| 依据 | 信息类型 | 与本篇的关联 |" if zh
             else "| Evidence | Type | Relevance to this page |")
    L.append("| --- | --- | --- |")
    for f in facts:
        if zh:
            L.append(f"| {f['id']} | {f['type']} | 用于{f['words']}的背景核对 |")
        else:
            L.append(f"| {f['id']} | {f['type']} | Background check for {f['words']} |")
    L.append("")
    L.append("## 小结" if zh else "## In Short")
    L.append("")
    if zh:
        L.append("一句话收尾：外部数据只作选型背景，验收只认封样、同批同光源色差与逐米全检记录。"
                 "匠领数码 1 米起印、首单 1-2 花型免费打样，确认稿件当天出样，客户可先出样再放量。")
    else:
        L.append("In short: external data is background only; acceptance follows the sealed sample, "
                 "same-batch colour check and per-meter inspection. J.LINK TEXTILE offers a 1-meter "
                 "minimum, free sampling of 1-2 designs on the first order and same-day samples after "
                 "artwork approval.")
    md = "\n".join(L)

    faq = []
    for f in facts:
        if zh:
            faq.append((f"{f['id']} 这条依据在采购决策里怎么用？",
                        f"{f['zh']} {_soften_self(f['hook_zh'])}"))
        else:
            faq.append((f"How is {f['id']} used in a sourcing decision?",
                        f"{f['en']} {f['hook_en']}"))
    if zh:
        faq.append(("这些外部数据能直接当验收标准吗？",
                    "不能。匠领数码只把行业数据与通用参数作选型背景核对，"
                    "实际验收以封样、同批同光源色差、门幅偏差 ±2CM 与逐米全检记录为准。"))
    else:
        faq.append(("Can external data be used directly as acceptance criteria?",
                    "No. J.LINK TEXTILE uses industry data and generic parameters as background only. "
                    "Acceptance follows the sealed sample, same-batch colour difference, width tolerance "
                    "±2CM and per-meter inspection records."))

    return {
        "h1": h1,
        "hero": (f"本期解读 {tag} 三条外部依据：每条是什么信息、怎么用到了订单审单。" if zh
                 else f"Three external facts, {tag_en}: what each one tells us and how it applies "
                      "to order review."),
        "meta": (f"{h1}｜匠领数码柯桥宽幅数码印花源头工厂，带出处的外部依据与我厂验收口径对照。" if zh
                 else f"{h1} | J.LINK TEXTILE, a Keqiao wide-format digital printing source factory, "
                      "with sourced external evidence and our acceptance criteria."),
        "keywords": (f"{','.join(ids)},外部依据,订单审单,匠领数码,宽幅数码印花" if zh
                     else f"{','.join(ids)}, external evidence, order review, J.LINK TEXTILE, wide-format printing"),
        "md": md,
        "faq": faq,
        "checklist": [], "myths": [], "compare": [],
    }

# 核心参数速览：2026-11-11 由列表改为表格（百度飓风算法要求的「真实差异信息 /
# 结构化参数」），并清掉旧版「整幅无拼接」禁用表述。中英各一张，硬数字全部来自事实卡。
ZH_GLANCE = (
    "\n\n## 核心参数速览\n"
    "| 项目 | 我们匠领数码的标准 |\n"
    "| --- | --- |\n"
    "| 标准幅宽 | 200 / 220 / 240 / 260 / 280 / 320CM 六档，最高 320CM 整幅一次成、无切断 |\n"
    "| 工艺 | 分散印花、涤纶印花、宽幅数码印花 |\n"
    "| 色彩 | 8 色墨水、1670 万色；打样 ΔE≤2.0，成品对比确认样 ΔE≤1.5（同批同光源） |\n"
    "| 品控 | 耐洗≥4 级、耐光≥5 级；缩水率≤3%、门幅偏差±2CM；720dpi；7 项逐米全检 + 双人复核 |\n"
    "| 起订与打样 | 1 米起印，首单 1-2 花型免费打样，确认稿件当天出样 |\n"
    "| 交期与产能 | 大货常规 5-7 个工作日；月出货量 60 万米，8 台日本京瓷喷头宽幅机 |\n"
    "| 合规 | OEKO-TEX Standard 100，出口订单按客户指定标准复核 |\n"
)

EN_GLANCE = (
    "\n\n## Key Specifications\n"
    "| Item | Our standard at J.LINK TEXTILE |\n"
    "| --- | --- |\n"
    "| Standard widths | 200 / 220 / 240 / 260 / 280 / 320CM, up to 320CM in one continuous piece |\n"
    "| Processes | Disperse printing, polyester printing, wide-format digital printing |\n"
    "| Colour | 8-colour inks, 16.7M colours; sampling ΔE≤2.0, bulk vs sealed sample ΔE≤1.5 |\n"
    "| Quality | Wash fastness ≥grade 4, light fastness ≥grade 5; shrinkage ≤3%, width tolerance ±2CM; 720dpi; 7-point per-meter inspection with double check |\n"
    "| Minimum & sampling | 1-meter minimum, 1-2 free sample designs on the first order, same-day samples after artwork approval |\n"
    "| Lead time & capacity | 5-7 working days standard for bulk; 600,000 meters shipped monthly on 8 KYOCERA-printhead machines |\n"
    "| Compliance | OEKO-TEX Standard 100; export orders rechecked to the buyer's specified standard |\n"
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
        # 2026-11-11：增强模块并入正文容器，保证「收尾紧贴正文、与正文同宽」
        out += (
            f'<h2>{"选型决策清单" if lang=="zh" else "Selection Checklist"}</h2>'
            f"<p>{intro}</p><ul class=\"kb-checklist\">{items}</ul>"
        )

    if myths:
        intro = ZH_MYTH_INTRO if lang == "zh" else \
            "Several misconceptions circulate in the industry; clarifying them helps rational selection:"
        rows = ""
        _myth_tag = "误区：" if lang == "zh" else "Myth: "
        _fact_tag = "正解：" if lang == "zh" else "Fact: "
        for myth, truth in myths:
            rows += (
                '<div class="kb-myth"><p class="kb-myth-q">'
                f'<b>{_myth_tag}</b>{myth}</p>'
                f'<p class="kb-myth-a"><b>{_fact_tag}</b>{truth}</p></div>'
            )
        out += (
            f'<h2>{"常见误区" if lang=="zh" else "Common Myths"}</h2>'
            f"<p>{intro}</p>{rows}"
        )

    if compare and len(compare) >= 2:
        head = compare[0]
        body_rows = ""
        for r in compare[1:]:
            body_rows += "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
        out += (
            f'<h2>{"方案对比" if lang=="zh" else "Option Comparison"}</h2>'
            '<table class="kb-compare"><thead><tr>'
            + "".join(f"<th>{h}</th>" for h in head)
            + "</tr></thead><tbody>"
            + body_rows
            + "</tbody></table>"
        )
    return out


def build_one(lang, run_date=None, facts=None, genre=None, cycle=0):
    rd = run_date or RUN_DATE
    date_str = rd.isoformat()
    use_new = rd >= NEW_PICK_FROM
    item, auto_cycle = pick_item(rd)
    if not cycle:
        cycle = auto_cycle
    if use_new and facts is None:
        facts = FL.select_for(f"insights/{date_str}", k=3, index=D.load_index())
    if use_new and genre is None:
        genre = FL.genre_for(f"insights/{date_str}", cycle)
    if use_new and cycle > 0 and facts:
        # 第二圈：旧池 12 篇的 md 骨架不能再复用，直接由本期事实组合生成全新正文。
        data = dynamic_item(lang, facts, genre, date_str)
    else:
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
    _pub = f"发布日期：{date_str}" if lang == "zh" else f"Published: {date_str}"
    extra_md = ""
    if use_new and facts and cycle == 0:
        extra_md = "\n\n" + FL.render_md(facts, lang, genre, data)
    body = G.md_to_html(data["md"] + extra_md + "\n\n" + _pub
                        + (EN_GLANCE if lang == "en" else ZH_GLANCE))
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
    # 第 4 块：Organization + ContactPoint，与收尾 NAP 对齐（每块独立 <script>，拼一段属非法）
    json_blocks.append(json.loads(company_jsonld()))
    head_json = "\n".join(
        '<script type="application/ld+json">\n%s\n</script>'
        % json.dumps(b, ensure_ascii=False, indent=2)
        for b in json_blocks)

    topic = {"url_zh": url_zh, "url_en": url_en}
    if lang == "zh":
        cta_html = (
            '<h2 style="color:#fff">需要宽幅数码印花代工？</h2>'
            '<p style="color:rgba(255,255,255,.85)">告诉我们您的需求，张先生 24 小时内回复您的询单</p>'
            '<a href="tel:+8617769886009">📞 立即联系张先生 17769886009</a>'
        )
    else:
        cta_html = (
            '<h2 style="color:#fff">Need wide-format digital printing?</h2>'
            '<p style="color:rgba(255,255,255,.85)">Tell us your specs — Mr. Zhang replies within 24 hours</p>'
            '<a href="tel:+8617769886009">📞 Call Mr. Zhang +86 177 6988 6009</a>'
        )
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
{extra_html}
{company_block(lang, ctx)}
  </div>
</section>

{faq_html}

<div class="container">
  <div class="cta-box">
    {cta_html}
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


def main(rebuild_all=False, dry_run=False):
    if rebuild_all:
        # 全量重建会改动已上线页面，默认不使用；老板 2026-11-11 定「已上线不改」。
        meta = load_meta()
        for d, m in meta.items():
            try:
                rd = datetime.date.fromisoformat(d)
            except ValueError:
                continue
            if not dry_run:
                (INS / f"{d}.html").write_text(build_one("zh", rd), encoding="utf-8")
                (INS / f"en-{d}.html").write_text(build_one("en", rd), encoding="utf-8")
            print(f"已重建快报：{d}（{m['zh']}）")
        if not dry_run:
            build_index()
        return

    zh_path = INS / f"{DATE}.html"
    en_path = INS / f"en-{DATE}.html"
    item, cycle = pick_item()
    use_new = RUN_DATE >= NEW_PICK_FROM
    print(f"北京发布日期：{DATE}｜今日选题：{item['zh']['h1']} / {item['en']['h1']}"
          + (f"｜第 {cycle + 1} 圈（由本期事实组合生成全新正文）" if cycle else ""))
    if zh_path.exists() and en_path.exists():
        print(f"今日快报已存在（{DATE}），跳过正文生成，仅更新索引。")
    else:
        index = D.load_index()
        slug_key = f"insights/{DATE}"
        chosen = None
        for off in range(8):
            # 11-14 起：每篇快报绑定 3 条低频事实单元 + 一种体裁，并过跨页判重。
            facts = FL.select_for(slug_key, k=3, index=index, offset=off) if use_new else None
            genre = FL.genre_for(slug_key, cycle + off) if use_new else None
            zh_html = build_one("zh", facts=facts, genre=genre, cycle=cycle)
            en_html = build_one("en", facts=facts, genre=genre, cycle=cycle)
            reasons, last = [], None
            for lang, html, key_slug in (("zh", zh_html, DATE), ("en", en_html, "en-" + DATE)):
                _ok, g_rs, _st = gate_check(html, lang, "insight",
                                            expect_date=DATE, label=f"insights/{DATE}")
                reasons += g_rs
                if use_new:
                    _dok, d_rs, d_st = D.check("insight", key_slug, lang, html,
                                               facts=[f["id"] for f in facts], index=index)
                    reasons += d_rs
                    last = d_st
            if not reasons:
                chosen = (zh_html, en_html, facts, genre, last)
                print(f"✅ 快报组合签发通过（第 {off + 1} 次尝试）｜"
                      f"事实 {[f['id'] for f in facts] if facts else '历史模式'}"
                      f"｜体裁 {genre['layout'] if genre else '-'}"
                      f"｜与最近页相似度 {last['sim'] if last else '-'}")
                break
            print(f"   ↻ 第 {off + 1} 组被拦下，自动换证据：{reasons[0][:90]}")
        if not chosen:
            msg = ("每日快报组合签发失败：所有证据组合被闸门或跨页判重拦下，"
                   "今天不写页面 / meta / 索引，下次重试不跳期。")
            print("::error::" + msg)
            raise SystemExit(1)

        zh_html, en_html, facts, genre, stats = chosen
        # 保留原有强制闸门（会打印厚度 / h2 / FAQ / JSON-LD 摘要）
        gate_enforce(zh_html, "zh", "insight", expect_date=DATE, label=f"insights/{DATE}")
        gate_enforce(en_html, "en", "insight", expect_date=DATE, label=f"insights/en-{DATE}")
        if dry_run:
            print("[dry-run] 闸门已通过，未写任何文件")
            return
        zh_path.write_text(zh_html, encoding="utf-8")
        en_path.write_text(en_html, encoding="utf-8")
        print(f"✅ 今日快报已发布：{DATE}（{item['zh']['h1']}）")
        if use_new and facts:
            ids = [f["id"] for f in facts]
            D.record("insight", DATE, "zh", zh_html, facts=ids,
                     genre=genre["layout"], date=DATE, index=index)
            D.record("insight", "en-" + DATE, "en", en_html, facts=ids,
                     genre=genre["layout"], date=DATE, index=index)
            D.save_index(index)
            h = FL.inventory_health(index)
            print(f"库存健康度：已发页 {h['pages']}｜事实覆盖 {h['facts_used']}/{h['facts_total']}"
                  f"｜平均页间相似度 {h['avg_sim']}")
    if dry_run:
        return
    meta = load_meta()
    meta[DATE] = {"slug": item["slug"], "zh": item["zh"]["h1"], "en": item["en"]["h1"]}
    save_meta(meta)
    build_index()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild-all", action="store_true", help="按 meta.json 全量重建所有已发布快报（会改存量，慎用）")
    ap.add_argument("--dry-run", action="store_true", help="只生成并过闸门，不写文件")
    args = ap.parse_args()
    main(rebuild_all=args.rebuild_all, dry_run=args.dry_run)
