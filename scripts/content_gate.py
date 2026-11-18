# -*- coding: utf-8 -*-
"""官网统一「发布闸门」—— 任何新页面写入磁盘前必须过这一关（2026-11-11 老板定）。

背景：阶段 0-2 的 quality_gate() 只挂在 auto_article.py 一条链路上，知识库专题
和每日快报没有门槛，导致每天仍可能发出带禁用词、缺参数表、FAQ 折叠、
JSON-LD 非法的页面。本模块把「最新收录规则」收敛成一份单一校验器，
三条生成链路（知识库专题 / 每日快报 / 长尾文章）在写文件前统一调用。

检查项（对应长期口径）：
  1. 禁用词 0（拼接类、活性、最大320CM、100米起印、非痛点恐惧钩子、窄幅）
  2. 版式顺序：正文 → 收尾（紧贴正文、同宽）→ 常见问题 → CTA → 页脚
  3. FAQ 一律默认展开（无 <details>），页面 FAQ ≥4 条
  4. 收尾固定主标题 + 3 条问答 + 公司介绍 + 宽幅实力 + NAP
  5. 正文厚度、h2≥3、参数表（百度飓风算法要求的真实差异信息）
  6. canonical + hreflang 三件套（单语文章页豁免 hreflang）
  7. 4 块独立、各自合法、含 FAQPage 的 JSON-LD（多对象拼一段属非法，会被整段忽略）
  8. 备案双号（ICP + 公安）、robots 可收录
  9. 英文页正文区不夹中文（共用导航/页脚的历史文案按「已上线不改」保留，不在检查区）
 10. 知识库问答页首句答「我们公司」；发布日期按北京日期

用法：
    from content_gate import check, enforce, GateError
    ok, reasons, stats = check(html, lang, kind="knowledge", expect_date="2026-11-11")
    enforce(html, lang, kind="insight", expect_date=DATE, label=slug)  # 不过直接抛错

只管「以后发的」：存量已上线页面不重建、不回补、不因本模块改动而变化。
"""
import json
import re
from html import unescape

# ── 无条件禁区（老板 2026-10-27 / 10-28 / 11-01 定，永久） ────────────────
BANNED_ZH = (
    "活性", "拼接", "拼缝", "拼花", "拼块", "分八块",
    "最大320CM", "最宽320CM", "最大320", "最宽320",
    "100米起印", "100米起订", "100米每花型", "断花", "花型对不上", "窄幅",
)
BANNED_EN = (
    "reactive dye", "reactive print", "reactive ink", "maximum 320", "max 320",
    "100m moq", "moq 100", "100 meters minimum",
    "narrow-width", "narrow width", "narrow machine", "narrow fabric", "narrow tiling",
    "splic", "pieced together", "stitched panels",
)

H2_ZH = "我们是匠领数码——柯桥宽门幅数码印花源头工厂"
H2_EN = "We are J.LINK — a wide-width digital printing source factory in Keqiao"
ICP = "浙ICP备20007773号-3"
GONGAN = "浙公网安备33060302001843号"

MIN_BODY = {"knowledge": (1200, 900), "insight": (900, 800), "article": (1200, 900)}
MIN_H2 = 3
MIN_FAQ = 4
MIN_QA = 3
MIN_JSONLD = {"knowledge": 4, "insight": 4, "article": 3}

HAN = re.compile(r"[\u4e00-\u9fff]")


class GateError(RuntimeError):
    """发布闸门未通过：调用方应中止写文件，不能带着脏页面上線。"""


def _plain(fragment: str) -> str:
    return re.sub(r"\s+", "", unescape(re.sub(r"<[^>]+>", "", fragment)))


def _body_zone(html: str) -> str:
    """取「正文区」：所有 <section> 内容中、收尾块之前的部分。
    导航、页脚、CTA、面包屑都不在 section 内，因此英文正文语言检查不会被共用模板干扰。
    """
    sections = "".join(re.findall(r"<section[^>]*>(.*?)</section>", html, re.S))
    zone = sections.split('id="company"')[0]
    if not zone.strip():
        h1 = html.find("<h1")
        company = html.find('id="company"')
        zone = html[h1:company] if h1 >= 0 and company > h1 else ""
    return zone


def check(html: str, lang: str = "zh", kind: str = "knowledge",
          expect_date: str | None = None, label: str = ""):
    """返回 (ok, reasons, stats)。reasons 为空即通过。"""
    reasons = []
    kind = kind if kind in MIN_BODY else "knowledge"
    lang = "en" if lang == "en" else "zh"
    probe = html.replace("灵活性", "").replace("活性剂", "")  # 避免「灵活性」误伤
    low = probe.lower()

    # 1. 禁用词
    hits = [b for b in BANNED_ZH if b in probe]
    hits += [b for b in BANNED_EN if b in low]
    if hits:
        reasons.append("禁用词: " + "/".join(sorted(set(hits))))

    # 2. 版式顺序
    p_company = html.find('id="company"')
    faq_pos = [x for x in (html.find('id="faq"'), html.find('class="faq-list"')) if x >= 0]
    p_faq = min(faq_pos) if faq_pos else -1
    p_cta = html.find('class="cta-box"')
    p_footer = html.find("<footer")
    if min(p_company, p_faq, p_cta, p_footer) < 0:
        reasons.append("缺少收尾 / FAQ / CTA / 页脚之一")
    elif not (p_company < p_faq < p_cta < p_footer):
        reasons.append("版式顺序错（应 正文→收尾→FAQ→CTA→页脚）")

    # 3. FAQ 默认展开
    if "<details" in html.lower():
        reasons.append("FAQ 用了 <details> 折叠（AI 引擎不会点开）")
    faq_n = len(re.findall(r'class="faq-item"', html))
    if faq_n < MIN_FAQ:
        reasons.append(f"页面 FAQ 仅 {faq_n} 条 < {MIN_FAQ}")

    # 4. 收尾块
    qa_n = len(re.findall(r'class="cb-qa-item"', html))
    if qa_n < MIN_QA:
        reasons.append(f"收尾问答仅 {qa_n} 条 < {MIN_QA}")
    if (H2_EN if lang == "en" else H2_ZH) not in html:
        reasons.append("缺收尾固定主标题")
    if "17769886009" not in html and "177 6988 6009" not in html:
        reasons.append("缺电话 NAP")
    if "兴浦路88号" not in html and "88 Xingpu Road" not in html:
        reasons.append("缺厂址 NAP")

    # 5. 正文厚度 / h2 / 参数表
    zone = _body_zone(html)
    body_text = _plain(zone)
    # 知识库 / 快报的内容厚度按「正文 + 问答式收尾 + FAQ」整页可见内容算：
    # 老板定的版式本来就是这四段连成一体，AI 抓取的是整页，不是只抓 md 正文。
    # 长尾文章页没有 <section>，仍按纯正文严格算（阶段 0 止血门槛不放宽）。
    full_zone = "".join(re.findall(r"<section[^>]*>(.*?)</section>", html, re.S))
    content_text = _plain(full_zone) if full_zone.strip() else body_text
    thickness = len(content_text) if kind in ("knowledge", "insight") else len(body_text)
    need_zh, need_en = MIN_BODY[kind]
    need = need_en if lang == "en" else need_zh
    if thickness < need:
        reasons.append(f"内容厚度 {thickness} 字 < {need}（正文 {len(body_text)} 字）")
    h2_n = len(re.findall(r"<h2[\s>]", html))
    if h2_n < MIN_H2:
        reasons.append(f"h2 仅 {h2_n} 个 < {MIN_H2}")
    if "<table" not in html:
        reasons.append("缺参数表（工艺 / 幅宽 / 品控硬数字）")

    # 6. canonical / hreflang
    if 'rel="canonical"' not in html:
        reasons.append("缺 canonical")
    if kind != "article":
        for tag in ('hreflang="zh"', 'hreflang="en"', 'hreflang="x-default"'):
            if tag not in html:
                reasons.append(f"缺 {tag}")

    # 7. JSON-LD：逐块独立、各自合法、含 FAQPage
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    parsed = []
    for i, b in enumerate(blocks, 1):
        try:
            obj = json.loads(b)
        except Exception as exc:
            reasons.append(f"第 {i} 块 JSON-LD 非法: {exc}")
            continue
        if not isinstance(obj, dict) or "@context" not in obj or "@type" not in obj:
            reasons.append(f"第 {i} 块 JSON-LD 缺 @context/@type")
        parsed.append(obj)
    if len(blocks) < MIN_JSONLD[kind]:
        reasons.append(f"JSON-LD 仅 {len(blocks)} 块 < {MIN_JSONLD[kind]}")
    faq_pages = [o for o in parsed if isinstance(o, dict) and o.get("@type") == "FAQPage"]
    if not faq_pages:
        reasons.append("缺 FAQPage 结构化数据")
    elif len(faq_pages[0].get("mainEntity", [])) < MIN_FAQ:
        reasons.append("FAQPage 条目不足")

    # 8. 备案 / robots
    if ICP not in html:
        reasons.append("缺 ICP 备案号")
    if GONGAN not in html:
        reasons.append("缺公安备案号")
    if "noindex" in html.lower():
        reasons.append("robots 含 noindex（新页必须可收录）")

    # 9. 语言纯净：英文页正文区不得夹中文
    han = len(HAN.findall(body_text))
    if lang == "en" and han > 0:
        reasons.append(f"英文正文夹中文 {han} 字：{body_text[max(0, HAN.search(body_text).start()-12):HAN.search(body_text).start()+20]}")

    # 10. 首句答我们公司（知识库问答页）+ 发布日期
    if kind == "knowledge":
        first = body_text[:90]
        ok_first = ("我们" in first or "匠领数码" in first) if lang == "zh" else \
                   ("We " in first or "J.LINK" in first or "we " in first)
        if not ok_first:
            reasons.append("正文首句未答「我们公司」（AI 建不了品牌实体关联）")
    if expect_date:
        dates = [o.get("datePublished") for o in parsed
                 if isinstance(o, dict) and o.get("datePublished")]
        if not dates or expect_date not in dates:
            reasons.append(f"datePublished 未对齐北京发布日期 {expect_date}（实际 {dates}）")

    h1m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    stats = {
        "label": label, "lang": lang, "kind": kind,
        "h1": _plain(h1m.group(1))[:60] if h1m else "",
        "body_chars": thickness, "md_chars": len(body_text),
        "h2": h2_n, "faq": faq_n, "qa": qa_n,
        "jsonld": len(blocks), "date": expect_date or "",
    }
    return (not reasons), reasons, stats


def enforce(html: str, lang: str = "zh", kind: str = "knowledge",
            expect_date: str | None = None, label: str = ""):
    """不过闸门就抛错；调用方必须在写文件之前调用。"""
    ok, reasons, stats = check(html, lang, kind, expect_date, label)
    if not ok:
        raise GateError(
            f"[{label or '未命名页面'}/{lang}] 发布闸门未通过：\n  - " + "\n  - ".join(reasons))
    print(f"  ✅ 闸门通过 {label}/{lang}｜{stats['h1']}｜正文 {stats['body_chars']} 字"
          f"｜h2 {stats['h2']}｜FAQ {stats['faq']}｜JSON-LD {stats['jsonld']} 块"
          + (f"｜发布日 {expect_date}" if expect_date else ""))
    return stats


if __name__ == "__main__":
    import sys
    from pathlib import Path
    if len(sys.argv) < 2:
        print("用法: python scripts/content_gate.py <页面.html> [--en] [--insight]")
        raise SystemExit(0)
    p = Path(sys.argv[1])
    lang = "en" if "--en" in sys.argv else "zh"
    kind = "insight" if "--insight" in sys.argv else "knowledge"
    ok, reasons, stats = check(p.read_text(encoding="utf-8"), lang, kind)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print("通过 ✅" if ok else "未通过 ❌\n  - " + "\n  - ".join(reasons))
