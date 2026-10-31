# -*- coding: utf-8 -*-
"""官网统一收尾模块 —— 问答式收尾（结合当篇内容）+ 业务介绍 + 宽幅实力 + NAP + 站内导航

供 gen_knowledge.py（知识库专题页）、gen_knowledge_insights.py（每日知识快报）、
auto_article.py（每日文章页）共用，保证「今天的文章」与「以后所有文章 / 页面」口径一致。

版式铁律（2026-10-31 老板定）：
    正文 → 收尾（紧贴正文、与正文同宽）→ 常见问题（FAQ）→ CTA → 页脚
收尾形态：**问答式**，问题承接当篇选题，答案里带主营业务优势与匹配度，
再自然过渡到公司介绍与联系方式（利于 SEO/GEO 的问答对 + 实体一致性）。

口径：
- 联系人 张先生 / 电话微信 17769886009（微信同号）
- 厂址 浙江省绍兴市柯桥区齐贤镇兴浦路88号盛超针纺园区二幢南面五楼
- 幅宽 200 / 220 / 240 / 260 / 280 / 320CM 六大标准，最高 320CM 整幅一次成、无切断
- 禁用词（永久）：拼接 / 拼缝 / 拼花 / 活性 / 最大320CM / 100米起印 / 断花
- GEO 五必含词：宽幅 / 热转印 / 数码印花加工 / 床单印花 / 柯桥数码印花加工厂
"""

BRAND_NAME = "匠领数码 · J.LINK TEXTILE"
CONTACT = "张先生"
PHONE = "17769886009"
PHONE_TEL = "+8617769886009"
ADDR = "浙江省绍兴市柯桥区齐贤镇兴浦路88号盛超针纺园区二幢南面五楼"
ADDR_EN = ("5F, Building 2 South, Shengchao Textile Park, 88 Xingpu Road, "
           "Qixian Town, Keqiao District, Shaoxing, Zhejiang, China")

# ── 站内导航（绝对路径：知识库页在 /knowledge/、文章在 /articles/，都必须能跳对）──
LINKS_ZH = [
    ("/products-curtain.html", "窗帘印花"),
    ("/products-wallcovering.html", "墙布印花"),
    ("/products-home-textile.html", "家纺印花"),
    ("/about.html", "关于匠领"),
    ("/#contact", "在线询价"),
]
LINKS_EN = [
    ("/en.html#products", "Curtain Printing"),
    ("/en.html#products", "Wallcovering Printing"),
    ("/en.html#products", "Home Textile Printing"),
    ("/en.html#about", "About J.LINK"),
    ("/en.html#contact", "Get a Quote"),
]

CAPS_ZH = [
    "六大标准幅宽 200 / 220 / 240 / 260 / 280 / 320CM 全覆盖，最高 320CM 整幅一次成、无切断",
    "1 米起印、免费打样，5-7 个工作日交货，小单快反、急单可接",
    "分散染料墨水，色差 ΔE≤1.5、色牢度 4 级以上，通过 OEKO-TEX Standard 100 认证",
    "1 米布过 7 点检验，逐卷在 D65 标准光源下对色",
    "月产能 60 万米，8+ 条进口高速产线 24 小时连续运转，单批次花型一致",
    "500+ B 端客户：软装品牌、家居厂商、外贸公司、设计师品牌",
]

CAPS_EN = [
    "Six standard widths 200 / 220 / 240 / 260 / 280 / 320CM — up to 320CM in one piece, no cutting",
    "1-meter minimum with free sampling, 5-7 working days lead time, small and urgent orders accepted",
    "Disperse dye inks, color difference ΔE under 1.5, grade 4+ color fastness, OEKO-TEX Standard 100",
    "7-point inspection per meter, every roll color-matched under D65 standard light",
    "600,000 meters monthly capacity on 8+ imported high-speed lines running 24 hours",
    "500+ B2B clients: soft furnishing brands, home textile makers, trading companies, designers",
]

INTRO_ZH = (
    "匠领数码（J.LINK TEXTILE）扎根浙江绍兴柯桥——中国轻纺城，是一家本地柯桥数码印花加工厂，"
    "专注宽幅数码印花加工 10 年。"
    "主营窗帘印花、墙布印花、家纺印花（床单印花、被套、四件套），"
    "工艺覆盖分散印花、热转印、宽幅数码印花加工三大类。"
    "1 米起印、免费打样，从打样到大货由专人跟到底。"
)

INTRO_EN = (
    "J.LINK TEXTILE is a wide-format digital textile printing mill based in Keqiao, "
    "Shaoxing, Zhejiang — China Textile City — with 10 years of focus on wide-width "
    "digital printing. We print curtain fabric, wallcovering and home textiles "
    "(bed sheets, duvet covers, four-piece sets) via disperse printing, heat transfer "
    "and wide-format digital printing. 1-meter minimum, free sampling, one dedicated "
    "contact from sample to bulk."
)

BRIDGE_ZH = "上面这些答案不是话术，而是我们每天在产线上做的事——"
BRIDGE_EN = "These are not sales lines — they are what our line does every day. "

# ═══════════════════════ 主题推断 ═══════════════════════
# 顺序即优先级：品类词优先，再工艺 / 幅宽 / 批量 / 控色 / 出口 / 选厂，最后兜底 general。
_KIND_RULES = [
    ("bedding", ["床单", "被套", "四件套", "床品", "家纺", "bedding", "bed-sheet", "bed sheet",
                 "home-textile", "home textile", "duvet"]),
    ("wallcovering", ["墙布", "壁布", "墙纸", "wallcovering", "wall-covering", "mural"]),
    ("curtain", ["窗帘", "窗纱", "帘布", "curtain", "blackout", "chenille", "drape"]),
    ("wide", ["320", "ultra-wide", "ultrawide", "wide-format", "wide format", "宽幅", "超宽", "无缝", "seamless"]),
    ("smallbatch", ["小批量", "小单", "起印", "打样", "封样", "翻单", "small-batch", "small batch",
                    "sample", "minimum", "reorder"]),
    ("color", ["色差", "控色", "对色", "色牢", "color", "colour", "shade", "consistency"]),
    ("export", ["出口", "外贸", "跨境", "合规", "oeko", "export", "cross-border", "compliance"]),
    ("process", ["工艺", "分散", "热转印", "印花机", "对比", "process", "disperse", "heat transfer",
                 "sublimation", "digital-vs"]),
    ("factory", ["柯桥", "绍兴", "工厂", "选厂", "产业带", "keqiao", "shaoxing", "factory", "sourcing"]),
]


def infer_kind(topic=None):
    """从当篇内容推断主题类别，用于选择匹配的问答组。

    两段式匹配：先用「slug + h1」做强匹配（当篇主题最可靠的信号），
    再用「keywords + meta + hero」做弱匹配兜底 —— 避免关键词里提了一句别的品类就跑偏。
    """
    if not topic:
        return "general"
    if isinstance(topic, str):
        strong = weak = topic.lower()
    else:
        strong = " ".join(str(topic.get(k, "") or "") for k in ("slug", "h1")).lower()
        weak = " ".join(str(topic.get(k, "") or "") for k in ("keywords", "meta", "hero")).lower()
    for text in (strong, weak):
        if not text:
            continue
        for kind, keys in _KIND_RULES:
            if any(k.lower() in text for k in keys):
                return kind
    return "general"


# ═══════════════════════ 问答库（结篇选题 → 能力/匹配度） ═══════════════════════
QA_TITLES = {
    "zh": {
        "curtain": "窗帘印花找代工，客户最常问我们的三个问题",
        "wallcovering": "墙布印花找代工，客户最常问我们的三个问题",
        "bedding": "床单被套印花找代工，客户最常问我们的三个问题",
        "wide": "宽幅这类活，客户最常问我们的三个问题",
        "process": "工艺怎么选，客户最常问我们的三个问题",
        "smallbatch": "小批量、打样这类单，客户最常问我们的三个问题",
        "color": "色差与多批次控色，客户最常问我们的三个问题",
        "export": "出口单的合规与品质，客户最常问我们的三个问题",
        "factory": "选印花工厂，客户最常问我们的三个问题",
        "general": "找宽幅数码印花代工，客户最常问我们的三个问题",
    },
    "en": {
        "curtain": "Curtain printing outsourcing: three questions we are asked most",
        "wallcovering": "Wallcovering printing: three questions we are asked most",
        "bedding": "Bed sheet and duvet printing: three questions we are asked most",
        "wide": "Wide-format work: three questions we are asked most",
        "process": "Choosing a printing process: three questions we are asked most",
        "smallbatch": "Small batches and sampling: three questions we are asked most",
        "color": "Color drift and batch control: three questions we are asked most",
        "export": "Export orders: three questions we are asked most",
        "factory": "Choosing a printing mill: three questions we are asked most",
        "general": "Wide-format digital printing: three questions we are asked most",
    },
}

QA = {
    "zh": {
        "curtain": [
            ("2.8 米、3 米层高的落地窗，你们门幅跟得上吗？",
             "跟得上。宽幅产线覆盖 200 / 220 / 240 / 260 / 280 / 320CM 六大标准幅宽，最高 320CM 整幅一次成、无切断。3 米层高的落地窗选 320CM 直接整幅下料，垂感和花型延续都在同一幅布上。"),
            ("雪尼尔、遮光布、纱料，能一起做吗？",
             "都能做。分散印花和热转印覆盖涤纶类窗帘布，雪尼尔、遮光涂层、纱料按克重与底材分别匹配前处理和上浆参数，同花色跨底布也能把色差压在 ΔE≤1.5 以内。"),
            ("大货颜色和打样对不上，怎么避免？",
             "打样阶段就把色定死：1 米起印、免费打样，先出 1-2 个花型实样给你确认，签字封样再排大货。大货逐卷在 D65 标准光源下对色，1 米布过 7 点检验，颜色以封样为准。"),
        ],
        "wallcovering": [
            ("一面墙能不能一张图印完？",
             "可以。墙布要的就是整幅——200 / 220 / 240 / 260 / 280 / 320CM 六档全覆盖，住宅 2.7-3 米层高选 320CM，一面墙一幅过，上墙没有接痕，施工也省工。"),
            ("无纺底、热熔底、十字布基，能直接上机吗？",
             "三种常规底材都能做。无纺底和热熔底走分散印花，涂层类按工艺区分前处理；底材吸水率和克重不同，先试一段确认发色与渗透，再整卷开印，避免整卷报废。"),
            ("只做一面墙十几米，接不接？",
             "接。1 米起印、不需要制版，一面墙的量也能排产；打样 1-2 天出实样，大货 5-7 个工作日交货。"),
        ],
        "bedding": [
            ("床单印花用什么工艺，洗几次会掉色？",
             "床单印花走分散印花和热转印两条线，涤纶及涤棉混纺面料都能上。色牢度 4 级以上，耐水洗耐日晒，通过 OEKO-TEX Standard 100 认证，贴身用也放心。"),
            ("200×230、245×250 这些尺寸，幅宽怎么配？",
             "按成品尺寸倒推：240CM 走 200×230 的床单，260CM 走 245×250，280 / 320CM 做加大与酒店规格。整幅一次成、无切断，四边包边不用预留接位。"),
            ("一个花型只做几百米，成本会不会很高？",
             "数码印花加工不打版，1 米起印，几百米和一两千米的单价差主要在坯布和工艺，不在版费上。先免费打样看手感与色光，确认了再定量。"),
        ],
        "wide": [
            ("320CM 是真能稳定量产，还是只能做样品？",
             "量产。320CM 是六大标准幅宽里最高的一档（200/220/240/260/280/320CM），8+ 条进口高速线 24 小时运转、月产能 60 万米，宽幅单不靠单台设备硬撑。"),
            ("这么宽，中间会不会比两边浅？",
             "不会。8 色喷头逐段校准，幅内色差靠在线检测加逐卷 D65 对色控制，1 米布过 7 点检验。幅宽越大越吃设备稳定性，这正是老线跑出来的余量。"),
            ("宽幅打样要等多久？",
             "打样 1-2 天，1 米起、免费；大货 5-7 个工作日，急单可以插排。"),
        ],
        "process": [
            ("我的面料该走分散印花还是热转印？",
             "看成分和用途：涤纶类两种都能走，要垂感和透气走分散印花，要图案锐利和快返走热转印；棉类另配工艺。寄 1 米坯布来，试印后给结论，不靠猜。"),
            ("数码印花加工比传统印花贵多少？",
             "单米报价通常高于传统，但省掉制版和起订门槛——1 米起印、1 天打样，小单、多花型、翻单快，综合成本往往更低，尤其适合测款和定制单。"),
            ("换花型要不要停机洗机、会不会串色？",
             "数码直喷无版，换花型只换文件，不用洗网；不同花型按深到浅排产并做清洗确认，串色风险靠流程控制，不靠运气。"),
        ],
        "smallbatch": [
            ("1 米真的能做？",
             "能。1 米起印、无需制版，打样就是这个量级；测款、寄样、拍图都够用，确认后按米追加，不用一次压库存。"),
            ("打样收费吗？多久出？",
             "免费打样，首单 1-2 个花型；1-2 天出实样，随样附色卡，大货照封样执行。"),
            ("小批量单价会不会高很多？",
             "单价随米数递减，但省掉了版费和起订门槛。对测款来说，先小批量验证花型再翻单，比一次备几千米稳。"),
        ],
        "color": [
            ("第一批和第二批颜色总有偏差，你们怎么控？",
             "靠体系不靠师傅手感。打样签字封样，色卡与工艺参数一并归档，翻单直接调档；同一花型跨批次按封样对色，色差控制 ΔE≤1.5。"),
            ("不同底布、不同克重会不会跑色？",
             "会，所以要分底材建档。同花色在雪尼尔、遮光涂层、无纺底上分别记录墨量与上浆参数，换底布先试一段再整卷开印。"),
            ("出了色差客诉怎么处理？",
             "先看封样：以签字样为基准判定责任，是我们工艺偏移就返工补数，是坯布批次差异就调工艺重出小样确认，判定规则写进订单。"),
        ],
        "export": [
            ("出口订单需要什么合规文件？",
             "通过 OEKO-TEX Standard 100 认证，SGS 可配合检测；色牢度 4 级以上、ΔE≤1.5 的批次数据可随货提供，报关资料按客户要求出。"),
            ("海外客户最担心色差和交期，怎么保证？",
             "封样后按样生产、逐卷 D65 对色；标准交期 5-7 个工作日，出口单提前排产，装柜前可提供验货照片。"),
            ("小批量试单能不能做？",
             "能。1 米起印、免费打样，先寄样确认再下单；跨境电商测款常用这个路径，跑起来再按米翻单。"),
        ],
        "factory": [
            ("你们是工厂还是贸易公司？",
             "工厂。柯桥数码印花加工厂，10 年只做宽幅数码印花加工，8+ 条进口高速线在自有车间，随时可以来看机、现场打样。"),
            ("怎么判断一家印花厂靠不靠谱？",
             "看四件事：设备幅宽是否覆盖你要的门幅、有没有封样与对色流程、打样是否免费且快、敢不敢让你进车间看大货在跑。这四条我们都能当场验。"),
            ("交期和产能撑得住大单吗？",
             "月产能 60 万米，8+ 条线 24 小时运转，单批次花型一致；常规 5-7 个工作日，急单可插排，大单可分段交付。"),
        ],
        "general": [
            ("你们主要做哪些品类？",
             "窗帘印花、墙布印花、家纺印花三大类，家纺里以床单印花、被套、四件套为主；工艺覆盖分散印花、热转印、宽幅数码印花加工。"),
            ("幅宽、起订量、交期是什么水平？",
             "200 / 220 / 240 / 260 / 280 / 320CM 六大标准幅宽，最高 320CM 整幅一次成；1 米起印、免费打样；打样 1-2 天，大货 5-7 个工作日。"),
            ("怎么报价、怎么开始合作？",
             "发花型文件 + 门幅 + 米数 + 面料成分，当天给报价区间；寄 1 米坯布免费打样，确认封样后排产。"),
        ],
    },
    "en": {
        "curtain": [
            ("Our drop is 2.8-3 m. Can you cover it without joining two pieces?",
             "Yes. Six standard widths: 200 / 220 / 240 / 260 / 280 / 320CM, up to 320CM printed in one piece with no cutting — a 3 m drop comes off a single panel, so drape and pattern continuity stay unbroken."),
            ("Can you handle chenille, blackout and sheer in one order?",
             "Yes. Disperse printing and heat transfer cover polyester curtain fabrics; chenille, coated blackout and sheer each get their own pre-treatment and sizing recipe, keeping colour drift within ΔE 1.5 across substrates."),
            ("How do you stop bulk shade from drifting away from the sample?",
             "Colour is locked at sampling: 1-meter minimum, free samples, you approve 1-2 patterns in hand, then we seal the standard. Bulk rolls are matched under D65 light with 7-point inspection per meter."),
        ],
        "wallcovering": [
            ("Can one wall be printed as a single drop?",
             "Yes — that is the point of wide format. 200 to 320CM covered in six standard widths; at a typical 2.7-3 m ceiling, 320CM lets one wall run as a single sheet with no seam on the wall."),
            ("Do non-woven, hot-melt and cross-base backings all run on your line?",
             "All three. Non-woven and hot-melt run disperse printing; coated bases get a different pre-treatment. Because absorbency and grammage differ, we test a short run before printing the full roll."),
            ("Will you take a single-wall order of just a dozen meters?",
             "Yes. 1-meter minimum with no plate-making; sampling in 1-2 days, bulk in 5-7 working days."),
        ],
        "bedding": [
            ("Which process for bed sheets, and will it fade after washing?",
             "Bed sheet printing runs on disperse printing or heat transfer, on polyester and poly-cotton blends. Colour fastness grade 4+, wash and light resistant, OEKO-TEX Standard 100 certified."),
            ("How do widths map to 200×230 and 245×250 sheet sizes?",
             "We work back from the finished size: 240CM for 200×230, 260CM for 245×250, 280/320CM for oversized and hotel specs — printed in one piece, so hemming needs no allowance."),
            ("Is a few hundred meters per pattern too small to be economical?",
             "Digital printing needs no plates and starts at 1 meter. The gap between 300 m and 1,500 m sits in fabric and process, not in plate cost. Sample free first, then set quantity."),
        ],
        "wide": [
            ("Is 320CM genuinely production-ready, or sample-only?",
             "Production. 320CM is the top of our six standard widths (200/220/240/260/280/320CM), running on 8+ imported high-speed lines, 24 hours, 600,000 m monthly."),
            ("At that width, does the middle print lighter than the edges?",
             "No. Eight-colour heads are calibrated zone by zone, with in-line checks plus D65 roll matching and 7-point inspection — the wider the fabric, the more machine stability matters."),
            ("How long is sampling on wide widths?",
             "1-2 days, free, from 1 meter; bulk in 5-7 working days, urgent runs can jump the queue."),
        ],
        "process": [
            ("Should my fabric go through disperse printing or heat transfer?",
             "Depends on fibre and use: polyester suits both — disperse for drape and breathability, heat transfer for sharper detail and faster turnaround; cotton needs a different route. Send 1 meter and we print a trial."),
            ("How much more expensive is digital than conventional printing?",
             "Per-meter price is usually higher, but plates and minimums disappear — 1-meter start, 1-day sampling. For small runs, many patterns and fast reorders, total cost is often lower."),
            ("Does changing a pattern require stopping to clean, and can colours bleed?",
             "No plates, so a pattern change is a file change. We sequence dark to light and verify cleaning between runs — bleed control is process, not luck."),
        ],
        "smallbatch": [
            ("Is a 1-meter minimum real?",
             "Yes. 1-meter minimum, no plate-making; that is exactly the sampling quantity — enough for a look, a photo shoot or a buyer's approval, then add meters."),
            ("Do you charge for samples, and how fast?",
             "Free sampling, 1-2 patterns for a first order; 1-2 days with a colour card, and bulk follows the sealed standard."),
            ("Is small-batch pricing much higher?",
             "Unit price falls with volume, but plates and minimums are gone. For testing a pattern, a small run followed by a reorder beats stocking thousands of meters."),
        ],
        "color": [
            ("Batch one and batch two never match — how do you control it?",
             "By system, not by feel. The approved sample is sealed with its colour card and process parameters on file; reorders pull the same record and match to the sealed standard at ΔE 1.5."),
            ("Do different substrates or grammages drift?",
             "They can, so we file each substrate separately — ink load and sizing recorded for chenille, coated blackout and non-woven. A new substrate gets a trial run first."),
            ("What happens if a customer reports a shade complaint?",
             "We start from the sealed sample: if our process drifted we reprint, if the greige batch differs we adjust and re-approve a small lot. The rule is written into the order."),
        ],
        "export": [
            ("What compliance documents do export orders need?",
             "OEKO-TEX Standard 100 certification, SGS testing on request, batch data for colour fastness grade 4+ and ΔE 1.5 supplied with the goods; customs paperwork as required."),
            ("Overseas buyers worry about shade and lead time — how do you cover that?",
             "Sealed sample drives production, rolls matched under D65. Standard lead time 5-7 working days, export orders scheduled ahead, inspection photos before loading."),
            ("Can you take a small trial order?",
             "Yes — 1-meter minimum, free sampling, approve the sample then order. It is the usual route for cross-border sellers testing a pattern."),
        ],
        "factory": [
            ("Are you a mill or a trading company?",
             "A mill. A Keqiao digital printing factory, 10 years on wide-format digital textile printing only, 8+ imported high-speed lines in our own workshop — visit and sample on site."),
            ("How do I tell a reliable printing mill from a reseller?",
             "Four checks: does the width cover your drop, is there a sealed-sample and colour-matching process, is sampling free and fast, will they let you walk the floor while bulk runs. We pass all four on the spot."),
            ("Can your capacity carry a large order?",
             "600,000 meters a month on 8+ lines round the clock, consistent within a batch; 5-7 working days standard, urgent runs queued in, large orders shipped in stages."),
        ],
        "general": [
            ("What do you print?",
             "Curtain fabric, wallcovering and home textiles — bed sheets, duvet covers and four-piece sets — via disperse printing, heat transfer and wide-format digital printing."),
            ("What are your widths, minimums and lead times?",
             "Six standard widths 200/220/240/260/280/320CM, up to 320CM in one piece; 1-meter minimum with free sampling; 1-2 days sampling, 5-7 working days bulk."),
            ("How do we start and get a price?",
             "Send artwork, width, meters and fibre content for a quote the same day; send 1 meter of greige for a free sample, then we schedule after the standard is sealed."),
        ],
    },
}


def qa_pairs(lang="zh", topic=None):
    """返回 (标题, [(问题, 答案), ...]) —— 供渲染与 FAQPage JSON-LD 共用。"""
    kind = infer_kind(topic) if not isinstance(topic, str) or topic not in QA["zh"] else topic
    if kind not in QA["zh"]:
        kind = "general"
    lang = "en" if lang == "en" else "zh"
    return QA_TITLES[lang][kind], QA[lang][kind]


def _links(items):
    return "".join(
        '<a href="%s">%s</a>' % (href, label) for href, label in items
    )


def _qa_html(pairs, lang):
    qtag = "Q" if lang == "zh" else "Q"
    out = ['  <div class="cb-qa">']
    for q, a in pairs:
        out.append(
            '    <div class="cb-qa-item">\n'
            '      <p class="cb-q"><span class="cb-qtag">%s</span>%s</p>\n'
            '      <p class="cb-a"><span class="cb-atag">A</span>%s</p>\n'
            '    </div>' % (qtag, q, a)
        )
    out.append('  </div>')
    return "\n".join(out)


def company_block(lang="zh", topic=None):
    """返回统一收尾段 HTML（lang: zh / en；topic: slug 字符串或含 h1/keywords/meta 的 dict）。

    输出为**可内嵌的内容块**（不含 <section>/<div class="container">），
    由调用方紧贴正文末尾、与正文同宽放置；页面顺序：
        正文 → 收尾（本块）→ 常见问题 → CTA → 页脚
    """
    lang = "en" if lang == "en" else "zh"
    title, pairs = qa_pairs(lang, topic)
    qa_html = _qa_html(pairs, lang)

    if lang == "en":
        caps = "".join("<li>%s</li>" % c for c in CAPS_EN)
        return (
            '<div class="company-block" id="company">\n'
            '  <p class="cb-kicker">J.LINK TEXTILE · 匠领数码</p>\n'
            '  <h2>%s</h2>\n'
            '  <p class="cb-sub">Keqiao, Shaoxing, Zhejiang (China Textile City) · '
            '10 years · 500+ B2B clients</p>\n'
            '%s\n'
            '  <p class="cb-intro">%s</p>\n'
            '  <h3 class="cb-h3">Wide-format capability</h3>\n'
            '  <ul class="cb-list">%s</ul>\n'
            '  <div class="cb-contact">\n'
            '    <div class="cb-item"><span class="cb-ic">📞</span><div>'
            '<b>Phone / WeChat</b><a class="cb-tel" href="tel:%s">+86 177 6988 6009</a>'
            '<span class="cb-note">Mr. Zhang · WeChat same number</span></div></div>\n'
            '    <div class="cb-item"><span class="cb-ic">📍</span><div>'
            '<b>Factory address</b><span>%s</span></div></div>\n'
            '  </div>\n'
            '  <p class="cb-links">%s</p>\n'
            '</div>\n'
        ) % (title, qa_html, BRIDGE_EN + INTRO_EN, caps, PHONE_TEL, ADDR_EN, _links(LINKS_EN))

    caps = "".join("<li>%s</li>" % c for c in CAPS_ZH)
    return (
        '<div class="company-block" id="company">\n'
        '  <p class="cb-kicker">J.LINK TEXTILE · 匠领数码</p>\n'
        '  <h2>%s</h2>\n'
        '  <p class="cb-sub">浙江绍兴柯桥（中国轻纺城）· 十年老厂 · 500+ B 端客户</p>\n'
        '%s\n'
        '  <p class="cb-intro">%s</p>\n'
        '  <h3 class="cb-h3">宽幅实力</h3>\n'
        '  <ul class="cb-list">%s</ul>\n'
        '  <div class="cb-contact">\n'
        '    <div class="cb-item"><span class="cb-ic">📞</span><div>'
        '<b>电话 / 微信</b><a class="cb-tel" href="tel:%s">%s</a>'
        '<span class="cb-note">%s，微信同号</span></div></div>\n'
        '    <div class="cb-item"><span class="cb-ic">📍</span><div>'
        '<b>工厂地址</b><span>%s</span></div></div>\n'
        '  </div>\n'
        '  <p class="cb-links">%s</p>\n'
        '</div>\n'
    ) % (title, qa_html, BRIDGE_ZH + INTRO_ZH, caps, PHONE_TEL, PHONE, CONTACT, ADDR, _links(LINKS_ZH))


def company_jsonld():
    """Organization + ContactPoint JSON-LD（与收尾段 NAP 对齐，强化 GEO 实体一致性）。"""
    import json as _json
    return _json.dumps({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "匠领数码（J.LINK TEXTILE）",
        "url": "https://bu6789.com/",
        "telephone": "+86-177-6988-6009",
        "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "sales",
            "name": CONTACT,
            "telephone": "+86-177-6988-6009",
            "areaServed": "CN",
            "availableLanguage": ["zh-CN", "en"],
        },
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "齐贤镇兴浦路88号盛超针纺园区二幢南面五楼",
            "addressLocality": "绍兴市",
            "addressRegion": "浙江省",
            "addressCountry": "CN",
        },
    }, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    for k in ("curtain", "wallcovering", "bedding", "wide", "general"):
        print("#", k, "→", qa_pairs("zh", k)[0])
    print(company_block("zh", "curtain-digital-printing")[:600])
