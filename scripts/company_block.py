# -*- coding: utf-8 -*-
"""官网统一收尾模块 —— 业务介绍 + 宽幅实力清单 + NAP 联系方式 + 站内导航

供 gen_knowledge.py（知识库专题页）与 auto_article.py（每日文章页）共用，
保证「今天新生成的文章」与「以后所有文章 / 页面」的收尾口径完全一致。

口径（2026-10-31 定，单一数据源，改这里即可全站生效）：
- 联系人  张先生
- 电话/微信  17769886009（微信同号）
- 厂址  浙江省绍兴市柯桥区齐贤镇兴浦路88号盛超针纺园区二幢南面五楼
- 幅宽  200 / 220 / 240 / 260 / 280 / 320CM 六大标准，最高 320CM 整幅一次成、无切断
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


def _links(items):
    return "".join(
        '<a href="%s">%s</a>' % (href, label) for href, label in items
    )


def company_block(lang="zh"):
    """返回统一收尾段 HTML（lang: zh / en）。

    输出为**可内嵌的内容块**（不含 <section>/<div class="container">），
    由调用方放在文章正文容器末尾 —— 收尾归属"文章内容的最后一节"，
    而不是页面级独立版块（2026-10-31 老板定）。
    """
    if lang == "en":
        caps = "".join("<li>%s</li>" % c for c in CAPS_EN)
        return (
            '<div class="company-block" id="company">\n'
            '  <p class="cb-kicker">J.LINK TEXTILE · 匠领数码</p>\n'
            '  <h2>We are J.LINK — a wide-format digital printing mill in Keqiao</h2>\n'
            '  <p class="cb-sub">Keqiao, Shaoxing, Zhejiang (China Textile City) · '
            '10 years · 500+ B2B clients</p>\n'
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
        ) % (INTRO_EN, caps, PHONE_TEL, ADDR_EN, _links(LINKS_EN))

    caps = "".join("<li>%s</li>" % c for c in CAPS_ZH)
    return (
        '<div class="company-block" id="company">\n'
        '  <p class="cb-kicker">J.LINK TEXTILE · 匠领数码</p>\n'
        '  <h2>我们是匠领数码，柯桥的宽幅数码印花源头工厂</h2>\n'
        '  <p class="cb-sub">浙江绍兴柯桥（中国轻纺城）· 十年老厂 · 500+ B 端客户</p>\n'
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
    ) % (INTRO_ZH, caps, PHONE_TEL, PHONE, CONTACT, ADDR, _links(LINKS_ZH))


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
    print(company_block("zh"))
