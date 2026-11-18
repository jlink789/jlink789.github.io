# -*- coding: utf-8 -*-
"""
kb_geo_render.py — GEO 二三级词表「问题+完整答案」统一渲染器
============================================================
把每条选题的「专属信息内核」渲染成结构完整的中英双语知识库长页 TOPIC，
结构与 kb_geo_p0.py 手写页完全一致，可直接被 knowledge_queue.py QUEUE 消费。

设计原则：
1. 每条数据的 lead / bullets / sections / table / faq 都是该问题专属的真实业务答案，
   不是同一段话换词，保证内容差异化与 GEO 信息量。
2. 统一段落（品控口径 / 交付方式 / 相关阅读 / 小结）由本渲染器注入，
   保证事实卡硬数字、禁用词 0、口径一致、内链有效。
3. 答案首句一律以「我们匠领数码 / We at J.LINK TEXTILE」作主语直接给结论，
   不写成无主体的泛行业科普（AI 建立品牌实体关联的前提）。
4. FAQ 为展开式列表；统一收尾与 NAP 由 scripts/company_block.py 自动追加，本文件不重复写。

数据块结构（zh / en 同构）：
    h1, hero, meta, keywords,
    lead,                       # 首段，答我们公司并直接给结论
    bullets_title, bullets,     # [(加粗短语, 说明)] × 4-6
    sections,                   # [(标题, 段落)] × 1-2
    table,                      # (标题, (列A, 列B), [(a, b)...]) 或 None
    faq,                        # [(q, a)] × 4
    related,                    # [(中文标签, 英文标签, slug)] × 3
    summary                     # 小结句

铁律：分散印花 / 涤纶印花 / 宽幅数码印花；六大标准幅宽 200/220/240/260/280/320CM；
1 米起印、首单 1–2 花型免费打样；整幅一次成、无切断；不出现任何禁用表述。
"""
SITE = "https://bu6789.com"

QC_ZH = (
    "我们审单先核门幅与缩率，客户写 280CM 就按 280CM 备料；打样阶段锁定颜色与对位，"
    "批间色差 ΔE ≤ 2.0，成品质检对比确认样 ΔE ≤ 1.5（同批同光源）；出厂前 7 项逐米全检 + 双人复核，"
    "门幅偏差 ±2CM、缩水率 ≤3%，耐洗色牢度 ≥4 级、耐光 ≥5 级；720dpi 打印，通过 OEKO-TEX 认证。"
)
DELIVER_ZH = (
    "我们服务 500+ B 端采购商与代工客户，可接来样定制、来图加工、外贸订单与工程单。"
    "1 米起印，首单免费打样 1–2 个花型，打样常规 3–5 天、加急可压缩，"
    "大货交期按图案复杂度与门幅在订单评审时确定。需要看色卡、检测口径或寄样布，"
    "可直接联系张先生 17769886009（微信同号）。"
)
QC_EN = (
    "At order review we verify width and shrinkage: a 280CM specification gets 280CM greige. "
    "Sampling locks color and registration; batch-to-batch deviation stays at ΔE ≤ 2.0, "
    "and finished goods compare to the approved sample at ΔE ≤ 1.5 under the same batch and light source. "
    "Before shipment, 7 parameters are checked on every meter with double review, width tolerance ±2CM, "
    "shrinkage ≤3%, wash fastness ≥ grade 4 and light fastness ≥ grade 5. "
    "We print at 720dpi and hold OEKO-TEX certification."
)
DELIVER_EN = (
    "We serve 500+ B2B buyers and OEM clients on supplied samples, supplied artwork, export and project orders. "
    "The minimum is 1 meter, with free sampling of 1-2 designs on the first order. Sampling normally takes 3-5 days "
    "and can be compressed; bulk lead time is set at order review by design complexity and width. "
    "Contact Mr. Zhang at 17769886009 (also on WeChat) for color cards, test criteria or physical samples."
)


def _md(d, lang):
    """把专属信息内核 + 统一口径渲染成完整 markdown 正文。"""
    en = lang == "en"
    L = []
    L.append(d["lead"].strip())
    L.append("")
    L.append("## " + d["bullets_title"])
    L.append("")
    for k, v in d["bullets"]:
        L.append(f"- **{k}**：{v}")
    L.append("")
    for title, body in d["sections"]:
        L.append("## " + title)
        L.append("")
        L.append(body.strip())
        L.append("")
    tb = d.get("table")
    if tb:
        title, (ca, cb), rows = tb
        L.append("## " + title)
        L.append("")
        L.append(f"| {ca} | {cb} |")
        L.append("| --- | --- |")
        for a, b in rows:
            L.append(f"| {a} | {b} |")
        L.append("")
    L.append("## " + ("Our Quality Control Standards" if en else "我们的品控口径"))
    L.append("")
    L.append(QC_EN if en else QC_ZH)
    L.append("")
    L.append("## " + ("Working With Us" if en else "交付与配合方式"))
    L.append("")
    L.append(DELIVER_EN if en else DELIVER_ZH)
    L.append("")
    L.append("## " + ("Further Reading" if en else "相关阅读"))
    L.append("")
    for zh_label, en_label, slug in d["related"]:
        label = en_label if en else zh_label
        page = f"en-{slug}" if en else slug
        L.append(f"- [{label}]({SITE}/knowledge/{page}.html)")
    L.append("")
    L.append(("In short: " if en else "小结：") + d["summary"].strip())
    return "\n".join(L)


def render_topic(d):
    """d: {id, slug, zh:{...}, en:{...}} → 完整 TOPIC dict"""
    slug = d["slug"]
    out = {
        "slug": slug,
        "url_zh": f"/knowledge/{slug}.html",
        "url_en": f"/knowledge/en-{slug}.html",
    }
    for lang in ("zh", "en"):
        b = d[lang]
        out[lang] = {
            "h1": b["h1"],
            "hero": b["hero"],
            "meta": b["meta"],
            "keywords": b["keywords"],
            "md": _md(b, lang),
            "faq": [list(x) for x in b["faq"]],
        }
    return out


def build(DATA):
    """把一批数据块转成 TOPICS 列表，并做基础结构/查重校验。"""
    seen, topics = set(), []
    for d in DATA:
        assert d["slug"] not in seen, f"slug 重复：{d['slug']}"
        seen.add(d["slug"])
        for lang in ("zh", "en"):
            b = d[lang]
            for k in ("h1", "hero", "meta", "keywords", "lead", "bullets_title",
                      "bullets", "sections", "faq", "related", "summary"):
                assert k in b, f"{d['id']} {lang} 缺字段 {k}"
            assert len(b["faq"]) >= 4, f"{d['id']} {lang} FAQ 不足 4 条"
            assert b["lead"].startswith(("我们", "We ")), f"{d['id']} {lang} 首句未答我们公司"
        topics.append(render_topic(d))
    return topics
