# -*- coding: utf-8 -*-
"""
rebuild_insights_tone.py — 按新口吻重建 2026-11-14 起的第二圈快报（存量页）。

老板 2026-11-28 点头：「把线上那几十篇也按新口吻重建一遍」，覆盖 11-11 的「已上线不改」规矩。

原则：只换口吻，不换事实。每篇从 published_fingerprints.json 取回该日期原始
facts/genre，用 build_one 精确重建，保证外部依据、标题、体裁与线上一致。
11-14 之前的 legacy 页（第一圈，由池内 md 生成，无机械口吻）不动。

用法：
    python scripts/rebuild_insights_tone.py --dry-run
    python scripts/rebuild_insights_tone.py
"""
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gen_knowledge_insights as GI
import fact_library as FL
from content_gate import check as gate_check, enforce as gate_enforce

INS = ROOT / "knowledge" / "insights"
INDEX = ROOT / "scripts" / "published_fingerprints.json"
FROZEN_FROM = "2026-11-14"  # NEW_PICK_FROM，第二圈起点


def main(dry_run=False):
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    pages = idx.get("pages", {})
    meta = json.loads((INS / "meta.json").read_text(encoding="utf-8"))
    byid = {f["id"]: f for f in FL.active_facts()}
    gmap = {g[4]: g for g in FL.GENRES}

    dates = sorted(d for d in meta if d >= FROZEN_FROM)
    print(f"待重建第二圈快报：{len(dates)} 篇（{dates[0]} ~ {dates[-1]}）")
    print("原则：用去重索引里的原始 facts/genre 重建，只换口吻，不换依据。\n")

    rebuilt = []
    failed = []
    for d in dates:
        rec = pages.get(f"insight/{d}/zh", {})
        ids = rec.get("facts") or []
        genre_key = rec.get("genre")
        if not ids or genre_key not in gmap:
            print(f"[{d}] 跳过：去重索引无原始 facts/genre（{ids}/{genre_key}）")
            continue
        facts = [byid[fid] for fid in ids if fid in byid]
        if len(facts) != len(ids):
            print(f"[{d}] 跳过：事实库缺 {set(ids) - set(byid)}")
            continue
        genre = gmap[genre_key]
        rd = datetime.date.fromisoformat(d)
        zh = GI.build_one("zh", run_date=rd, facts=facts, genre=genre, cycle=1)
        en = GI.build_one("en", run_date=rd, facts=facts, genre=genre, cycle=1)

        # 事实保真：每条外部依据的事实句必须在重建后仍出现。
        # 注意：事实句开头的全称自称会被 _soften_self 换掉，比对时按同样规则软化。
        plain = re.sub(r"<[^>]+>", " ", zh)
        miss = [fid for fid, f in zip(ids, facts)
                if GI._soften_self(f["zh"])[:24] not in plain]
        if miss:
            print(f"[{d}] ❌ 事实句丢失 {miss}，不写")
            failed.append(d)
            continue

        # 闸门：日期 / 结构 / JSON-LD
        ok_z, rz, _ = gate_check(zh, "zh", "insight", expect_date=d, label=f"insight/{d}")
        ok_e, re_, _ = gate_check(en, "en", "insight", expect_date=d, label=f"insight/en-{d}")
        if not (ok_z and ok_e):
            print(f"[{d}] ❌ 闸门未过 zh:{rz[:2]} en:{re_[:2]}，不写")
            failed.append(d)
            continue

        # 口吻自检：机械表述必须归零
        bad = ["不写成我厂实测值", "我们公司（匠领数码", "按「case」", "强制要求", "结合「本期依据"]
        left = {b: zh.count(b) for b in bad if zh.count(b)}
        if left:
            print(f"[{d}] ❌ 残留机械口吻 {left}，不写")
            failed.append(d)
            continue

        if not dry_run:
            (INS / f"{d}.html").write_text(zh, encoding="utf-8")
            (INS / f"en-{d}.html").write_text(en, encoding="utf-8")
        print(f"[{d}] ✅ 依据 {ids} 体裁 {genre_key}｜口吻归零｜闸门通过"
              + ("（dry-run，未写）" if dry_run else "（已写）"))
        rebuilt.append(d)

    if not dry_run:
        GI.build_index()
        print("\n已更新快报索引 index.html / index-en.html")

    print(f"\n汇总：重建 {len(rebuilt)} 篇｜失败 {len(failed)} 篇"
          + (f"｜失败日期 {failed}" if failed else ""))
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只校验不写文件")
    args = ap.parse_args()
    main(dry_run=args.dry_run)
