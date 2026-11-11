# -*- coding: utf-8 -*-
"""一次性改写：把每日快报 12 篇中文选题里的「拼接类 + 窄幅恐惧钩子」全部换成正面整幅表述。

2026-11-11 老板定：以后发的内容必须符合最新收录规则。
旧池子里 67 行含「拼接 / 拼缝 / 窄幅」等禁用词，且多为「窄幅→拼接→对花错位」
这类非痛点恐惧钩子，属永久禁区。本脚本按行号精确替换，只改中文选题源，
不重建、不改动任何已上线页面；以后每天轮选生成的快报即为干净内容。
按行号 + 保留原换行/缩进的字节级替换，避免整文件 diff。
"""
import re
from pathlib import Path

POOL = Path(__file__).with_name("knowledge_insights_pool.py")

LINES = {
    22: r'"h1": "2026 窗帘印花流行趋势：整幅一次成与大花回当道",',
    23: r'"hero": "2026 年窗帘定制更看重整幅连续花型与高还原。我们按 200/220/240/260/280/320CM 六档幅宽整幅一次成、无切断，契合大花回壁画感需求。",',
    24: r'"meta": "2026 窗帘印花趋势：整幅一次成、大花回、高色彩还原，宽幅数码印花 200-320CM 六档幅宽承接落地帘与遮光帘定制。",',
    26: r'"md": """2026 年窗帘定制的设计语言明显转向「整幅感」：一幅落地帘从顶到底图案连续、对花精准，视觉一气呵成。这背后是宽幅数码印花设备的成熟，也是软装审美从「遮光功能」走向「墙面艺术」的体现。',
    29: r'- **整幅一次成成为标配**：2.8-3.2 米高落地帘整幅一次成、无切断，墙面视觉严丝合缝。',
    40: r'整幅一次成最适合 2.4 米以上的落地帘、遮光帘与壁画级墙布；小窗、半帘按 200CM 档位出图更省料。大花回图案对色彩一致性的要求更高，务必先打样封样再放单。',
    47: r'总结：2026 窗帘趋势是整幅、大花回、高还原；宽幅数码印花以整幅一次成 + 8 色 + ICC 管理承接这类订单，采购认准三项硬指标即可。""",',
    49: r'("2026 窗帘印花最明显的趋势是什么？", "整幅一次成成为标配，大花回与写真级图案走俏，且小批量多花型快反需求上升，新品上架从按月变按周。"),',
    50: r'("整幅窗帘靠什么实现？", "靠 200/220/240/260/280/320CM 六档幅宽的宽幅数码印花设备整幅一次成、无切断，墙面视觉连续。"),',
    53: r'("整幅一次成适合所有窗帘吗？", "最适合 2.4 米以上落地帘、遮光帘与壁画墙布；小窗半帘按 200CM 档位出图即可，按成品尺寸选档更省料。"),',
    57: r'"确认工厂具备 200/220/240/260/280/320CM 六档标准幅宽与整幅一次成能力",',
    68: r'("整幅窗帘一定更贵", "按成品尺寸选合适幅宽档位反而省料，整幅一次成省去对花工序与损耗，综合成本可控、视觉与品质更稳。"),',

    128: r'"hero": "酒店工程帘要统一花色、稳定供货、可控交期。宽幅数码印花以整幅一次成 + 封样制度 + 5-7 个工作日交期，适配连锁标准化的硬要求。",',
    129: r'"meta": "酒店工程帘选宽幅数码印花：整幅一次成、封样控色、5-7 个工作日交期、多批次翻单一致，柯桥工厂直供。",',
    135: r'- **整幅完整**：落地帘、壁画级墙布整幅一次成、无切断，大堂与客房视觉更高级。',
    139: r'我们按 200/220/240/260/280/320CM 六档幅宽整幅一次成，3 米高帘一次出图、图案连续，省去现场对花工序，施工更快、损耗更低。对工程方而言，少一道现场对花，等于少一个工期与返工变量。',
    145: r'整幅一次成最适合落地帘、遮光帘、工程墙布与壁画；短帘或成品帘头按 200CM 档位出图即可，需按部位选幅宽。工程单务必先封样，并把封样留档到项目结束。',
    155: r'("宽幅数码怎么解决？", "封样为唯一标准、ICC 曲线锁机差保证多批次一致，我们按六大标准幅宽整幅一次成、无切断。"),',
    158: r'("工程墙布也要整幅吗？", "壁画级与大面积墙布最吃整幅红利，整幅一次成视觉更完整、严丝合缝，施工也更快。"),',
    168: r'"整幅落地帘确认整幅一次成、省去现场对花，减少工期变量",',
    173: r'("整幅一定更贵很多", "按档位出图省下对花工序与损耗，工程单综合成本可控，且返工率更低。"),',

    239: r'- **宽幅能力**：窗帘墙布常按 200-320CM 六档幅宽整幅一次成，海外买家尤其看重整幅图案连续、无切断。',
    271: r'"确认 200-320CM 六档幅宽，按成品尺寸选档、整幅一次成",',
    493: r'色彩稳定性依赖体系而非个人：8 色墨水 1670 万色打底，ICC 曲线把设备差异量化锁定；200/220/240/260/280/320CM 六档幅宽下整幅一次成，同幅内色相一致；4 级以上色牢度保证耐日晒耐水洗，后期不褪。',

    594: r'"hero": "墙布、壁画级墙面讲究一面墙一张图。宽幅数码印花整幅一次成、无切断，施工更省、视觉更完整。",',
    595: r'"meta": "墙布无缝施工优势：宽幅数码印花整幅一次成、无切断，壁画级墙面视觉完整、严丝合缝、施工更快。",',
    597: r'"md": """墙布与无缝壁画的核心卖点是一面墙图案连续、看不到断点。我们按 200/220/240/260/280/320CM 六档幅宽整幅一次成，让「一面墙一张图」成为常态。',
    600: r'- **整幅无切断**：200-320CM 一次出图，墙面视觉一气呵成，近看也无断点。',
    602: r'- **施工更快**：整幅一次成省去现场对花工序，损耗更低，工期更可控。',
    603: r'- **大花纹还原好**：渐变、写真级图案整幅连续，完整性高。',
    609: r'下单前提供墙面尺寸与花回方向，工厂按幅宽整幅出图；施工时由熟练师傅对位铺贴，虽已一次成图，仍需规范上胶与对位。异形或超高墙面要提前沟通出图方案。',
    612: r'整幅无缝最适合客厅背景墙、卧室壁画、酒店工程墙布、商业大面幅图案墙；小面积图案可按 200CM 档位出图，按实际尺寸选档更省料。',
    619: r'总结：墙布无缝靠整幅一次成、无切断，按花回走布保连续，施工省、视觉完整，适合壁画级与工程墙布。""",',
    621: r'("墙布无缝是怎么做到的？", "宽幅设备 200-320CM 整幅一次成、无切断，纵向按花回精确走布保证连续。"),',
    622: r'("对施工有什么好处？", "整幅一次成省去现场对花工序，损耗更低、施工更快，墙面视觉更完整。"),',
    623: r'("大花纹会不会被切断？", "整幅一次成、无切断，渐变与写真级图案完整还原。"),',
    625: r'("整幅一定比小档位好吗？", "大面幅墙面视觉完整度更高、施工更快；小面积按 200CM 档位出图更省料，按成品尺寸选档即可。"),',
    635: r'"确认整幅一次成后的工期与损耗预估",',
    639: r'("无缝墙布一定贵很多", "整幅一次成省下现场对花工序与损耗，综合成本可控，且返工率低。"),',
    640: r'("按 200CM 档位出图也一样", "整幅一次成、无切断，图案严丝合缝，近看也没有断点，视觉完整度更高。"),',

    715: r'产线 OEKO-TEX 合规、与 SGS 合作、8 色墨水 ΔE<1.5 保还原，再叠加 200-320CM 六档幅宽整幅一次成、无切断，出口单与海外工程都能接。小批量快反（1米起印、免费打样）还能帮跨境卖家低库存试款。',
    745: r'"核查 200/220/240/260/280/320CM 六档幅宽与整幅一次成能力",',
    857: r'"确认工厂 200-320CM 六档幅宽与整幅一次成、无切断",',
    948: r'封样制度依托稳定产线：8 色墨水 1670 万色打底，ICC 曲线把设备差异量化；200-320CM 六档幅宽整幅一次成让同幅内色相一致；4 级以上色牢度保证不褪；1米起印、免费打样让封样本身零门槛。',

    1056: r'- **整幅床盖（大面幅）**：宽幅数码印花整幅一次成、无切断，适合大尺寸床盖与被面。',
    1065: r'先用 1-2 花型免费打样验证手感色牢度，小批量上架测款，爆款加单封样锁色。床盖等大尺寸按 280CM 或 320CM 档位整幅一次成，图案连续更完整。',
    1079: r'("整幅床盖为什么好？", "宽幅数码整幅一次成、无切断，大尺寸图案连续完整，视觉更完整。"),',
    1089: r'"整幅床盖确认 200-320CM 六档幅宽、整幅一次成",',
    1097: r'("大尺寸床盖要分两次印吗", "不用。宽幅数码 200-320CM 整幅一次成，大床盖可完整出图、图案连续。"),',

    1159: r'"hero": "落地帘、背景墙讲究一幅到底。宽幅设备 200-320CM 整幅一次成、无切断，纵向按花回走布，图案严丝合缝。",',
    1160: r'"meta": "宽幅设备整幅出图：200/220/240/260/280/320CM 六档幅宽整幅一次成、无切断，按花回走布保连续，施工与品质双收益。",',
    1162: r'"md": """窗帘、墙布要做大尺寸，我们按 200/220/240/260/280/320CM 六档幅宽整幅一次成，一次出图、图案连续，带来实打实的红利。',
    1164: r'## 六大标准幅宽怎么选',
    1165: r'做 3 米高落地帘，直接选 320CM 档位整幅出图，从顶到底一次成、无切断；2.4 米左右的帘选 240CM 或 260CM 档位，按成品尺寸选档更省料。',
    1168: r'- **整幅无切断**：200-320CM 整幅一次成，一面墙/一幅帘一气呵成。',
    1170: r'- **省工序**：整幅一次成省去现场对花，损耗与工时都降。',
    1171: r'- **品质稳**：图案整幅连续，视觉更完整，近看无断点。',
    1177: r'下单按实际幅宽选档（不必非 320CM，合适档位更省料）；提供花回方向与尺寸，工厂整幅一次成出图；施工仍需规范上胶对位。',
    1180: r'整幅红利最适合落地帘、遮光帘、无缝墙布、工程墙布与大床盖；小窗半帘按 200CM 档位出图即可。',
    1187: r'总结：宽幅设备 200-320CM 整幅一次成、无切断，纵向按花回走布，图案严丝合缝，施工与品质双收益。""",',
    1189: r'("高帘怎么选幅宽档位？", "3 米高落地帘选 320CM 档位整幅一次成，2.4 米左右选 240/260CM 档位，按成品尺寸选档更省料。"),',
    1190: r'("整幅一次成省了什么？", "一次出图、图案连续，省去现场对花工序，损耗与工时都降。"),',
    1191: r'("整幅对大花纹有什么好处？", "无切断，渐变与写真级图案完整还原，壁画级更出彩。"),',
    1193: r'("施工还要注意什么？", "虽已整幅一次成，仍需规范上胶与对位，异形/超高墙提前沟通出图方案。"),',
    1199: r'"确认整幅一次成、无切断，纵向按花回连续",',
    1203: r'"确认整幅出图后的工期与损耗预估",',
    1207: r'("用 200CM 档位出图也一样", "整幅一次成、无切断，图案严丝合缝，近看也没有断点。"),',
    1208: r'("整幅一定更费料", "按合适档位整幅出图反而更省料，综合更省。"),',
    1212: r'["对比维度", "200 / 220CM 档", "260 / 280 / 320CM 档"],',
    1213: r'["适用成品", "小窗半帘、抱枕、帘头", "落地帘、遮光帘、墙布、大床盖"],',
    1214: r'["对花", "按花回走布", "整幅一次成，图案严丝合缝"],',
    1215: r'["工序", "常规铺贴", "省去现场对花工序"],',
    1216: r'["幅宽选择", "按成品尺寸选最省料的一档", "大面幅一次出图、无切断"],',
    1217: r'["适合", "小尺寸软装", "大面幅软装与工程单"],',
    1302: r'体系依赖稳定产线：8 色墨水 1670 万色打底，ICC 曲线量化锁机差；200-320CM 六档幅宽整幅一次成让同幅内色相一致；4 级以上色牢度保证耐日晒耐水洗；8+ 高速线月产 60 万米以上，翻单不断供；1米起印、免费打样让新花型低门槛试水。',
}

# 英文选题同样清掉「narrow / splicing / seam 恐惧钩子」，并去掉正文夹的中文。
# 用三单引号原始字符串，内容里的双引号、转义引号、撇号都无需额外处理。
EN_LINES = {
    108: r'''"Confirm six standard widths 200-320CM with continuous full-width output",''',
    119: r'''("Seamless drapes must cost more", "Choosing the right width tier saves aligning steps and waste, so one-pass full-width printing is not necessarily pricier and is steadier."),''',
    190: r'''We print a 3m drape in one continuous pass across our six standard widths 200-320CM, so the pattern runs top to bottom without a break and on-site matching is unnecessary — faster install, lower waste. For project buyers, one less on-site aligning step means one less schedule and rework variable.''',
    196: r'''Full-width suits drapes, blackout and mural wallcovering; short valances can use the 200CM tier. Always seal the sample and archive it through project close.''',
    291: r'''"md": """Cross-border soft-furnishing competes on speed: fast launches, fast replenishment, low inventory risk. But many sellers stall at factory selection — plenty of printers exist, yet few meet wide-format + small-batch + export compliance + stable lead together. When choosing a digital printing factory, don't judge on price alone — check four hard metrics.''',
    294: r'''- **Wide-format**: curtains and wallcoverings are produced across six standard widths 200-320CM in one continuous pass; overseas buyers value uninterrupted patterns.''',
    319: r'''("Why small-batch matters?", "Fast launches with zero inventory risk; 1-meter minimum and free sampling fit test-then-scale cycles."),''',
    326: r'''"Confirm six widths 200-320CM and continuous full-width output",''',
    649: r'''"md": """The core selling point of wallcoverings and seamless murals is one wall with a continuous pattern and no visible breaks. We print across six standard widths 200-320CM in one continuous pass, making \"one wall, one image\" the norm.''',
    664: r'''Full-width seamless fits living-room feature walls, bedroom murals, hotel project wallcovering and commercial large-surface walls; smaller areas can use the 200CM tier to save material.''',
    677: r'''("Is full-width always better?", "Large surfaces gain completeness and faster installation; the 200CM tier suits smaller areas, so choose the tier by finished size."),''',
    692: r'''("Using the 200CM tier is the same", "One continuous pass keeps the pattern unbroken and precisely matched; full-width output is truly seamless."),''',
    888: r'''Keqiao's scale is the guarantee: one of the world's largest textile distribution hubs, dense fabric and dyeing capacity; local wide-format lines commonly offer six widths 200-320CM, 8 inks, 1-meter minimum and 5-7 day lead, plus OEKO-TEX compliance for export markets.''',
    906: r'''("Is export easy in Keqiao?", "Logistics, testing, certification ready; OEKO-TEX/SGS one-stop, no barrier to export."),''',
    1151: r'''("Oversized covers need two passes", "No. Wide-format 200-320CM prints the whole cover in one continuous pass."),''',
    1222: r'''"hero": "Tall drapes and feature walls call for one continuous image. Our 200-320CM wide-format lines print the whole width in a single pass — no cut, repeat-accurate feed, no matching step.",''',
    1225: r'''"md": """For large curtains and wallcoverings, we print across six standard widths 200/220/240/260/280/320CM in one continuous pass, so the pattern stays whole from edge to edge.''',
    1227: r'''## Choosing among six standard widths''',
    1228: r'''A 3m floor drape uses the 320CM tier for one continuous print from top to bottom; a 2.4m drape uses the 240CM or 260CM tier. Choosing the tier by finished size saves material.''',
    1231: r'''- **One continuous pass**: 200-320CM full-width direct printing, no cut from edge to edge.''',
    1233: r'''- **Fewer steps**: one continuous pass removes on-site aligning, cutting waste and labor.''',
    1234: r'''- **Stable quality**: the pattern stays whole, with no visible break up close.''',
    1240: r'''Pick the right width by actual size (not always 320CM — right tier saves cloth); provide repeat direction and dimensions; still standardize gluing and positioning at install.''',
    1250: r'''Summary: wide-format printing across six standard widths 200-320CM delivers one continuous pass with no cut; repeat-accurate feed keeps the pattern whole, gaining on both install and quality.""",''',
    1252: r'''("Which width tier for a tall drape?", "A 3m drape uses the 320CM tier in one continuous pass; around 2.4m uses 240/260CM. Choose by finished size."),''',
    1253: r'''("What does wide-format save?", "One continuous pass with repeat-accurate feed, no on-site aligning, less waste and labor."),''',
    1254: r'''("Benefit for big motifs?", "No cut in the pattern; gradients and photo-level patterns stay intact, murals shine."),''',
    1256: r'''("Install cautions?", "One continuous pass, but still standardize gluing/positioning; pre-discuss the output plan for irregular walls."),''',
    1262: r'''"Confirm one continuous pass and repeat-accurate feed",''',
    1266: r'''"Estimate schedule and waste after one continuous pass",''',
    1270: r'''("Using the 200CM tier is the same", "One continuous pass keeps the pattern unbroken and precisely matched, with no visible break."),''',
    1271: r'''("Full-width wastes cloth", "Choosing the right tier for the finished size actually saves material; total cost is lower."),''',
    1275: r'''["Dimension", "200 / 220CM tier", "260 / 280 / 320CM tier"],''',
    1276: r'''["Best for", "Small windows, valances, cushions", "Drapes, blackout, wallcovering, bedspreads"],''',
    1277: r'''["Matching", "Repeat-accurate feed", "One continuous pass, pattern unbroken"],''',
    1278: r'''["Steps", "Standard installation", "No on-site aligning step"],''',
    1279: r'''["Width choice", "Pick the most economical tier for the finished size", "Large surfaces printed whole, no cut"],''',
    1280: r'''["Typical order", "Small soft furnishings", "Large surfaces and project orders"],''',
}


def main():
    raw = POOL.read_bytes()
    lines = raw.splitlines(keepends=True)
    all_lines = {**LINES, **EN_LINES}
    for n, new in all_lines.items():
        old = lines[n - 1]
        eol = b"\r\n" if old.endswith(b"\r\n") else b"\n"
        indent = re.match(rb"[ \t]*", old).group()
        lines[n - 1] = indent + new.encode("utf-8") + eol
    POOL.write_bytes(b"".join(lines))
    print(f"已改写 {len(all_lines)} 行（中文 {len(LINES)} + 英文 {len(EN_LINES)}）→ {POOL.name}")


if __name__ == "__main__":
    main()
