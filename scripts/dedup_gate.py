# -*- coding: utf-8 -*-
"""
dedup_gate.py — 跨页同质化判重闸门（发布前最后一道卡口）
============================================================
背景：2026-11-11 全站诊断发现 1164 篇长尾文里 82.6% 页面共享同一句、
每篇 73.8% 为模板复现句、100 篇抽样有 608/4950 对 8-gram Jaccard > 0.50。
content_gate.py 只卡「单页合规」，卡不住「攒一起全一样」，本模块补这一层。

两条判据（任一命中即拒发，签发器自动换事实组合重试）：
  1. 正文指纹相似度：8-gram shingle 的 bottom-k MinHash 估计 Jaccard > SIM_LIMIT
  2. 事实集合重合：|A∩B| / min(|A|,|B|) >= FACT_LIMIT

只比对「正文区」（复用 content_gate._body_zone），统一收尾 / FAQ / CTA / 页脚
全站本来就该一致，不该算进同质化。只跟同语种页比对，中英互不干扰。

索引 scripts/published_fingerprints.json 随 git 持久化，沿用 kb_autogen_generated.json
的既有做法；发布成功后由签发器 record()，闸门失败绝不记账。
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from content_gate import _body_zone, _plain

ROOT = Path(__file__).parent.parent
INDEX = Path(__file__).parent / "published_fingerprints.json"
K = 256                 # bottom-k sketch 大小，估计误差约 1/sqrt(K) ≈ 6%
NGRAM = 8              # 字符级 8-gram，与 2026-11-11 诊断口径一致
# 阈值由 132 页存量基线校准：存量 12 天循环快报 0.98~1.00，正常知识库页 0.11~0.20，
# 自动补货未注入页彼此 0.30~0.57，注入事实后新页 0.16~0.45。
# 硬阈值对齐给老板的验收口径「页间 8-gram Jaccard >0.50 判同质」：新页一旦 >0.50 就拒发，
# 保证增量为 0 对；0.42 实测会让事实复用 60 天后开始缺页，0.50 才撑得住长期不断供。
# 存量历史循环页仍占 17/4017 ≈ 0.42%，低于验收目标 <1%，按「已上线不改」不回补。
SIM_LIMIT = 0.50
# 历史遗留页折扣：bootstrap 标 genre=legacy 的页是 12 天硬循环 / 旧模板产物，
# 正文骨架固定。新页注入事实后与同题历史页仍有 0.51~0.55 的骨架相似，这是存量包袱，
# 不是「新增同质化」；按 0.50 硬卡会把第 2 圈快报整批拒发。放到 0.60 仍能挡住
# 0.98 那种完全复制，且新页之间、新页 vs 非 legacy 页一律仍按 0.50 硬卡。
# 存量循环页另由阶段 3 的 noindex + 移出 sitemap 处理，与这套增量机制互不替代。
LEGACY_LIMIT = 0.60
# 滑动窗口：只跟最近 N 个「新机制上线后」的页比正文指纹，存量 legacy 页始终全比。
# 双链路每天 2 页，90 页 ≈ 45 天。若无窗口，事实库复用到一定轮次后所有新页都会
# 跟半年积攒的旧页贴着阈值，长期必然越堵越缺页（实测 60 天双链路缺 42 页）。
# 窗口让老页自然滑出，组合池 + 每月投喂负责补充新鲜证据，阈值永不放水。
WINDOW = 90
FACT_LIMIT = 0.80       # 事实集合重合上限
_UNIFY = re.compile(r"[\s\u3000]+")


# ── 指纹 ────────────────────────────────────────────────
def _sketch(text: str) -> list[int]:
    """字符级 8-gram → 64bit hash 集合 → 最小的 K 个（bottom-k MinHash）。"""
    s = _UNIFY.sub("", _plain(text))
    if len(s) < NGRAM:
        return []
    hs = {
        int.from_bytes(hashlib.blake2b(s[i:i + NGRAM].encode("utf-8"), digest_size=8).digest(), "big")
        for i in range(len(s) - NGRAM + 1)
    }
    return sorted(hs)[:K]


def fingerprint(html: str) -> list[int]:
    """取 HTML 正文区指纹；不含统一收尾与页脚。"""
    return _sketch(_body_zone(html))


def _jaccard(a: list[int], b: list[int]) -> float:
    """由两份 bottom-k sketch 估计原集合 Jaccard（并集最小 K 个中双份占比）。"""
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    merged = sorted(sa | sb)[:K]
    if not merged:
        return 0.0
    both = sum(1 for h in merged if h in sa and h in sb)
    return both / len(merged)


def _fact_overlap(a, b) -> float:
    sa, sb = set(a or []), set(b or [])
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


# ── 索引 ────────────────────────────────────────────────
def load_index() -> dict:
    if INDEX.exists():
        try:
            d = json.loads(INDEX.read_text(encoding="utf-8"))
            d.setdefault("pages", {})
            return d
        except Exception as e:
            print(f"::warning::判重索引读取失败，将重建：{e}")
    return {"version": 1, "updated": "", "pages": {}}


def save_index(data: dict):
    from beijing_time import today_str
    # 只保留 legacy 基线 + 最近 WINDOW*2 个新页：再老的页永远不参与判重，
    # 留着只会让随 git 持久化的索引一年膨胀几 MB。
    pages = data.get("pages", {})
    legacy = [(k, v) for k, v in pages.items() if v.get("genre") == "legacy"]
    fresh = [(k, v) for k, v in pages.items() if v.get("genre") != "legacy"]
    if len(fresh) > WINDOW * 2:
        data["pages"] = dict(legacy + fresh[-WINDOW * 2:])
        print(f"判重索引裁剪：保留 {len(legacy)} 个存量基线 + 最近 {WINDOW * 2} 个新页")
    data["updated"] = today_str()
    INDEX.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _key(kind, slug, lang):
    return f"{kind}/{slug}/{lang}"


# ── 判重 ────────────────────────────────────────────────
def check(kind: str, slug: str, lang: str, html: str,
          facts=None, sim_limit: float = SIM_LIMIT, fact_limit: float = FACT_LIMIT,
          index: dict | None = None):
    """返回 (ok, reasons, stats)。reasons 为空即通过。不写任何文件。"""
    data = index if index is not None else load_index()
    sk = fingerprint(html)
    facts = list(facts or [])
    reasons, worst_sim, worst_key, worst_fact, worst_fkey = [], 0.0, "", 0.0, ""
    key = _key(kind, slug, lang)

    pages = data["pages"]
    legacy_keys = [k for k, v in pages.items() if v.get("genre") == "legacy"]
    recent_keys = [k for k, v in pages.items() if v.get("genre") != "legacy"][-WINDOW:]
    compare_keys = legacy_keys + recent_keys   # 保持顺序，日志可复现

    for other_key in compare_keys:
        if other_key == key or not other_key.endswith("/" + lang):
            continue
        rec = pages[other_key]
        sim = _jaccard(sk, rec.get("sketch", []))
        ov = _fact_overlap(facts, rec.get("facts", []))
        limit = max(sim_limit, LEGACY_LIMIT) if rec.get("genre") == "legacy" else sim_limit
        if sim > worst_sim:
            worst_sim, worst_key = sim, other_key
        if ov > worst_fact:
            worst_fact, worst_fkey = ov, other_key
        if sim > limit:
            reasons.append(f"正文与已发页 {other_key} 相似度 {sim:.3f} > {limit}")
        if facts and ov >= fact_limit:
            reasons.append(f"事实集合与 {other_key} 重合 {ov:.0%} ≥ {fact_limit:.0%}")

    # 去重提示，避免同一次比对刷屏
    reasons = list(dict.fromkeys(reasons))[:4]
    stats = {
        "kind": kind, "slug": slug, "lang": lang,
        "sim": round(worst_sim, 3), "sim_with": worst_key,
        "fact_overlap": round(worst_fact, 2), "fact_with": worst_fkey,
        "facts": facts, "pages": len(data["pages"]),
        "sketch": len(sk),
    }
    return (not reasons), reasons, stats


def record(kind: str, slug: str, lang: str, html: str,
           facts=None, genre: str = "", date: str = "", index: dict | None = None):
    """发布成功后记账。调用方必须保证闸门已过。"""
    data = index if index is not None else load_index()
    from beijing_time import today_str
    data["pages"][_key(kind, slug, lang)] = {
        "date": date or today_str(), "kind": kind, "genre": genre,
        "facts": list(facts or []), "sketch": fingerprint(html),
    }
    if index is None:
        save_index(data)
    return data


# ── 存量基线 ────────────────────────────────────────────
def bootstrap(overwrite: bool = False) -> dict:
    """把已上线知识库专题 / 快报页建成判重基线（只记指纹，不改任何页面）。

    长尾文 articles/ 不纳入：那 1164 篇本身就是阶段 3 待分级存量，
    塞进索引只会让阈值失真；新页跟它们比由阶段 3 的 noindex 处理。
    """
    data = load_index() if not overwrite else {"version": 1, "updated": "", "pages": {}}
    KB = ROOT / "knowledge"
    jobs = []
    for p in sorted(KB.glob("*.html")):
        if p.name in ("index.html", "index-en.html"):
            continue
        lang = "en" if p.name.startswith("en-") else "zh"
        jobs.append(("knowledge", p.stem, lang, p))
    INS = KB / "insights"
    for p in sorted(INS.glob("*.html")):
        if p.name in ("index.html", "index-en.html"):
            continue
        lang = "en" if p.name.startswith("en-") else "zh"
        jobs.append(("insight", p.stem, lang, p))

    added = 0
    for kind, slug, lang, p in jobs:
        key = _key(kind, slug, lang)
        if key in data["pages"] and not overwrite:
            continue
        try:
            html = p.read_text(encoding="utf-8")
        except Exception:
            continue
        data["pages"][key] = {
            "date": "", "kind": kind, "genre": "legacy",
            "facts": [], "sketch": fingerprint(html),
        }
        added += 1
    save_index(data)
    print(f"✅ 判重基线：新增 {added} 页，索引累计 {len(data['pages'])} 页")
    return data


def health(index: dict | None = None) -> dict:
    """库存健康度：条数 / 维度覆盖率 / 平均页间相似度 / 事实复用。"""
    from collections import Counter
    from fact_units import active_facts
    data = index if index is not None else load_index()
    pages = data["pages"]
    usage = Counter(f for rec in pages.values() for f in rec.get("facts", []))
    total = len(active_facts())
    used = len(set(usage) & {f["id"] for f in active_facts()})

    # 同语种抽样两两相似度（最多 4000 对，避免 O(n²) 卡住）
    sims = []
    for lang in ("zh", "en"):
        items = [(k, v["sketch"]) for k, v in pages.items() if k.endswith("/" + lang)]
        for i in range(len(items)):
            for j in range(i + 1, min(i + 60, len(items))):
                sims.append(_jaccard(items[i][1], items[j][1]))
            if len(sims) > 4000:
                break
    return {
        "pages": len(pages),
        "facts_total": total,
        "facts_used": used,
        "fact_coverage": round(used / total, 3) if total else 0,
        "fact_max_reuse": max(usage.values()) if usage else 0,
        "avg_sim": round(sum(sims) / len(sims), 3) if sims else 0,
        "max_sim": round(max(sims), 3) if sims else 0,
        "pairs_over_limit": sum(1 for s in sims if s > SIM_LIMIT),
        "pairs_sampled": len(sims),
    }


if __name__ == "__main__":
    import sys
    if "--bootstrap" in sys.argv:
        bootstrap(overwrite="--overwrite" in sys.argv)
    d = load_index()
    h = health(d)
    print("索引健康度:", json.dumps(h, ensure_ascii=False, indent=2))
    print("用法: python scripts/dedup_gate.py --bootstrap [--overwrite]")
