# -*- coding: utf-8 -*-
"""
knowledge_grow.py — 知识库增长发布（定时自动）

工作流程：
1. 读 scripts/knowledge_queue_state.json（已上线 live 列表）
2. 取 knowledge_queue.py QUEUE 中第一个未上线专题
3. 把它的 slug 加入 live 并写回状态文件
4. 调用 gen_knowledge.main() 重新生成（hub 会动态纳入新专题）
之后由工作流运行 gen_sitemap.py 重建站点地图。

禁用词铁律：工艺只用 分散印花/涤纶印花/宽幅数码印花；幅宽 200-320CM 六档；
最小起印 1米起印/免费打样；不出现旧规格禁用词。
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
STATE = ROOT / "scripts" / "knowledge_queue_state.json"


def load_queue():
    spec = importlib.util.spec_from_file_location(
        "knowledge_queue", str(ROOT / "scripts" / "knowledge_queue.py"))
    kq = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kq)
    return kq.QUEUE


def main():
    queue = load_queue()
    state = json.loads(STATE.read_text(encoding="utf-8"))
    live = set(state.get("live", []))

    nxt = None
    for t in queue:
        if t["slug"] not in live:
            nxt = t
            break
    if not nxt:
        print("队列已空，无新专题可发布。")
        return

    live.add(nxt["slug"])
    state["live"] = sorted(live)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已发布专题：{nxt['slug']}（{nxt['zh']['h1']}）")

    # 重新生成知识库（改动状态后再 import，T 才会纳入新专题）
    import gen_knowledge
    gen_knowledge.main()


if __name__ == "__main__":
    main()
