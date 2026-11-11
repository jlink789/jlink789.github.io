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


def main():
    queue = load_queue()
    state = json.loads(STATE.read_text(encoding="utf-8"))
    live = set(state.get("live", []))
    pending = [t for t in queue if t["slug"] not in live]
    print(f"队列库存：共 {len(queue)} 条，已上线 {len(live)} 条，待发布 {len(pending)} 条")

    # 自动补货：库存 < MIN_STOCK 时一次生成 BATCH 条完整问答并持久化，随后重新加载队列
    import kb_autogen
    added = kb_autogen.ensure_inventory(len(pending), min_stock=MIN_STOCK, batch=BATCH)
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

    nxt = pending[0]
    today = today_str()
    print(f"北京发布日期：{today}")
    print(f"今日专题：{nxt['slug']}｜{nxt['zh']['h1']} / {nxt['en']['h1']}")

    # 发布闸门预检：只构建、不写文件。不合规直接抛错 → state / llms / 页面都不动，
    # 工作流失败后下次重试仍抓同一个待发专题，不会把不合格的题「跳过」。
    import gen_knowledge
    gen_knowledge.main(
        enforce_new={nxt["slug"]}, dry_run=True,
        pub_dates={nxt["slug"]: today}, extra_topics=[nxt])

    live.add(nxt["slug"])
    state["live"] = sorted(live)
    # 新页 datePublished 用真实北京上线日；老页没有 published 记录，保持原日期不变。
    state.setdefault("published", {})[nxt["slug"]] = today
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    # 先同步 llms，再重生成页面；两者都只依赖 state，顺序不影响结果
    sync_llms(queue, live)

    gen_knowledge.main(extra_topics=[nxt])
    print(f"✅ 已上线中英双页（闸门通过）：{nxt['zh']['h1']} / {nxt['en']['h1']}")

    rest = len(pending) - 1
    print(f"剩余库存 {rest} 条（按每天 1 条可发 {rest} 天）")
    if rest <= 3:
        warn = f"知识库库存仅剩 {rest} 条，请尽快补货，避免每日增长中断。"
        print("::warning::" + warn)
        print("⚠️ " + warn)


if __name__ == "__main__":
    main()
