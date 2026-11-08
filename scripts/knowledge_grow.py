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

断供保护：队列没有待发布专题时，输出 GitHub Actions ::warning:: 黄色告警，
不再静默空跑；库存 ≤3 条时同样告警，提示尽快把下一批已补完整答案的专题灌入 QUEUE。

禁用词铁律：工艺只用 分散印花/涤纶印花/宽幅数码印花；幅宽 200-320CM 六档；
最小起印 1米起印/免费打样；不出现旧规格禁用词。
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
STATE = ROOT / "scripts" / "knowledge_queue_state.json"
LLMS_FILES = (ROOT / "llms.txt", ROOT / "llms-full.txt")
SITE = "https://bu6789.com"
MARK_S = "<!-- KB-GROW:START -->"
MARK_E = "<!-- KB-GROW:END -->"


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

    if not pending:
        msg = ("知识库队列已断供：没有待发布专题，今天无法新增页面。"
               "请把 GEO 计划中已补完整答案的下一批专题灌入 knowledge_queue.py。")
        print("::warning::" + msg)
        print("⚠️ " + msg)
        sync_llms(queue, live)
        return

    nxt = pending[0]
    live.add(nxt["slug"])
    state["live"] = sorted(live)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 今日发布专题：{nxt['slug']}（{nxt['zh']['h1']}）")

    # 先同步 llms，再重生成页面；两者都只依赖 state，顺序不影响结果
    sync_llms(queue, live)

    import gen_knowledge
    gen_knowledge.main()

    rest = len(pending) - 1
    print(f"剩余库存 {rest} 条（按每天 1 条可发 {rest} 天）")
    if rest <= 3:
        warn = f"知识库库存仅剩 {rest} 条，请尽快补货，避免每日增长中断。"
        print("::warning::" + warn)
        print("⚠️ " + warn)


if __name__ == "__main__":
    main()
