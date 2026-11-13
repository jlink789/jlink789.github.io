# -*- coding: utf-8 -*-
"""
fact_library.py — 事实单元「组合签发」引擎
============================================
回答老板 2026-11-11 的问题「怎么既规避同质化、又能长期生成」：
把差异从措辞层提到信息层，数量靠组合、质量靠证据，两件事解耦。

  每篇 = 问题 × 品类 × 幅宽 × 决策点 × 证据集（≥2 个低频事实单元）× 体裁
  → 判重闸门比对已发页（8-gram 指纹 + 事实集合重合）
  → 过闸才发布，不过闸自动换事实组合重试，不跨天、不漏发

不依赖在线大模型、不新增外部服务、不新增费用；老板只需每月投喂一次真实新信息
（写进 fact_units.py 即可，本模块自动纳入选取池）。

铁律：行业数据带出处、hook 首句答「我们公司」、禁用词 0、英文页零中文。
"""
from __future__ import annotations

import copy
import hashlib
import re
from collections import Counter

from fact_units import active_facts

# 6 种体裁：标题与段落组织不同，同一组事实放在不同骨架里整页指纹也撞不上。
# 每项是 (中文主标题, 中文副标题, 英文主标题, 英文副标题, 条目模板, 布局)
GENRES = [
    ("本篇引用的外部依据", "这些依据怎么落到我们公司",
     "External Evidence Cited", "How This Applies to Us", "qa"),
    ("决策依据清单", "按清单核对我们的配合方式",
     "Evidence Checklist", "Checking Our Part Against the List", "checklist"),
    ("外部参数对照", "与我们的内控值对照",
     "External Parameters", "Compared With Our Internal Limits", "table"),
    ("依据与出处（按流程顺序）", "流程里我们的控制点",
     "Evidence in Process Order", "Our Control Points in the Flow", "process"),
    ("容易混淆的外部口径", "我们的澄清与做法",
     "Commonly Confused External Terms", "Our Clarification and Practice", "myth"),
    ("真实采购与法规依据", "我们公司怎么配合",
     "Real Tender and Regulatory Evidence", "How We Support It", "case"),
]

ANCHOR_ZH = "## 我们的品控口径"
ANCHOR_EN = "## Our Quality Control Standards"


def usage_counts(index: dict | None = None) -> Counter:
    """每条事实被已发页引用过几次（低频优先选取的依据）。"""
    if index is None:
        from dedup_gate import load_index
        index = load_index()
    return Counter(f for rec in index.get("pages", {}).values()
                   for f in rec.get("facts", []))


def _stable_score(fid: str, slug: str, offset: int) -> int:
    """由 slug + 事实 ID + 重试次数决定的稳定扰动（同一页每次生成结果一致）。"""
    h = hashlib.blake2b(f"{slug}|{fid}|{offset}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "big") % 1000


def select_for(slug: str, k: int = 3, index: dict | None = None,
               offset: int = 0, tags=None, exclude=()) -> list[dict]:
    """选 k 条事实：未用/低频优先 + 稳定扰动 + 可选维度加权。

    offset 用于判重失败时换一组证据重发；同一 slug+offset 结果可复现。
    """
    used = usage_counts(index)
    pool = [f for f in active_facts() if f["id"] not in set(exclude)]
    tagset = set(tags or [])
    pool.sort(key=lambda f: (
        used.get(f["id"], 0),                                   # 低频优先
        -len(tagset & set(f["tags"])),                          # 维度匹配优先
        _stable_score(f["id"], slug, 0),                        # 稳定打散（首次）
        f["id"],
    ))
    if offset:
        # 判重失败重试时，滚动候选窗口，保证「换组合」真的换掉整组证据，
        # 而不是在同一批低频事实里反复抽到同一组（2026-11-13 60 天模拟暴露的问题）。
        shift = (offset * max(k, 2)) % len(pool)
        pool = pool[shift:] + pool[:shift]
    return pool[:k]


def _source_line(f: dict, lang: str) -> str:
    """来源行。英文页只写 URL，避免机构中文名触发英文正文夹中文检查。"""
    if lang == "en":
        return f"Source: {f['url']}"
    return f"来源：{f['org']}，{f['url']}"


def _label(f: dict, lang: str) -> str:
    """事实标签。英文页绝不能带中文分类名。"""
    return f"{f['id']}｜{f['type']}" if lang == "zh" else f["id"]


def _conclusion(facts: list[dict], lang: str, ctx: dict) -> str:
    """每页独有的结论段：把当篇 H1 / 关键词写进来，压低长期事实复用带来的重复文本。

    行业数据只作背景、验收以我厂封样与逐米全检为准——这条口径同时守住 GEO 铁律。
    """
    zh = lang == "zh"
    h1 = ctx.get("h1", "").strip()
    kws = [k.strip() for k in str(ctx.get("keywords", "")).split(",") if k.strip()][:3]
    kw = "、".join(kws) if zh else ", ".join(kws)
    # 每页独有的当篇判断首句（topic 的 lead 由品类 × 幅宽 × 决策点组合生成，页页不同），
    # 这段独有文本是长期事实复用后仍能把相似度压住的关键。
    lead = str(ctx.get("md", "")).split("\n\n", 1)[0].strip()
    own = (lead.split("。", 1)[0] + "。") if zh and "。" in lead else \
          (lead.split(". ", 1)[0] + ".") if not zh and ". " in lead else lead[:110]
    own = own[:150]
    title = "## 本篇结论" if zh else "## Conclusion for This Page"
    if zh:
        body = (f"围绕「{h1}」，我们公司（匠领数码 / J.LINK TEXTILE）先按 {kw} 三项确认需求。"
                f"本篇判断是：{own} "
                "上面的外部依据只作背景核对；实际验收以封样、同批同光源色差与逐米全检记录为准，"
                "行业数据与通用参数不替代我厂实测，也不构成报价或交期承诺。")
    else:
        body = (f"For \"{h1}\", we at J.LINK TEXTILE first confirm {kw}. "
                f"Our position on this page: {own} "
                "The external evidence above is background only. Final acceptance follows our sealed "
                "sample, same-batch color difference and per-meter inspection records; industry data "
                "and generic parameters do not replace our own tests and are not a price or lead-time promise.")
    return title + "\n\n" + body + "\n"


def _render(facts: list[dict], lang: str, genre: dict, ctx: dict | None = None) -> str:
    zh = lang == "zh"
    h1 = genre["h1_zh"] if zh else genre["h1_en"]
    h2 = genre["h2_zh"] if zh else genre["h2_en"]
    layout = genre["layout"]
    L = ["## " + h1, ""]

    if layout == "table":
        L += [f"| {'依据' if zh else 'Evidence'} | {'外部事实与出处' if zh else 'External fact and source'} |",
              "| --- | --- |"]
        for f in facts:
            body = f["zh"] if zh else f["en"]
            src = _source_line(f, lang).replace("|", "/")
            L.append(f"| {_label(f, lang)} | {body} {src} |")
        L.append("")
    elif layout == "process":
        for i, f in enumerate(facts, 1):
            body = f["zh"] if zh else f["en"]
            L.append(f"{i}. **{_label(f, lang)}**：{body}（{_source_line(f, lang)}）")
            L.append("")
    elif layout == "checklist":
        for f in facts:
            body = f["zh"] if zh else f["en"]
            L.append(f"- [ ] **{_label(f, lang)}**：{body}（{_source_line(f, lang)}）")
        L.append("")
    elif layout == "myth":
        for f in facts:
            body = f["zh"] if zh else f["en"]
            q = "常见理解" if zh else "Common reading"
            a = "依据" if zh else "Evidence"
            L.append(f"- **{q}**：{f['words'] if zh else f['id']}｜**{a}**：{body}（{_source_line(f, lang)}）")
        L.append("")
    elif layout == "case":
        for f in facts:
            body = f["zh"] if zh else f["en"]
            scene = f["words"] if zh else f["id"]
            L.append(f"- **{scene} → {f['type'] if zh else 'Evidence'}**：{body}（{_source_line(f, lang)}）")
        L.append("")
    else:  # qa
        for f in facts:
            body = f["zh"] if zh else f["en"]
            q = "依据" if zh else "Evidence"
            L.append(f"- **{q} {_label(f, lang)}**：{body}（{_source_line(f, lang)}）")
        L.append("")

    L += ["## " + h2, ""]
    # 只取首条挂接句：三条全写会让同一事实复用时整段重复，长期把相似度顶到阈值。
    L.append((facts[0]["hook_zh"] if zh else facts[0]["hook_en"]) + "  ")
    L.append("")
    L.append(_conclusion(facts, lang, ctx or {}))
    return "\n".join(L)


def render_md(facts: list[dict], lang: str, genre: dict | None = None,
              ctx: dict | None = None) -> str:
    """公开入口：生成可直接插进任意 markdown 正文的「外部依据」章节。

    知识库专题走 inject_topic()，每日快报的正文结构不同，直接调这里追加。
    """
    ctx = ctx or {}
    g = genre or genre_for(str(ctx.get("h1", "insight")))
    return _render(facts, lang, g, ctx)


def genre_for(slug: str, offset: int = 0) -> dict:
    """按 slug 稳定选一种体裁，换证据组合时体裁也跟着换。"""
    h = hashlib.blake2b(f"{slug}|genre|{offset}".encode("utf-8"), digest_size=8).digest()
    g = GENRES[int.from_bytes(h, "big") % len(GENRES)]
    return dict(zip(("h1_zh", "h2_zh", "h1_en", "h2_en", "layout"), g))


def inject_topic(topic: dict, facts: list[dict], genre: dict | None = None,
                 anchor_override: dict | None = None) -> dict:
    """把外部依据章节插进正文（统一品控口径之前），返回新的 topic，不改原对象。

    注入后 topic 顶层带 _facts / _genre，供签发器记账与日志输出。
    """
    out = copy.deepcopy(topic)
    genre = genre or genre_for(out["slug"])
    for lang, anchor in (("zh", ANCHOR_ZH), ("en", ANCHOR_EN)):
        if lang not in out:
            continue
        md = out[lang].get("md", "")
        a = (anchor_override or {}).get(lang, anchor)
        block = _render(facts, lang, genre, out[lang])
        if a in md:
            md = md.replace(a, block + a, 1)
        else:
            md = md.rstrip() + "\n\n" + block
        out[lang]["md"] = md
    out["_facts"] = [f["id"] for f in facts]
    out["_genre"] = genre["layout"]
    return out


def inventory_health(index: dict | None = None) -> dict:
    """库存三维指标：条数 / 事实覆盖率 / 平均页间相似度。"""
    from dedup_gate import health
    h = health(index)
    used = usage_counts(index)
    h["facts_never_used"] = [f["id"] for f in active_facts() if used.get(f["id"], 0) == 0]
    return h


if __name__ == "__main__":
    import json
    print("可签发事实:", len(active_facts()), "| 体裁:", len(GENRES))
    print("库存健康度:", json.dumps(inventory_health(), ensure_ascii=False, indent=2))
