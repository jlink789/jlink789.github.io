# -*- coding: utf-8 -*-
"""
update_index_insights.py — 把首页「最新资讯」区块改为展示每日知识快报。

背景：/articles/ 批量水文已停更（最后停在 2026-11-07），但首页 news 区块仍由
build_news.py 从 articles/ 取数，长期显示旧文。知识快报（/knowledge/insights/）
每天 02:30 北京时间仍在更新，故改由本脚本供首页取数。

- 数据源：knowledge/insights/meta.json（按日期倒序取最新 10 篇）
- 输出：index.html 中 <section id="news">…</section> 区块
- 由 knowledge-insights.yml 每日生成快报后调用，首页随之自动刷新

用法：
    python scripts/update_index_insights.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
INSIGHTS = ROOT / "knowledge" / "insights"
META = INSIGHTS / "meta.json"
INDEX = ROOT / "index.html"
TOP_N = 10


def build_section(rows: list) -> str:
    items = []
    for date, title in rows:
        title = (title or "").replace("&", "&amp;").replace('"', "&quot;")
        items.append(
            f'        <li><span class="news-tag" style="background:#e8f0fe;color:#1a73e8">行业洞察</span> '
            f'<a href="/knowledge/insights/{date}.html">{title}</a> '
            f'<span class="news-date" style="color:#999;font-size:.85em">· {date}</span></li>'
        )
    total = len(rows)
    return f'''<section id="news" style="padding:60px 20px;max-width:900px;margin:0 auto;background:#fafbfc;border-radius:12px;margin-top:40px">
  <h2 style="font-size:1.6em;color:#1a1a2e;margin-bottom:8px">📰 最新资讯 · 行业洞察</h2>
  <p style="color:#666;margin-bottom:24px;font-size:.95em">带出处的行业依据、工艺参数与采购决策 · 每日更新</p>
  <ul style="list-style:none;padding:0;margin:0;line-height:2">
{chr(10).join(items)}
  </ul>
  <div style="text-align:center;margin-top:28px">
    <a href="/knowledge/insights/index.html" class="btn-primary" style="display:inline-block;text-decoration:none">查看全部 {total} 篇 →</a>
  </div>
</section>'''


def main():
    if not META.exists():
        print("FAIL: 无 insights meta.json")
        raise SystemExit(1)
    meta = json.loads(META.read_text(encoding="utf-8"))
    rows = [(d, meta[d].get("zh", "")) for d in sorted(meta, reverse=True)[:TOP_N]]
    if not rows:
        print("FAIL: 无快报数据")
        raise SystemExit(1)

    content = INDEX.read_text(encoding="utf-8")
    new_section = build_section(rows)
    m = re.search(r'<section id="news".*?</section>', content, re.DOTALL)
    if not m:
        print("FAIL: 首页未找到 news 区块")
        raise SystemExit(1)
    if m.group(0) == new_section:
        print("首页资讯区块已是最新快报，无变化")
        return
    INDEX.write_text(content.replace(m.group(0), new_section, 1), encoding="utf-8")
    print(f"✅ 首页资讯区块已换成知识快报：最新 {len(rows)} 篇（{rows[0][0]} ~ {rows[-1][0]}）")


if __name__ == "__main__":
    main()
