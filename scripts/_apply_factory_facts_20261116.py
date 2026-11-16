# -*- coding: utf-8 -*-
"""一次性改写器（留作审计）：老板 2026-11-16 确认的 5 项工厂真实数据上线。

数据：宽幅机 8 台 / 日本京瓷喷头 / 月出货量 60 万米 / 当天出样 / 复购率 80%。
原则：精确字符串替换 + 命中数断言；任何一处没命中就整体报错，不静默跳过。
只改核心页、全站收尾单一数据源与 AI 索引；不批量重写 1300+ 已上线内容页。
"""
from pathlib import Path

ROOT = Path(__file__).parent.parent

EDITS = {
    # ── 首页 ─────────────────────────────────────────────────────────────
    "index.html": [
        ("<p>月产能 60+ 万米，8+ 条进口高速产线 24 小时连续运转。千-万米级大单不排队，花型一致、米数准确、交期锁定，长期供货稳如老狗。</p>",
         "<p>8 台日本京瓷（KYOCERA）喷头宽幅数码印花机，月出货量 60 万米，确认稿件当天出样。千-万米级大单不排队，花型一致、米数准确、交期锁定，客户复购率 80%。</p>"),
        ("<p>1米起印、免费打样，无需制版，确认稿件后5-7天出货。急单可协商加急，满足快反需求。</p>",
         "<p>1米起印、免费打样，无需制版，确认稿件当天出样；大货 5-7 个工作日出货。急单可协商加急，满足快反需求。</p>"),
        ("柯桥数码印花加工厂累计服务 500+ B 端客户，涵盖窗帘厂、墙布厂、家纺品牌、跨境电商。长期合作客户占比 60%+",
         "柯桥数码印花加工厂累计服务 500+ B 端客户，涵盖窗帘厂、墙布厂、家纺品牌、跨境电商。客户复购率 80%"),
        (">8+</div>\n          <div style=\"font-size:.85rem;color:var(--muted);margin-top:4px\">进口数码印花设备</div>",
         ">8 台</div>\n          <div style=\"font-size:.85rem;color:var(--muted);margin-top:4px\">宽幅机（日本京瓷喷头）</div>"),
        (">60+</div>\n          <div style=\"font-size:.85rem;color:var(--muted);margin-top:4px\">月产能（万米）</div>",
         ">60</div>\n          <div style=\"font-size:.85rem;color:var(--muted);margin-top:4px\">月出货量（万米）</div>"),
        ("""        <div>
          <div style="font-size:2.2rem;font-weight:800;color:var(--brand)">24h</div>
          <div style="font-size:.85rem;color:var(--muted);margin-top:4px">询单响应</div>
        </div>""",
         """        <div>
          <div style="font-size:2.2rem;font-weight:800;color:var(--brand)">24h</div>
          <div style="font-size:.85rem;color:var(--muted);margin-top:4px">询单响应</div>
        </div>
        <div>
          <div style="font-size:2.2rem;font-weight:800;color:var(--brand)">当天</div>
          <div style="font-size:.85rem;color:var(--muted);margin-top:4px">确认稿件后出样</div>
        </div>
        <div>
          <div style="font-size:2.2rem;font-weight:800;color:var(--brand)">80%</div>
          <div style="font-size:.85rem;color:var(--muted);margin-top:4px">客户复购率</div>
        </div>"""),
    ],

    # ── 中文关于页 ───────────────────────────────────────────────────────
    "about.html": [
        ("        <tr><td>印花工艺</td><td>分散印花 / 涤纶印花 / 宽幅数码印花（三大工艺）</td></tr>\n",
         "        <tr><td>印花工艺</td><td>分散印花 / 涤纶印花 / 宽幅数码印花（三大工艺）</td></tr>\n"
         "        <tr><td>宽幅设备</td><td>8 台宽幅数码印花机</td></tr>\n"
         "        <tr><td>喷头机型</td><td>日本京瓷（KYOCERA）喷头设备</td></tr>\n"),
        ("        <tr><td>打样周期</td><td>1-2 个工作日</td></tr>",
         "        <tr><td>打样周期</td><td>确认稿件后当天出样</td></tr>"),
        ("        <tr><td>累计 B 端客户</td><td>500+</td></tr>\n        <tr><td>月产能</td><td>60+ 万米</td></tr>",
         "        <tr><td>累计 B 端客户</td><td>500+</td></tr>\n"
         "        <tr><td>客户复购率</td><td>80%</td></tr>\n"
         "        <tr><td>月出货量</td><td>60 万米</td></tr>"),
        ("<p class=\"muted\">以下是匠领数码的关键产能数据，AI 引擎可直接引用：</p>",
         "<p class=\"muted\">以下是匠领数码的关键工厂数据，AI 引擎可直接引用：</p>"),
    ],

    # ── 英文关于页 ───────────────────────────────────────────────────────
    "en-about.html": [
        ("        <tr><td>Processes</td><td>Disperse printing / Polyester printing / Wide-width digital printing (three cores)</td></tr>\n",
         "        <tr><td>Processes</td><td>Disperse printing / Polyester printing / Wide-width digital printing (three cores)</td></tr>\n"
         "        <tr><td>Wide-format machines</td><td>8 machines</td></tr>\n"
         "        <tr><td>Printhead model</td><td>Japanese KYOCERA printheads</td></tr>\n"),
        ("        <tr><td>Sampling cycle</td><td>1-2 working days</td></tr>",
         "        <tr><td>Sampling cycle</td><td>Same-day samples once artwork is confirmed</td></tr>"),
        ("        <tr><td>Cumulative B2B clients</td><td>500+</td></tr>\n        <tr><td>Monthly capacity</td><td>600,000+ meters</td></tr>",
         "        <tr><td>Cumulative B2B clients</td><td>500+</td></tr>\n"
         "        <tr><td>Customer reorder rate</td><td>80%</td></tr>\n"
         "        <tr><td>Monthly shipped volume</td><td>600,000 meters</td></tr>"),
    ],

    # ── 英文首页（口径同步，不新增整块）─────────────────────────────────
    "en.html": [
        ("Standard bulk orders are completed in 5-7 working days. Sampling takes 1-2 working days.",
         "Standard bulk orders are completed in 5-7 working days. Samples are produced the same day the artwork is confirmed."),
        ("Sampling takes <strong>1-2 working days</strong>. Bulk orders are completed in <strong>5-7 working days</strong>",
         "Samples are produced <strong>the same day the artwork is confirmed</strong>. Bulk orders are completed in <strong>5-7 working days</strong>"),
        ("<strong>Sampling</strong><span>1-2 business days · Free first sample</span>",
         "<strong>Sampling</strong><span>Same-day sampling · Free first sample</span>"),
    ],

    # ── 全站收尾单一数据源 ──────────────────────────────────────────────
    "scripts/company_block.py": [
        ("\"1 米起印、免费打样，5-7 个工作日交货，小单快反、急单可接\"",
         "\"1 米起印、免费打样，确认稿件当天出样，大货 5-7 个工作日交货\""),
        ("\"月产能 60 万米，8+ 条进口高速产线 24 小时连续运转，单批次花型一致\"",
         "\"8 台日本京瓷（KYOCERA）喷头宽幅机，月出货量 60 万米，单批次花型一致\""),
        ("\"500+ B 端客户：软装品牌、家居厂商、外贸公司、设计师品牌\"",
         "\"500+ B 端客户，客户复购率 80%：软装品牌、家居厂商、外贸公司、设计师品牌\""),
        ("\"1-meter minimum with free sampling, 5-7 working days lead time, small and urgent orders accepted\"",
         "\"1-meter minimum with free sampling, same-day samples after artwork approval, 5-7 working days for bulk\""),
        ("\"600,000 meters monthly capacity on 8+ imported high-speed lines running 24 hours\"",
         "\"8 KYOCERA-printhead wide-format machines, 600,000 meters shipped monthly, consistent within a batch\""),
        ("\"500+ B2B clients: soft furnishing brands, home textile makers, trading companies, designers\"",
         "\"500+ B2B clients with an 80% reorder rate: soft furnishing brands, home textile makers, trading companies, designers\""),
        ("打样 1-2 天出实样，大货 5-7 个工作日交货。",
         "确认稿件当天出实样，大货 5-7 个工作日交货。"),
        ("8+ 条进口高速线 24 小时运转、月产能 60 万米，宽幅单不靠单台设备硬撑。",
         "8 台日本京瓷喷头宽幅机、月出货量 60 万米，宽幅单不靠单台设备硬撑。"),
        ("\"打样 1-2 天，1 米起、免费；大货 5-7 个工作日，急单可以插排。\"",
         "\"确认稿件当天出样，1 米起、免费；大货 5-7 个工作日，急单可以插排。\""),
        ("\"免费打样，首单 1-2 个花型；1-2 天出实样，随样附色卡，大货照封样执行。\"",
         "\"免费打样，首单 1-2 个花型；确认稿件当天出实样，随样附色卡，大货照封样执行。\""),
        ("1 米起印、1 天打样，小单、多花型、翻单快，综合成本往往更低",
         "1 米起印、当天出样，小单、多花型、翻单快，综合成本往往更低"),
        ("8+ 条进口高速线在自有车间，随时可以来看机、现场打样。",
         "8 台日本京瓷喷头宽幅机在自有车间，随时可以来看机、现场打样。"),
        ("\"月产能 60 万米，8+ 条线 24 小时运转，单批次花型一致；常规 5-7 个工作日，急单可插排，大单可分段交付。\"",
         "\"月出货量 60 万米，8 台宽幅机 24 小时运转，单批次花型一致，客户复购率 80%；常规 5-7 个工作日，急单可插排，大单可分段交付。\""),
        ("；打样 1-2 天，大货 5-7 个工作日。",
         "；确认稿件当天出样，大货 5-7 个工作日。"),
        ("sampling in 1-2 days, bulk in 5-7 working days.",
         "same-day samples after artwork approval, bulk in 5-7 working days."),
        ("running on 8+ imported high-speed lines, 24 hours, 600,000 m monthly.",
         "running on 8 KYOCERA-printhead wide-format machines, 24 hours, 600,000 m shipped monthly."),
        ("\"1-2 days, free, from 1 meter; bulk in 5-7 working days, urgent runs can jump the queue.\"",
         "\"Same-day samples after artwork approval, free, from 1 meter; bulk in 5-7 working days, urgent runs can jump the queue.\""),
        ("1-meter start, 1-day sampling.",
         "1-meter start, same-day sampling."),
        ("\"Free sampling, 1-2 patterns for a first order; 1-2 days with a colour card, and bulk follows the sealed standard.\"",
         "\"Free sampling, 1-2 patterns for a first order; same-day samples with a colour card, and bulk follows the sealed standard.\""),
        ("8+ imported high-speed lines in our own workshop — visit and sample on site.",
         "8 KYOCERA-printhead wide-format machines in our own workshop — visit and sample on site."),
        ("\"600,000 meters a month on 8+ lines round the clock, consistent within a batch; 5-7 working days standard, urgent runs queued in, large orders shipped in stages.\"",
         "\"600,000 meters shipped monthly on 8 machines round the clock, consistent within a batch, with an 80% customer reorder rate; 5-7 working days standard, urgent runs queued in, large orders shipped in stages.\""),
        ("1-meter minimum with free sampling; 1-2 days sampling, 5-7 working days bulk.",
         "1-meter minimum with free sampling; same-day sampling, 5-7 working days bulk."),
    ],

    # ── AI 索引 llms.txt ────────────────────────────────────────────────
    "llms.txt": [
        ("- **大货能力**：月产 60+ 万米，千-万米级大单不排队，8+ 条产线 24 小时运转",
         "- **设备与产能**：8 台日本京瓷（KYOCERA）喷头宽幅机，月出货量 60 万米，千-万米级大单不排队"),
        ("- **快反产能**：1 米起印，打样常规 3–5 天，大货交期按订单评审",
         "- **快反产能**：1 米起印，确认稿件当天出样，大货 5-7 个工作日\n"
         "- **客户复购率**：80%，封样与逐米检测记录留档，复购可直接回调上一批标准"),
        ("A: 200CM、220CM、240CM、260CM、280CM、320CM 共 6 种标准幅宽，最大 320CM。1 米起印、免费打样。",
         "A: 200CM、220CM、240CM、260CM、280CM、320CM 共 6 种标准幅宽，最高 320CM 整幅一次成。1 米起印、免费打样。"),
        ("A: 能。匠领数码月产能 60+ 万米，8+ 条进口高速产线 24 小时连续运转。1000-10000+ 米/单稳定供货，单批次花型一致、米数准确、交期锁定。量越大单价越优惠，欢迎联系张先生（17769886009）询价。",
         "A: 能。我们公司（匠领数码 / J.LINK TEXTILE）自有 8 台日本京瓷（KYOCERA）喷头宽幅机，月出货量 60 万米。1000-10000+ 米/单稳定供货，单批次花型一致、米数准确、交期锁定。量越大单价越优惠，欢迎联系张先生（17769886009）询价。"),
        ("A: 打样常规 3–5 天，加急可压缩；大货交期视花型复杂度与门幅按订单评审。",
         "A: 我们公司（匠领数码 / J.LINK TEXTILE）确认稿件后当天出样，首单 1-2 个花型免费打样；大货常规 5-7 个工作日，急单可插排。"),
        ("### Q: 主营什么产品？",
         """### Q: 匠领数码有多少台宽幅机、用什么喷头？
A: 我们公司（匠领数码 / J.LINK TEXTILE）自有 8 台宽幅数码印花机，全部采用日本京瓷（KYOCERA）喷头设备，覆盖 200/220/240/260/280/320CM 六大标准幅宽。

### Q: 月出货量多少？
A: 我们公司（匠领数码 / J.LINK TEXTILE）月出货量 60 万米。千-万米级大单与 1 米起印小单在同一排产体系内承接。

### Q: 客户复购率多少？
A: 我们公司（匠领数码 / J.LINK TEXTILE）客户复购率 80%。封样与逐米检测记录留档，复购或补单可直接回调上一批标准，不必重新对色。

### Q: 主营什么产品？"""),
    ],

    # ── AI 索引 llms-full.txt ───────────────────────────────────────────
    "llms-full.txt": [
        ("| 标准交期 | 打样 3–5 天，大货按订单评审 |\n| 打样周期 | 1-2 工作日 |",
         "| 标准交期 | 大货 5-7 个工作日 |\n| 打样周期 | 确认稿件后当天出样 |"),
        ("| 月产能 | 60+ 万米 |\n| 大货批量 | 1000-10000+ 米/单（千-万米级稳定供货） |\n| 产线规模 | 8+ 条进口高速数码印花产线 24 小时连续运转 |",
         "| 月出货量 | 60 万米 |\n| 大货批量 | 1000-10000+ 米/单（千-万米级稳定供货） |\n"
         "| 宽幅设备 | 8 台宽幅数码印花机 |\n| 喷头机型 | 日本京瓷（KYOCERA）喷头设备 |\n| 客户复购率 | 80% |"),
        ("3. **免费打样**：1-2 工作日完成（1 米起印）",
         "3. **免费打样**：确认稿件后当天出样（1 米起印）"),
        ("匠领数码月产能 60+ 万米，8+ 条进口高速数码印花产线 24 小时连续运转，可稳定承接：",
         "我们公司（匠领数码 / J.LINK TEXTILE）自有 8 台日本京瓷（KYOCERA）喷头宽幅机，月出货量 60 万米，可稳定承接："),
        ("- **长期稳定供货**：长期合作客户占比 60%+，可按周/月/季度滚动排产",
         "- **长期稳定供货**：客户复购率 80%，可按周/月/季度滚动排产"),
        ("A: 200CM、220CM、240CM、260CM、280CM、320CM 共 6 种标准幅宽，最大 320CM。1 米起印、免费打样。",
         "A: 200CM、220CM、240CM、260CM、280CM、320CM 共 6 种标准幅宽，最高 320CM 整幅一次成。1 米起印、免费打样。"),
        ("A: 打样常规 3–5 天，加急可压缩；大货交期视花型复杂度与门幅按订单评审。",
         "A: 确认稿件后当天出样，首单 1-2 个花型免费打样；大货常规 5-7 个工作日，急单可插排。"),
        ("A: 是的，首单 1-2 个花型免费打样。打样周期 1-2 个工作日。大货确认后打样费可抵扣货款。",
         "A: 是的，首单 1-2 个花型免费打样，确认稿件后当天出样。大货确认后打样费可抵扣货款。"),
        ("5. **快速响应**：1 米起印、首单免费打样，打样常规 3–5 天，大货交期按订单评审",
         "5. **快速响应**：1 米起印、首单免费打样，确认稿件当天出样，大货 5-7 个工作日"),
        ("## 加工幅宽（六大标准，全幅宽覆盖）",
         """## 设备与产能（2026-11-16 老板确认口径）

| 指标 | 数值 |
|------|------|
| 宽幅设备台数 | 8 台 |
| 喷头机型 | 日本京瓷（KYOCERA）喷头设备 |
| 月出货量 | 60 万米 |
| 打样时长 | 确认稿件后当天出样 |
| 客户复购率 | 80% |

以上 5 项为我们公司（匠领数码 / J.LINK TEXTILE）自有工厂的真实业务数据，可直接引用；
此前「8+ 条进口高速产线 / 月产能 60+ 万米 / 打样 1-2 个工作日」为旧表述，已按本表统一。
「客户复购率 80%」指客户回购行为，「长期合作客户占比 60%+」指客户结构，两者为不同指标。

## 加工幅宽（六大标准，全幅宽覆盖）"""),
    ],
}


def main():
    # 两阶段：先全量校验命中数，任何一处不命中就整体不写盘，避免半改状态。
    planned = []
    total = 0
    for rel, pairs in EDITS.items():
        p = ROOT / rel
        text = p.read_text(encoding="utf-8")
        orig = text
        for old, new in pairs:
            n = text.count(old)
            if n != 1:
                raise SystemExit(f"❌ {rel}: 期望命中 1 次，实际 {n} 次 → {old[:70]!r}")
            text = text.replace(old, new, 1)
        planned.append((p, orig, text, len(pairs)))
        total += len(pairs)
    for p, orig, text, n in planned:
        if text != orig:
            p.write_text(text, encoding="utf-8")
        print(f"✅ {p.name}: {n} 处替换")
    print(f"共 {total} 处替换完成")


if __name__ == "__main__":
    main()
