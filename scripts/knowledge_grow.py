# -*- coding: utf-8 -*-
"""
knowledge_grow.py — 知识库增长发布（每日自动，每天至少一条）

工作流程：
1. 读 scripts/knowledge_queue_state.json（已上线 live 列表）
2. 取 knowledge_queue.py QUEUE 中第一个未上线专题（一次只发 1 条，保证逐条上线）
3. 把它的 slug 加入 live 并写回状态文件
4. 同步 llms.txt / llms-full.txt 的「知识库每日增长专题」块（AI 抓取入口）
5. 调用 gen_knowledge.main() 重新生成（hub 会动态纳入新专题）
之后由工作流运行 gen_sitemap.py 重建站点地图（sitemap 会自动派生 hreflang / 权重）。

自动补货（老板 2026-11-08 定）：待发布库存 <3 条时，调用 kb_autogen.ensure_inventory()
一次生成 50 条全新的中英双语完整问答（问题+答案都完整、禁用词 0、组合去重），
写入 scripts/kb_autogen_generated.json 并随工作流提交持久化，保证每天至少能发 1 条。
队列真的无待发布专题时仍输出 ::warning:: 黄色告警，不静默空跑。

禁用词铁律：工艺只用 分散印花/涤纶印花/宽幅数码印花；幅宽 200-320CM 六档；
最小起印 1米起印/免费打样；不出现旧规格禁用词。
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))
from beijing_time import today_str  # noqa: E402  上线日期按北京时间

STATE = ROOT / "scripts" / "knowledge_queue_state.json"
LLMS_FILES = (ROOT / "llms.txt", ROOT / "llms-full.txt")
SITE = "https://bu6789.com"
MARK_S = "<!-- KB-GROW:START -->"
MARK_E = "<!-- KB-GROW:END -->"
MIN_STOCK = 3     # 库存低于此数触发自动补货
BATCH = 50        # 每次自动补充的完整问答条数

# 保证从任意工作目录运行时都能 import 同目录脚本（GitHub Actions / 本地手动均适用）
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))


def load_queue():
    spec = importlib.util.spec_from_file_location(
        "knowledge_queue", str(ROOT / "scripts" / "knowledge_queue.py"))
    kq = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kq)
    return kq.QUEUE


def sync_llms(queue, live):
    """把已上线队列专题同步进 llms.txt / llms-full.txt 的增长专题块（幂等）。"""
    rows = []
    for t in queue:
        if t["slug"] not in live:
            continue
        zh = t["url_zh"].lstrip("/")
        rows.append(
            f"- {t['zh']['h1']}（匠领数码知识库专题 · 中英双语）：{SITE}/{zh}")
    block = "\n".join([MARK_S] + rows + [MARK_E])
    for f in LLMS_FILES:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        if MARK_S in text and MARK_E in text:
            new = re.sub(
                re.escape(MARK_S) + r".*?" + re.escape(MARK_E),
                lambda _: block, text, flags=re.S)
        else:
            anchor = "- 知识库首页（中英双语）："
            if anchor in text:
                new = text.replace(anchor, block + "\n" + anchor, 1)
            else:
                new = text.rstrip() + "\n\n" + block + "\n"
        if new != text:
            f.write_text(new, encoding="utf-8")
            print(f"已同步 {f.name}：{len(rows)} 条增长专题")


def _build_with_facts(candidates, today, index, try_topics=12, try_offsets=8):
    """组合签发：选证据 → 注入正文 → 单页闸位 → 跨页判重 → 不过就自动换证据 / 换题。

    全程只构建 HTML，不写任何文件；返回 (注入后的 topic, {lang: html}, 判重统计) 或 None。
    2026-11-13 起：每天每篇强制绑定 3 条低频事实单元 + 1 种体裁，
    与所有已发页比 8-gram 指纹和事实集合，超阈值就在同一次工作流内换组合重试。
    """
    import gen_knowledge
    import dedup_gate as D
    import fact_library as FL
    from content_gate import check as gate_check

    tried = 0
    for t in candidates[:try_topics]:
        for off in range(try_offsets):
            tried += 1
            facts = FL.select_for(t["slug"], k=3, index=index, offset=off)
            it = FL.inject_topic(t, facts, FL.genre_for(t["slug"], off))
            htmls, reasons, last = {}, [], None
            for lang in ("zh", "en"):
                html = gen_knowledge.build_page(lang, it, pub_date=today)
                htmls[lang] = html
                _ok, g_rs, _st = gate_check(html, lang, "knowledge",
                                            expect_date=today, label=t["slug"])
                _dok, d_rs, d_st = D.check("knowledge", t["slug"], lang, html,
                                           facts=it["_facts"], index=index)
                last = d_st
                reasons += g_rs + d_rs
            if not reasons:
                print(f"✅ 组合签发通过（第 {tried} 次尝试）｜事实 {it['_facts']}"
                      f"｜体裁 {it['_genre']}｜与最近页相似度 {last['sim']}")
                return it, htmls, last
            if off == 0 or tried % 8 == 0:
                print(f"   ↻ 第 {tried} 次组合被拦下，自动换证据/换题：{reasons[0][:90]}")
    return None


def main(dry_run=False):
    queue = load_queue()
    state = json.loads(STATE.read_text(encoding="utf-8"))
    live = set(state.get("live", []))
    pending = [t for t in queue if t["slug"] not in live]
    print(f"队列库存：共 {len(queue)} 条，已上线 {len(live)} 条，待发布 {len(pending)} 条")

    # 自动补货：库存 < MIN_STOCK 时按「未发维度覆盖率」生成 BATCH 条并持久化
    import kb_autogen
    added = 0 if dry_run else kb_autogen.ensure_inventory(
        len(pending), min_stock=MIN_STOCK, batch=BATCH)
    if added:
        queue = load_queue()
        pending = [t for t in queue if t["slug"] not in live]
        print(f"补货后队列：共 {len(queue)} 条，待发布 {len(pending)} 条")

    if not pending:
        msg = ("知识库队列已断供：没有待发布专题，今天无法新增页面。"
               "请把 GEO 计划中已补完整答案的下一批专题灌入 knowledge_queue.py。")
        print("::warning::" + msg)
        print("⚠️ " + msg)
        sync_llms(queue, live)
        return

    today = today_str()
    print(f"北京发布日期：{today}")

    import dedup_gate as D
    import fact_library as FL
    index = D.load_index()
    picked = _build_with_facts(pending, today, index)
    if not picked:
        msg = ("组合签发失败：候选专题 × 证据组合 × 体裁全部被跨页判重或发布闸门拦下，"
               "今天不写任何页面 / state / llms，下次运行仍抓同一批待发专题（不跳题）。"
               "若持续出现，请往 fact_units.py 投喂新的真实信息。")
        print("::error::" + msg)
        raise SystemExit(1)

    it, htmls, stats = picked
    print(f"今日专题：{it['slug']}｜{it['zh']['h1']} / {it['en']['h1']}")

    # 正式发布闸门预检：只构建、不写文件。不合规直接抛错 → state / llms / 页面都不动。
    import gen_knowledge
    gen_knowledge.main(
        enforce_new={it["slug"]}, dry_run=True,
        pub_dates={it["slug"]: today}, extra_topics=[it])
    if dry_run:
        print(f"[dry-run] 组合签发 + 双闸门全部通过，未写 state / llms / 页面 / 指纹索引")
        return

    live.add(it["slug"])
    state["live"] = sorted(live)
    # 新页 datePublished 用真实北京上线日；老页没有 published 记录，保持原日期不变。
    state.setdefault("published", {})[it["slug"]] = today
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    sync_llms(queue, live)
    gen_knowledge.main(extra_topics=[it])

    # 页面写盘成功后才记指纹；闸门失败绝不污染索引。
    for lang in ("zh", "en"):
        D.record("knowledge", it["slug"], lang, htmls[lang],
                 facts=it["_facts"], genre=it["_genre"], date=today, index=index)
    D.save_index(index)

    print(f"✅ 已上线中英双页（闸门 + 判重通过）：{it['zh']['h1']} / {it['en']['h1']}")
    h = FL.inventory_health(index)
    print(f"库存健康度：已发页 {h['pages']}｜事实覆盖 {h['facts_used']}/{h['facts_total']}"
          f"｜平均页间相似度 {h['avg_sim']}｜>0.50 页对 {h['pairs_over_limit']}/{h['pairs_sampled']}")

    rest = len(pending) - 1
    print(f"剩余库存 {rest} 条（按每天 1 条可发 {rest} 天）")
    if rest <= 3:
        warn = f"知识库库存仅剩 {rest} 条，请尽快补货，避免每日增长中断。"
        print("::warning::" + warn)
        print("⚠️ " + warn)


if __name__ == "__main__":
    import sys as _sys
    main(dry_run="--dry-run" in _sys.argv)
