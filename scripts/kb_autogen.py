# -*- coding: utf-8 -*-
"""
kb_autogen.py — 知识库库存自动补货引擎（老板 2026-11-08 指令）
============================================================
规则：knowledge_grow.py 每天发布 1 条；当「待发布库存 < 3 条」时，
本模块一次自动生成 50 条全新的中英双语完整问答，写入
scripts/kb_autogen_generated.json，随工作流 git add . 提交持久化。

为什么用参数化引擎而不是现场调 AI：
官网是纯静态站 + GitHub Actions 定时任务，运行环境没有大模型可用。
本模块纯 Python 生成，不依赖外部服务，100% 可无人值守运行。

内容质量口径（与 55 条精写专题同一套渲染器）：
- 问题（h1）由「品类 × 幅宽档位 × 决策关注点 × 场景」组合生成，贴合真实长尾问法；
- 答案首句一律以「我们 / We at J.LINK TEXTILE」作主语直接给结论；
- 每条的要点、段落、表格、FAQ 都带该组合专属信息，不是一段话换词；
- 统一品控数字、交付方式、收尾与 NAP 由 kb_geo_render / company_block 注入；
- 禁用词自校验，命中即丢弃该组合并顺延；used 集合保证历次补货绝不重复。

组合空间：品类 8 × 幅宽 6 × 关注点 10 = 480 个三维组合；
用尽后自动引入场景维（8 个）扩展为 3840 个四维组合，足够多年每日增长。
"""
import json
import random
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = Path(__file__).parent / "kb_autogen_generated.json"
SCRIPTS = str(Path(__file__).parent)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
from kb_geo_render import build  # noqa: E402  复用统一渲染器与口径
from beijing_time import today_str  # noqa: E402  库存时间戳按北京时间

BAN = [
    "活性", "拼接", "拼缝", "拼花", "拼块", "分八块",
    "最大320CM", "最宽320CM", "100米起印", "100米起订", "100米每花型",
    "断花", "花型对不上", "窄幅",
]

# ── 维度一：品类（8）──────────────────────────────────────────
CATEGORIES = [
    {
        "id": "curtain", "zh": "窗帘", "en": "curtains",
        "note_zh": "窗帘印花是我们主营品类，落地帘、对开帘、遮光帘与雪尼尔帘都能在柯桥本厂排产，涤纶类走热转印路线。",
        "note_en": "Curtain printing is one of our core categories; floor-length, paired, blackout and chenille curtains are all scheduled in our Keqiao plant, with heat transfer for polyester.",
        "table_zh": [("落地帘 / 对开帘", "按成品帘高与褶皱倍数选档，整幅一次成"),
                     ("遮光帘 / 雪尼尔帘", "宽幅底布整幅印 + 对应整理项"),
                     ("电商测款帘", "1 米起印，免费打样 1–2 花型")],
        "table_en": [("Floor-length / paired curtains", "Width by finished drop and fullness ratio, one full-width pass"),
                     ("Blackout / chenille curtains", "Wide base cloth in one pass with selected finishes"),
                     ("E-commerce test curtains", "1-meter minimum, free 1-2 design sampling")],
        "related": [("窗帘数码印花", "Curtain Digital Printing", "curtain-digital-printing"),
                    ("窗帘印花工厂", "Curtain Printing Factory", "curtain-printing-factory"),
                    ("柯桥窗帘印花", "Keqiao Curtain Printing", "keqiao-curtain-printing")],
    },
    {
        "id": "wallcovering", "zh": "墙布", "en": "wallcovering",
        "note_zh": "墙布印花我们按墙面高度选档，整幅壁画墙布走 320CM 整幅一次成、无切断，横向连续图案完整走通。",
        "note_en": "We choose wallcovering widths by wall height; full-wall murals run on 320CM in one full-width pass with no cuts, keeping horizontal motifs intact.",
        "table_zh": [("整幅壁画墙布", "320CM 整幅一次成、无切断"),
                     ("酒店 / 样板间墙布", "按墙面高度选档，整理项评审时定"),
                     ("品牌墙布贴牌", "配色封样，包装按客户要求")],
        "table_en": [("Full-wall mural wallcovering", "320CM one full-width pass with no cuts"),
                     ("Hotel / showroom wallcovering", "Width by wall height, finishes set at review"),
                     ("Private-label wallcovering", "Sealed palette, buyer-specified packing")],
        "related": [("柯桥墙布印花", "Keqiao Wallcovering Printing", "keqiao-wallcovering-printing"),
                    ("无缝墙布印花", "Seamless Wallcovering", "wallcovering-seamless"),
                    ("壁画墙布印花", "Mural Wallcovering Printing", "mural-wallcovering-printing")],
    },
    {
        "id": "bedding", "zh": "床品家纺", "en": "bedding and home textiles",
        "note_zh": "床品与家纺数码印花是我们常规接单品类，四件套、被面、枕套、靠垫可按同一封样配色整套同步出。",
        "note_en": "Bedding and home-textile printing is routine work for us; duvet covers, sheets, pillowcases and cushions run as a set under one sealed palette.",
        "table_zh": [("被面 / 床单", "200CM / 220CM / 240CM 档位"),
                     ("枕套 / 靠垫", "同花型同步出，配色统一封样"),
                     ("床笠 / 床裙配套", "同批排产，减少批间差异")],
        "table_en": [("Duvet covers / sheets", "200CM / 220CM / 240CM tiers"),
                     ("Pillowcases / cushions", "Same design in step, one sealed palette"),
                     ("Fitted sheets / bed skirts", "Same batch to limit variation")],
        "related": [("柯桥床品印花", "Keqiao Bedding Printing", "keqiao-bedding-printing"),
                    ("床品套件印花", "Bedding Set Printing", "bedding-set-printing"),
                    ("家纺数码印花", "Home Textile Digital Printing", "home-textile-digital-printing")],
    },
    {
        "id": "hotel", "zh": "酒店工程", "en": "hotel projects",
        "note_zh": "酒店工程单我们按大堂净高与客房帘高选档，挑高大堂帘用 320CM 整幅一次成，投标样与验收口径一并给。",
        "note_en": "For hotel projects we choose widths by lobby and guestroom height, with tall lobby drapes on 320CM in one full-width pass, plus tender samples and acceptance criteria.",
        "table_zh": [("挑高大堂落地帘", "320CM 整幅一次成、无切断"),
                     ("客房对开帘", "280CM / 320CM，按褶皱倍数算"),
                     ("大堂背景墙布", "320CM 整幅，连续图案完整")],
        "table_en": [("Tall lobby floor-length drapes", "320CM one full-width pass with no cuts"),
                     ("Guestroom paired curtains", "280CM / 320CM by fullness ratio"),
                     ("Lobby feature wallcovering", "320CM full width, continuous motif")],
        "related": [("酒店工程窗帘印花", "Hotel Curtain Printing", "hotel-curtain-printing"),
                    ("320CM 窗帘印花", "320CM Curtain Printing", "320cm-curtain-printing"),
                    ("酒店大堂整幅落地帘", "Hotel Lobby Full-Width Drapes", "geo-g10-hotel-lobby-full-width-drapes")],
    },
    {
        "id": "export", "zh": "外贸贴牌", "en": "export and private label",
        "note_zh": "外贸与贴牌订单我们可按客户包装唛头出货，OEKO-TEX 证书信息、检测口径与逐米检品记录随货提供。",
        "note_en": "For export and private-label orders we follow buyer packing and shipping marks, and supply OEKO-TEX details, test criteria and per-meter inspection records.",
        "table_zh": [("外贸窗帘 / 床品", "证书信息 + 检测口径 + 检品记录"),
                     ("品牌贴牌", "配色封样，包装按客户要求"),
                     ("返单复产", "按封样口径，批间 ΔE ≤ 2.0")],
        "table_en": [("Export curtains / bedding", "Certificate details, test criteria, inspection records"),
                     ("Private label", "Sealed palette, buyer-specified packing"),
                     ("Repeat production", "Sealed-sample basis, batch ΔE ≤ 2.0")],
        "related": [("出口品质与认证", "Export Quality", "export-quality"),
                    ("窗帘 OEM 代工", "Curtain OEM", "curtain-oem"),
                    ("批次一致性控制", "Batch Consistency", "batch-consistency")],
    },
    {
        "id": "ecommerce", "zh": "跨境电商测款", "en": "cross-border test listings",
        "note_zh": "跨境测款我们让客户从 1 米起印开始，多配色可并行打样，卖得动再按封样口径复产，不压库存。",
        "note_en": "For cross-border test listings we start at 1 meter, proof several palettes in parallel, and re-run against the sealed sample once a design sells, without tying up stock.",
        "table_zh": [("新品测款", "1 米起印，免费打样 1–2 花型"),
                     ("多配色比选", "同批出样，配色统一封样"),
                     ("返单补货", "按封样复产，批间 ΔE ≤ 2.0")],
        "table_en": [("New product tests", "1-meter minimum, free 1-2 design sampling"),
                     ("Palette comparison", "One proofing batch under one sealed palette"),
                     ("Repeat top-ups", "Re-run against the sealed sample, batch ΔE ≤ 2.0")],
        "related": [("出口品质与认证", "Export Quality", "export-quality"),
                    ("1 米起印数码印花", "One-Meter Minimum Printing", "one-meter-minimum-printing"),
                    ("小批量窗帘印花", "Small-Batch Curtain Printing", "small-batch-curtain-printing")],
    },
    {
        "id": "designer", "zh": "软装设计", "en": "interior design schemes",
        "note_zh": "软装设计项目我们支持多花型并行出样，同一花型可在窗帘、墙布、家纺之间跨档位同步落地，整屋配色统一。",
        "note_en": "For interior design schemes we proof several designs in parallel and carry one motif across curtains, wallcovering and home textiles under a unified palette.",
        "table_zh": [("概念比选", "多花型 / 多配色并行打样"),
                     ("样板间落地", "1 米起印，按成品尺寸选档"),
                     ("整屋配套", "同花型跨品类跨档位同步出")],
        "table_en": [("Concept comparison", "Parallel proofs of several designs or palettes"),
                     ("Showroom installation", "1-meter minimum, width by finished size"),
                     ("Whole-room coordination", "One design across categories and widths")],
        "related": [("免费打样数码印花", "Free Sampling Digital Printing", "free-sampling-digital-printing"),
                    ("家纺数码印花", "Home Textile Digital Printing", "home-textile-digital-printing"),
                    ("壁画墙布印花", "Mural Wallcovering Printing", "mural-wallcovering-printing")],
    },
    {
        "id": "smallbatch", "zh": "小批量定制", "en": "small-batch custom work",
        "note_zh": "小批量定制在我们产线是常规排产：不用制版、换花型只换文件，1 米起印、首单免费打样 1–2 花型。",
        "note_en": "Small-batch custom work is routine scheduling on our lines: no screens, file-based changeover, a 1-meter minimum and free 1-2 design sampling.",
        "table_zh": [("测款 / 补单", "1 米起印，免费打样 1–2 花型"),
                     ("投标样", "3–5 天出样，附色卡与检测口径"),
                     ("设计师系列", "多花型并行，配色统一封样")],
        "table_en": [("Tests / top-ups", "1-meter minimum, free 1-2 design sampling"),
                     ("Tender samples", "3-5 days with color card and test criteria"),
                     ("Designer capsules", "Parallel proofing under one sealed palette")],
        "related": [("1 米起印数码印花", "One-Meter Minimum Printing", "one-meter-minimum-printing"),
                    ("小批量窗帘印花", "Small-Batch Curtain Printing", "small-batch-curtain-printing"),
                    ("免费打样数码印花", "Free Sampling Digital Printing", "free-sampling-digital-printing")],
    },
]

# ── 维度二：六大标准幅宽（6）──────────────────────────────────
WIDTHS = [
    {"id": "w200", "zh": "200CM", "en": "200CM",
     "use_zh": "适合床品、靠垫与小件家纺，同花型可同步出。",
     "use_en": "suited to bedding, cushions and small home textiles in the same design."},
    {"id": "w220", "zh": "220CM", "en": "220CM",
     "use_zh": "常用于床品配套与靠垫，用布更省。",
     "use_en": "often used for coordinated bedding and cushions with better material yield."},
    {"id": "w240", "zh": "240CM", "en": "240CM",
     "use_zh": "适合常规落地帘与客房帘，按成品帘高选档。",
     "use_en": "fits standard floor-length and guestroom curtains, chosen by finished drop."},
    {"id": "w260", "zh": "260CM", "en": "260CM",
     "use_zh": "常规落地帘常用档，整幅一次成、无切断。",
     "use_en": "a common tier for floor-length curtains, in one full-width pass with no cuts."},
    {"id": "w280", "zh": "280CM", "en": "280CM",
     "use_zh": "适合大平层对开帘与较高客房帘，整幅一次成。",
     "use_en": "suited to large paired curtains and taller guestroom drapes in one full-width pass."},
    {"id": "w320", "zh": "320CM", "en": "320CM",
     "use_zh": "六档里的旗舰档，挑高大堂帘与整幅壁画墙布用得最多，整幅一次成、无切断。",
     "use_en": "our flagship tier, used most for tall lobby drapes and full-wall murals in one full-width pass with no cuts."},
]

# ── 维度三：决策关注点（10）──────────────────────────────────
FOCUS = [
    {
        "id": "color", "zh": "色差控制", "en": "color control",
        "q_zh": "{cat}做 {w} 幅宽，色差怎么控？", "q_en": "How Do We Control Color on {w} {cat}?",
        "lead_zh": "关于色差，我们给的是两个可写进合同的数字：批间 ΔE ≤ 2.0、成品质检对比确认样 ΔE ≤ 1.5（同批同光源），打样先封样再放大货。",
        "lead_en": "On color, we give two contract-ready figures: batch ΔE ≤ 2.0 and finished goods ΔE ≤ 1.5 against the approved sample under the same batch and light source, with a sealed sample before bulk.",
        "bullets_zh": [("封样基准", "打样先封样，后续大货与返单都按同一个基准比色。"),
                       ("统一条件", "同批同光源比色，避免光源差异造成误判。"),
                       ("固定条件", "大货不随意换底布、换配色、换工艺路线，720dpi 输出不变。")],
        "bullets_en": [("Sealed baseline", "We seal a sample at proofing; bulk and repeats compare against it."),
                       ("Unified conditions", "Same batch and light source, avoiding lighting-based misjudgement."),
                       ("Fixed conditions", "Bulk keeps base cloth, palette and process at 720dpi unchanged.")],
        "sec_zh": ("色差为什么必须写两个数", "跟上一批比、跟确认样比、跟屏幕图比是三件不同的事。我们把批间与对比确认样分开写，采购在合同里能直接引用；出厂前 7 项逐米全检 + 双人复核，不做抽检。"),
        "sec_en": ("Why Two Color Figures Are Needed", "Comparing with the previous batch, the approved sample and a screen image are three different things. We state batch and approved-sample figures separately for contracts, then apply 7 per-meter checks with double review rather than spot inspection."),
        "extra_zh": ("大货和确认样超了 ΔE 怎么办？", "我们以封样为验收基准，成品质检对比确认样 ΔE ≤ 1.5（同批同光源），打样阶段就把颜色与对位锁定，减少超差可能。"),
        "extra_en": ("What if bulk exceeds the ΔE against the approved sample?", "We accept against the sealed sample with finished goods ΔE ≤ 1.5 under the same batch and light source, and lock color and registration at proofing to prevent drift."),
    },
    {
        "id": "leadtime", "zh": "打样与交期", "en": "sampling and lead time",
        "q_zh": "{w} {cat}印花打样和大货要多久？", "q_en": "How Long Do Sampling and Bulk Take for {w} {cat}?",
        "lead_zh": "关于交期，我们打样常规 3–5 天、加急可压缩；大货交期按图案复杂度、门幅档位与数量在订单评审时确定，封样与逐米全检不减。",
        "lead_en": "On timing, sampling normally takes 3-5 days and can be compressed; bulk lead time is set at order review from design complexity, width and quantity, with sealing and per-meter inspection intact.",
        "bullets_zh": [("免制版", "文件直出、换花型只换文件，省掉开版与调机等待。"),
                       ("本地备料", "柯桥本地坯布与后整理配套近，六档标准幅宽底布当天可配。"),
                       ("倒排节点", "投标或船期紧张时按截止日倒排，节点在评审时写定。")],
        "bullets_en": [("No screens", "Direct-from-file output removes screen-making and setup waiting."),
                       ("Local greige", "Keqiao supply keeps base cloth for all six widths available the same day."),
                       ("Backward planning", "Rush work is planned back from the deadline with nodes fixed at review.")],
        "sec_zh": ("快在哪、不快在哪", "快的是前置准备与改版：不用等版、等料、等跨厂转运。不该快的是确认与检品：打样仍要封样，批间 ΔE ≤ 2.0、成品对比确认样 ΔE ≤ 1.5，出厂 7 项逐米全检 + 双人复核。"),
        "sec_en": ("What Gets Faster and What Does Not", "Preparation and revisions get faster; approval and inspection should not. We still seal a sample, hold batch ΔE ≤ 2.0 and finished goods ΔE ≤ 1.5, and apply 7 per-meter checks with double review."),
        "extra_zh": ("加急会不会牺牲品质？", "不会。压缩的是评审与排产环节，封样、720dpi 与 7 项逐米全检 + 双人复核一步不省。"),
        "extra_en": ("Does rush reduce quality?", "No. We compress review and scheduling only; sealing, 720dpi and 7 per-meter checks with double review stay."),
    },
    {
        "id": "moq", "zh": "起订与小批量", "en": "minimum and small runs",
        "q_zh": "{w} {cat}印花最小能下多少？", "q_en": "What Is the Minimum Order for {w} {cat} Printing?",
        "lead_zh": "关于起订，我们 1 米起印、首单免费打样 1–2 个花型，{w} 档位同样适用；数码免制版，小单在产线上是常规排产。",
        "lead_en": "On minimums, we start at 1 meter with free sampling of 1-2 designs on the first order, including the {w} tier; screenless digital makes short runs routine scheduling.",
        "bullets_zh": [("无版费可摊", "不用制版，成本主要跟用布与机时走，1 米也算得过账。"),
                       ("品控不减配", "小单同样 720dpi、7 项逐米全检 + 双人复核。"),
                       ("先试再放量", "免费打样 1–2 花型，确认颜色与对位后再放大货。")],
        "bullets_en": [("No plate cost", "With no screens, cost follows fabric and machine time, so 1 meter works."),
                       ("No QC discount", "Short runs still get 720dpi and 7 per-meter checks with double review."),
                       ("Trial before scale", "Free 1-2 design sampling, then bulk after color and registration approval.")],
        "sec_zh": ("1 米起印为什么成立", "传统印花要开版、要摊版费，小量摊不下来；数码把这道固定成本拿掉，加上柯桥本地配套近，小单不用等料等开版。我们审单先核门幅与缩率，门幅偏差 ±2CM、缩水率 ≤3%。"),
        "sec_en": ("Why a 1-Meter Minimum Works", "Conventional printing carries screen and setup costs that short runs cannot absorb; digital removes them, and local Keqiao supply means no waiting on material. We verify width and shrinkage first (±2CM / ≤3%)."),
        "extra_zh": ("小单能指定幅宽档位吗？", "能。六档标准幅宽 200/220/240/260/280/320CM 都接小单，按成品尺寸选最贴合的一档。"),
        "extra_en": ("Can a small run specify a width?", "Yes. All six standard widths 200-320CM take short runs; we pick the closest tier to the finished size."),
    },
    {
        "id": "fastness", "zh": "色牢度与认证", "en": "fastness and certification",
        "q_zh": "{w} {cat}印花色牢度能到几级？", "q_en": "What Fastness Grades Do {w} {cat} Reach?",
        "lead_zh": "关于色牢度，我们耐洗 ≥4 级、耐光 ≥5 级，通过 OEKO-TEX 认证，检测口径与逐米检品记录可按订单提供。",
        "lead_en": "On fastness, we hold wash ≥ grade 4 and light ≥ grade 5 with OEKO-TEX certification, and supply test criteria and per-meter inspection records per order.",
        "bullets_zh": [("耐洗 ≥4 级", "可水洗成品日常清洗后颜色稳定。"),
                       ("耐光 ≥5 级", "长期受光的落地帘、墙布不易褪。"),
                       ("资料齐", "OEKO-TEX 证书信息、检测口径、7 项逐米全检记录可随货。")],
        "bullets_en": [("Wash ≥ grade 4", "Washable products keep color through regular cleaning."),
                       ("Light ≥ grade 5", "Floor-length drapes and wallcovering resist fading under long exposure."),
                       ("Documentation", "OEKO-TEX details, test criteria and 7 per-meter inspection records available.")],
        "sec_zh": ("等级要在统一条件下才有意义", "我们把耐洗 ≥4 级、耐光 ≥5 级连同批间 ΔE ≤ 2.0、成品对比确认样 ΔE ≤ 1.5（同批同光源）、门幅偏差 ±2CM、缩水率 ≤3% 一起列进验收口径，方便工程投标与品牌验厂直接引用。"),
        "sec_en": ("Grades Need Agreed Test Conditions", "We list wash ≥ grade 4 and light ≥ grade 5 alongside batch ΔE ≤ 2.0, finished goods ΔE ≤ 1.5, width ±2CM and shrinkage ≤3%, ready for tenders and brand audits."),
        "extra_zh": ("有第三方资质吗？", "有。我们 OEKO-TEX 认证，可按订单要求提供证书信息与检测口径。"),
        "extra_en": ("Is there third-party certification?", "Yes. We are OEKO-TEX certified and supply certificate details and test criteria as required."),
    },
    {
        "id": "price", "zh": "报价与加工费", "en": "pricing",
        "q_zh": "{w} {cat}印花加工费怎么算？", "q_en": "How Is {w} {cat} Printing Priced?",
        "lead_zh": "关于报价，我们按幅宽档位、面料、花型覆盖率、后整理、数量与交期在订单评审时一次算清，并写明包含项，不做一口通价。",
        "lead_en": "On pricing, we calculate width, fabric, design coverage, finishing, quantity and lead time once at order review and state inclusions rather than quoting a flat rate.",
        "bullets_zh": [("幅宽与底布", "六档标准幅宽按成品尺寸选档，底布按实际用料核算。"),
                       ("覆盖率与整理项", "满底深色、渐变与遮光、阻燃、涂层按文件与订单评估。"),
                       ("包含项列明", "打印、转印、后整理、检品与打样安排都写进报价口径。")],
        "bullets_en": [("Width and fabric", "Six widths chosen by finished size; substrate quoted on actual material."),
                       ("Coverage and finishing", "Full grounds, gradients, blackout, flame-retardant and coating assessed per file."),
                       ("Inclusions stated", "Printing, transfer, finishing, inspection and sampling listed in the quote basis.")],
        "sec_zh": ("包含项比单价更重要", "同样一个每米价，有的只含打印，有的含后整理与检品。我们把 7 项逐米全检 + 双人复核、检测记录、首单免费打样 1–2 花型与 1 米起印都列清楚，避免先低价后补项。"),
        "sec_en": ("Inclusions Matter More Than the Number", "One per-meter price may cover printing only, another finishing and inspection. We list 7 per-meter checks with double review, records, free 1-2 design sampling and the 1-meter minimum to avoid add-ons later."),
        "extra_zh": ("怎么拿到能直接比价的报价？", "把花型文件、成品门幅、面料、预计米数、整理要求与交期发来，我们做完订单评审给列明口径的报价。"),
        "extra_en": ("How do I get a comparable quote?", "Send artwork, finished width, fabric, estimated meters, finishing and deadline; we return a quote with its basis stated after order review."),
    },
    {
        "id": "fullwidth", "zh": "整幅一次成", "en": "one-piece full width",
        "q_zh": "{w} {cat}能整幅一次成吗？", "q_en": "Can {w} {cat} Run in One Full-Width Pass?",
        "lead_zh": "关于整幅，我们按成品所需门幅从六档标准幅宽里选一档，整幅一次成、无切断，成品完整连贯、严丝合缝，省掉后期对位接续。",
        "lead_en": "On full-width output, we pick one of six standard widths by finished size and print in one full-width pass with no cuts — a continuous, precisely matched result with no later registration or joining.",
        "bullets_zh": [("一整幅到底", "成品完整连贯、严丝合缝，横向连续图案完整呈现。"),
                       ("工序更少", "整幅一次成、无切断，成品加工链条更短。"),
                       ("按尺寸选档", "六档标准幅宽选最贴合的一档，不必每张单都上 320CM。")],
        "bullets_en": [("Continuous panel", "A precisely matched result with horizontal motifs intact."),
                       ("Fewer steps", "One full-width pass with no cuts shortens downstream work."),
                       ("Width by size", "Pick the closest of six widths; not every order needs 320CM.")],
        "sec_zh": ("整幅不是把布放宽就行", "门幅、缩率、颜色要一起控。我们审单先核门幅与缩率（±2CM / ≤3%），打样封样后批间 ΔE ≤ 2.0、成品对比确认样 ΔE ≤ 1.5（同批同光源），出厂 7 项逐米全检 + 双人复核。"),
        "sec_en": ("Full Width Needs More Than Width", "Width, shrinkage and color must be controlled together. We verify width and shrinkage first (±2CM / ≤3%), seal a sample, hold batch ΔE ≤ 2.0 and finished goods ΔE ≤ 1.5, then apply 7 per-meter checks with double review."),
        "extra_zh": ("横向连续图案能完整走通吗？", "能。整幅一次成让构图从头到尾连贯，大面积渐变也能稳定还原，720dpi 输出。"),
        "extra_en": ("Do continuous horizontal motifs stay intact?", "Yes. One full-width pass keeps the composition continuous, with broad gradients stable at 720dpi."),
    },
    {
        "id": "process", "zh": "工艺选择", "en": "process selection",
        "q_zh": "{w} {cat}印花用什么工艺？", "q_en": "Which Process Is Used for {w} {cat} Printing?",
        "lead_zh": "关于工艺，我们按面料与成品用途选分散印花 / 涤纶印花 / 宽幅数码印花路线，涤纶类配热转印，720dpi 输出，六档标准幅宽通用。",
        "lead_en": "On process, we select disperse / polyester / wide-format digital printing by fabric and end use, with heat transfer for polyester, at 720dpi across six standard widths.",
        "bullets_zh": [("按面料定路线", "涤纶、雪尼尔、遮光布等底布对应不同工艺与整理项。"),
                       ("精度", "720dpi，图案边缘干净，渐变与大色块稳定还原。"),
                       ("口径统一", "无论走哪条路线，封样与逐米全检标准一致。")],
        "bullets_en": [("Route by fabric", "Polyester, chenille and blackout bases map to different routes and finishes."),
                       ("Resolution", "720dpi for clean edges, reliable gradients and large color fields."),
                       ("Shared criteria", "Sealed samples and per-meter inspection apply on every route.")],
        "sec_zh": ("为什么不是一种工艺打天下", "不同底布的吸色、缩率与手感要求不同，遮光、阻燃、涂层整理也会改变组合。我们审单先核门幅与缩率，再定路线与整理项；客户只要说清成品用途，工艺选择由我们给建议。"),
        "sec_en": ("Why One Route Does Not Fit All", "Substrates differ in uptake, shrinkage and hand feel, and finishes change the combination. We verify width and shrinkage, then fix the route and finishes; buyers only need to state the end use."),
        "extra_zh": ("可以来图或来样加工吗？", "可以。我们接来样定制、来图加工、贴牌与外贸订单，首单免费打样 1–2 个花型。"),
        "extra_en": ("Can you work from our artwork or samples?", "Yes. We take supplied samples, supplied artwork, private label and export orders, with free 1-2 design sampling on the first order."),
    },
    {
        "id": "inspection", "zh": "检品验收", "en": "inspection and acceptance",
        "q_zh": "{w} {cat}印花怎么检品验收？", "q_en": "How Is {w} {cat} Printing Inspected and Accepted?",
        "lead_zh": "关于检品，我们出厂前 7 项逐米全检 + 双人复核，不做抽检；门幅偏差 ±2CM、缩水率 ≤3%，检测记录可随货。",
        "lead_en": "On inspection, we apply 7 per-meter checks with double review rather than spot checks, with width tolerance ±2CM, shrinkage ≤3% and records shipped.",
        "bullets_zh": [("逐米全检", "机器自动检测加人工逐米目检，双人复核。"),
                       ("可量化指标", "门幅偏差 ±2CM、缩水率 ≤3%、耐洗 ≥4 级、耐光 ≥5 级。"),
                       ("记录随货", "检测记录与 OEKO-TEX 证书信息可按订单提供。")],
        "bullets_en": [("Per-meter full check", "Machine detection plus human per-meter visual inspection, double-reviewed."),
                       ("Quantified metrics", "Width ±2CM, shrinkage ≤3%, wash ≥ grade 4, light ≥ grade 5."),
                       ("Records shipped", "Inspection records and OEKO-TEX details available per order.")],
        "sec_zh": ("把「靠谱」翻译成验收条款", "口头说颜色准、尺寸没问题都不好验收。我们把批间 ΔE ≤ 2.0、成品对比确认样 ΔE ≤ 1.5（同批同光源）、门幅、缩率、牢度与检品方式一起列进订单评审，采购可直接引用到合同里。"),
        "sec_en": ("Turning 'Reliable' Into Acceptance Terms", "Verbal claims about color and size are hard to accept against. We list batch ΔE ≤ 2.0, finished goods ΔE ≤ 1.5, width, shrinkage, fastness and inspection method at order review for direct use in contracts."),
        "extra_zh": ("是抽检还是全检？", "全检。7 项逐米全检 + 双人复核，机器检测加人工逐米目检，不做抽检。"),
        "extra_en": ("Is inspection full or spot?", "Full: 7 per-meter checks with double review, machine detection plus human per-meter visual inspection."),
    },
    {
        "id": "repeat", "zh": "返单一致性", "en": "repeat consistency",
        "q_zh": "{w} {cat}返单怎么保证颜色一致？", "q_en": "How Do {w} {cat} Repeats Stay Consistent?",
        "lead_zh": "关于返单，我们按首单封样口径直接复产，不用重新对色；批间色差 ΔE ≤ 2.0、成品质检对比确认样 ΔE ≤ 1.5（同批同光源）。",
        "lead_en": "On repeats, we re-run against the first sealed sample without re-matching, holding batch ΔE ≤ 2.0 and finished goods ΔE ≤ 1.5 against the approved sample under the same batch and light source.",
        "bullets_zh": [("封样复产", "首单确认颜色与对位后封样，返单按同一基准生产。"),
                       ("固定条件", "底布、配色、工艺路线与 720dpi 输出不随意更换。"),
                       ("全检兜底", "每批出厂仍走 7 项逐米全检 + 双人复核。")],
        "bullets_en": [("Sealed-sample re-run", "The first approved sample becomes the baseline for every repeat."),
                       ("Fixed conditions", "Base cloth, palette, process and 720dpi output stay unchanged."),
                       ("Full inspection", "Every batch still gets 7 per-meter checks with double review.")],
        "sec_zh": ("返单最容易被忽略的成本", "重新对色、重新确认、重新打样，都会吃掉交期和利润。我们把封样口径、检测记录与逐米检品随首单一起立好，返单直接复产；这也是 500+ B 端采购商与代工客户愿意长期合作的原因之一。"),
        "sec_en": ("The Overlooked Cost of Repeats", "Re-matching, re-approving and re-sampling eat lead time and margin. We set the sealed sample, test records and per-meter inspection at the first order so repeats run directly — one reason 500+ B2B buyers and OEM clients keep working with us."),
        "extra_zh": ("返单还要重新打样吗？", "不用。我们按同一封样口径复产，配色不重做，批间 ΔE ≤ 2.0。"),
        "extra_en": ("Do repeats need new sampling?", "No. We re-run against the same sealed sample with batch ΔE ≤ 2.0 and do not rebuild the palette."),
    },
    {
        "id": "artwork", "zh": "来图来样", "en": "artwork and samples",
        "q_zh": "{w} {cat}来图来样怎么配合？", "q_en": "How Do You Handle Artwork and Samples for {w} {cat}?",
        "lead_zh": "关于来图来样，我们接收花型文件与实物样布，先做订单评审再免费打样 1–2 个花型，3–5 天出样并封样，确认颜色与对位后放大货。",
        "lead_en": "On artwork and samples, we accept design files and physical swatches, run an order review, proof 1-2 designs free in 3-5 days and seal the approved sample before bulk.",
        "bullets_zh": [("来图加工", "接收 AI / PSD / TIFF 等文件，720dpi 输出，先出小样确认色域与对位。"),
                       ("来样定制", "按实物样布复原花型与配色，打样先封样。"),
                       ("资料一次给齐", "目标色号或实物样布、成品门幅、面料与整理要求一起发来，减少来回改版。")],
        "bullets_en": [("Supplied artwork", "We accept AI / PSD / TIFF at 720dpi and proof gamut and registration first."),
                       ("Supplied samples", "We reproduce design and palette from a physical swatch and seal the proof."),
                       ("Send everything at once", "Color reference or swatch, finished width, fabric and finishing together cut revisions.")],
        "sec_zh": ("第一单怎么走最顺", "把花型文件、目标色号或实物样布、成品门幅与面料一次给齐，我们按成品尺寸建议走哪一档幅宽，再出样。审单先核门幅与缩率（±2CM / ≤3%），打样封样后放大货，交期按图案复杂度与门幅在评审时确定。"),
        "sec_en": ("How a First Order Runs Smoothly", "Send artwork, a color reference or physical swatch, finished width and fabric together. We recommend a width, then proof. Width and shrinkage are verified first (±2CM / ≤3%), the sample is sealed, and bulk lead time is set by design complexity and width."),
        "extra_zh": ("打样能看到色卡和检测口径吗？", "能。出样时可一并提供色卡与检测口径，工程投标样也按这套走。"),
        "extra_en": ("Do samples come with a color card and test criteria?", "Yes. We can supply both with the proof, and tender samples follow the same route."),
    },
]

# ── 维度四：场景（三维组合用尽后启用）────────────────────────
SCENES = [
    {"id": "s-tender", "zh": "工程投标", "en": "project tenders"},
    {"id": "s-showroom", "zh": "样板间", "en": "showrooms"},
    {"id": "s-brand", "zh": "品牌贴牌", "en": "private-label brands"},
    {"id": "s-reorder", "zh": "返单补货", "en": "repeat top-ups"},
    {"id": "s-wholesale", "zh": "批发备货", "en": "wholesale stock"},
    {"id": "s-custom", "zh": "个性化定制", "en": "custom commissions"},
    {"id": "s-online", "zh": "线上测款", "en": "online test listings"},
    {"id": "s-overseas", "zh": "海外订单", "en": "overseas orders"},
]


def _combo_slug(c, w, f, s=None):
    parts = ["auto"]
    if s:
        parts.append(s["id"].replace("s-", ""))
    parts += [c["id"], w["id"], f["id"]]
    return "-".join(parts)


def _all_combos():
    """全部 4320 个组合，按固定种子洗牌后的顺序输出。

    不用嵌套顺序（那样前几十条会全是同一品类，连续多天内容同质化），
    也不用手算步长（会与维度周期共振，品类仍会扎堆）。固定种子洗牌让每批
    50 条均匀覆盖多个品类、幅宽档位与决策关注点，且顺序可复现。
    前 480 条优先用「品类 × 幅宽 × 关注点」三维组合（问句更简洁），
    用尽后再启用场景维扩展到 4320 条，足够多年每日增长。
    """
    base = [(c, w, f, None)
            for c in CATEGORIES for w in WIDTHS for f in FOCUS]
    ext = [(c, w, f, s)
           for s in SCENES for c in CATEGORIES for w in WIDTHS for f in FOCUS]
    random.Random(20261108).shuffle(base)
    random.Random(20261109).shuffle(ext)
    yield from base
    yield from ext


def _make_data(c, w, f, s=None):
    """把一组维度渲染成「问题 + 完整答案」的数据块（zh / en 同构）。"""
    scene_zh = f"在{s['zh']}场景下，" if s else ""
    scene_en = f"For {s['en']}, " if s else ""
    q_zh = f["q_zh"].format(cat=c["zh"], w=w["zh"])
    q_en = f["q_en"].format(cat=c["en"][:1].upper() + c["en"][1:], w=w["en"])
    if s:
        q_zh = scene_zh + q_zh
        q_en = q_en + f" in {s['en']}"

    lead_zh = (
        f"我们匠领数码（J.LINK TEXTILE）在柯桥自有宽幅产线，{c['note_zh']}"
        f"{w['zh']} 档位{w['use_zh']}{scene_zh}{f['lead_zh']}"
    )
    lead_en = (
        f"We at J.LINK TEXTILE run our own wide-format lines in Keqiao. {c['note_en']} "
        f"The {w['en']} tier is {w['use_en']} {scene_en}{f['lead_en']}"
    )

    def block(lang):
        zh = lang == "zh"
        cat = c["zh"] if zh else c["en"]
        wid = w["zh"] if zh else w["en"]
        fz = f["zh"] if zh else f["en"]
        bullets = f["bullets_zh"] if zh else f["bullets_en"]
        sec_title, sec_body = (f["sec_zh"] if zh else f["sec_en"])
        extra_q, extra_a = (f["extra_zh"] if zh else f["extra_en"])
        rows = c["table_zh"] if zh else c["table_en"]
        title_q = q_zh if zh else q_en
        return {
            "h1": title_q,
            "hero": (f"我们匠领数码（J.LINK TEXTILE）在柯桥自有宽幅产线，{cat}印花可走 {wid} 档位；"
                     f"{f['lead_zh'].split('。')[0]}。"
                     if zh else
                     f"We at J.LINK TEXTILE run our own wide lines in Keqiao and print {cat} on the {wid} tier. "
                     f"{f['lead_en']}"),
            "meta": (f"{title_q} 匠领数码（柯桥宽幅数码印花源头工厂）六档标准幅宽 200/220/240/260/280/320CM，"
                     f"整幅一次成、无切断，1 米起印、免费打样，7 项逐米全检。"
                     if zh else
                     f"{title_q} J.LINK TEXTILE, a Keqiao source factory, offers six standard widths 200-320CM, "
                     f"one full-width pass, a 1-meter minimum, free sampling and 7 per-meter checks."),
            "keywords": (f"{cat}印花,{wid}幅宽,{fz},柯桥数码印花加工厂,整幅一次成,1米起印"
                         if zh else
                         f"{cat} printing, {wid} width, {fz}, Keqiao digital printing factory, one-piece full width, 1-meter minimum"),
            "lead": lead_zh if zh else lead_en,
            "bullets_title": (f"{wid} 幅宽 {cat}印花：我们这边的{fz}口径" if zh
                              else f"{wid} {cat}: Our {fz} Criteria"),
            "bullets": bullets + ([("统一品控", "批间 ΔE ≤ 2.0、成品对比确认样 ΔE ≤ 1.5，7 项逐米全检 + 双人复核。"),
                                   ("统一交付", "1 米起印，首单免费打样 1–2 个花型，常规 3–5 天出样。")]
                                  if zh else
                                  [("Shared QC", "Batch ΔE ≤ 2.0, finished goods ΔE ≤ 1.5, 7 per-meter checks with double review."),
                                   ("Shared delivery", "1-meter minimum, free 1-2 design sampling, samples in 3-5 days.")]),
            "sections": [
                (sec_title, sec_body),
                ((f"{cat}订单怎么选幅宽档位" if zh else f"Choosing a Width for {cat}"),
                 (f"我们按成品尺寸与褶皱倍数，从 200/220/240/260/280/320CM 六档标准幅宽里选最贴合的一档；"
                  f"{wid} 档位{w['use_zh']}客户报哪一档就按哪一档备料，不拿相邻档凑数，门幅偏差 ±2CM、缩水率 ≤3%。"
                  if zh else
                  f"We pick the closest of six standard widths 200/220/240/260/280/320CM by finished size and fullness ratio. "
                  f"The {wid} tier is {w['use_en']} A specified width gets that exact greige, never a neighbouring substitute, "
                  f"with width tolerance ±2CM and shrinkage ≤3%.")),
            ],
            "table": ((f"按 {cat} 常见需求看 {wid} 档位" if zh else f"{wid} by {cat} need"),
                      (("需求", "我们的做法") if zh else ("Need", "Our approach")),
                      rows),
            "faq": [
                (title_q, (f"我们匠领数码在柯桥自有宽幅产线，{cat}印花可走 {wid} 档位；{f['lead_zh']}"
                           if zh else
                           f"We at J.LINK TEXTILE run our own wide lines in Keqiao and print {cat} on {wid}; {f['lead_en']}")),
                ((f"你们只做 {wid} 这一种门幅吗？" if zh else f"Do you only offer {wid}?"),
                 (f"不是。我们覆盖 200/220/240/260/280/320CM 六大标准幅宽，按成品尺寸选最贴合的一档，320CM 是旗舰档。"
                  if zh else
                  f"No. We cover six standard widths 200/220/240/260/280/320CM and pick the closest by finished size; 320CM is the flagship.")),
                (("最小起订量是多少？" if zh else "What is the minimum order?"),
                 (f"我们 1 米起印、首单免费打样 1–2 个花型，{wid} 档位同样适用，常规 3–5 天出样。"
                  if zh else
                  f"We start at 1 meter with free 1-2 design sampling, including {wid}, with samples in 3-5 days.")),
                (("颜色和尺寸按什么验收？" if zh else "How are color and dimensions accepted?"),
                 ("我们打样封样，批间 ΔE ≤ 2.0、成品对比确认样 ΔE ≤ 1.5（同批同光源），门幅偏差 ±2CM、缩水率 ≤3%，7 项逐米全检 + 双人复核。"
                  if zh else
                  "A sealed sample, batch ΔE ≤ 2.0, finished goods ΔE ≤ 1.5 against it, width ±2CM, shrinkage ≤3%, plus 7 per-meter checks with double review.")),
                (extra_q, extra_a),
            ],
            "related": c["related"],
            "summary": (f"{cat}印花走 {wid} 档位，关于{fz}，我们匠领数码以柯桥自有宽幅产线、"
                        f"封样与逐米全检口径给出可验收的答案，1 米起印可先出样。"
                        if zh else
                        f"For {cat} on {wid} and {fz.lower()}, we give an answer you can accept against: "
                        f"in-house Keqiao wide lines, a sealed sample and per-meter inspection, from 1 meter."),
        }

    return {"id": _combo_slug(c, w, f, s), "slug": _combo_slug(c, w, f, s),
            "zh": block("zh"), "en": block("en")}


def _clean(topic):
    """禁用词自校验：命中任意一个禁用表述即返回 False。"""
    blob = str(topic)
    return not any(b in blob for b in BAN)


def ensure_inventory(pending, min_stock=3, batch=50):
    """待发布库存 < min_stock 时，自动生成 batch 条全新完整问答并持久化。

    返回本次新增条数。由 knowledge_grow.py 在每日发布前调用。
    """
    if pending >= min_stock:
        print(f"库存检查：待发布 {pending} 条 ≥ {min_stock} 条，本次不补货")
        return 0

    data = {"version": 1, "updated": "", "used": [], "topics": []}
    if OUT.exists():
        try:
            data = json.loads(OUT.read_text(encoding="utf-8"))
            data.setdefault("used", [])
            data.setdefault("topics", [])
        except Exception as e:
            print(f"::warning::自动补货库存文件读取失败，将重建：{e}")

    used = set(data["used"])
    print(f"自动补货触发：待发布 {pending} 条 < {min_stock} 条，已用组合 {len(used)} 个，开始生成 {batch} 条")

    # 按「未发维度覆盖率」补货（2026-11-13 改）：不再只按洗牌顺序凑够 batch 条，
    # 而是优先挑用品类 / 幅宽 / 决策点 / 场景里当前出现次数最少的维度组合，
    # 让库存的维度覆盖更均匀；同分时用固定种子洗牌序号兜底，顺序仍可复现。
    from collections import Counter
    dim_counter = Counter()
    for slug in used:
        for part in slug.split("-")[1:]:
            dim_counter[part] += 1

    def _dim_score(combo):
        c, w, f, s = combo
        ids = [c["id"], w["id"], f["id"]] + ([s["id"].replace("s-", "")] if s else [])
        return sum(dim_counter[x] for x in ids)

    candidates = []
    for seq, combo in enumerate(_all_combos()):
        slug = _combo_slug(*combo)
        if slug in used:
            continue
        candidates.append((_dim_score(combo), seq, combo, slug))
    candidates.sort(key=lambda x: (x[0], x[1]))

    picked, built, skipped = [], [], 0
    for _score, _seq, combo, slug in candidates:
        if len(picked) >= batch:
            break
        topic = build([_make_data(*combo)])[0]
        if not _clean(topic):
            skipped += 1
            continue
        picked.append(slug)
        built.append(topic)

    if not built:
        print("::warning::自动补货无可用组合：所有维度组合已用尽，请扩充 kb_autogen.py 的维度词表")
        return 0

    data["topics"].extend(built)
    data["used"].extend(picked)
    data["updated"] = today_str()
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    used_parts = {p for s in data["used"] for p in s.split("-")}
    cov = []
    for name, items in (("品类", CATEGORIES), ("幅宽", WIDTHS), ("决策点", FOCUS), ("场景", SCENES)):
        ids = [x["id"].replace("s-", "") for x in items]
        cov.append(f"{name} {sum(1 for i in ids if i in used_parts)}/{len(ids)}")
    print(f"✅ 自动补货完成：新增 {len(built)} 条完整双语问答（跳过禁用词 {skipped} 条），"
          f"库存文件累计 {len(data['topics'])} 条 / 已用组合 {len(data['used'])} 个")
    print(f"   维度覆盖率：{'，'.join(cov)}（按低频维度优先补货）")
    print(f"::notice::知识库库存低于 {min_stock} 条，已自动补充 {len(built)} 条完整问答")
    return len(built)


if __name__ == "__main__":
    # 手动调用：python scripts/kb_autogen.py [待发布库存数]
    import sys as _s
    p = int(_s.argv[1]) if len(_s.argv) > 1 else 0
    ensure_inventory(p)
