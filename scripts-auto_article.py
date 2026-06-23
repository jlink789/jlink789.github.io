import random, os, re
from datetime import datetime

# ── 匠领数码 · 内容生产规范（永久规则） ─────────────────────────
# 幅宽：200CM / 220CM / 240CM / 260CM / 280CM / 320CM（六档全幅宽）
# 工艺：分散印花、涤纶印花、宽幅数码印花（三大工艺）
# 起印：1 米起印、免费打样

WIDTHS = ["200CM", "220CM", "240CM", "260CM", "280CM", "320CM"]
PROCESSES = ["分散印花", "涤纶印花", "宽幅数码印花"]
MOQ_LINE = "1米起印、免费打样"
WIDTH_LINE = "200/220/240/260/280/320CM六大标准幅宽"
PROCESS_LINE = "分散印花、涤纶印花、宽幅数码印花三大工艺"

KEYWORDS = [
  "宽幅数码印花","桌布印花","墙布印花","窗帘印花","家纺印花",
  "沙发面料印花","抱枕印花","床品印花","地毯印花","遮光窗帘印花",
  "高精密印花","雪尼尔印花","麂皮绒印花","棉麻印花","涤纶印花",
]

TOPICS = [
  ("市场趋势", [
    "随着家居定制化需求快速增长，2026年{}市场迎来新一轮扩张期，柯桥产区凭借完整供应链持续领跑。",
    "{}出口贸易回暖，东南亚及中东市场需求旺盛，国产数码印花品质获国际认可。",
    "2026年一季度柯桥轻纺城{}成交量同比上升，宽幅订单占比持续走高。",
    "{}市调显示：终端消费者对个性化印花面料偏好持续增强，定制化订单量增幅超30%。",
  ]),
  ("技术解析", [
    "{}技术解析：分散印花、涤纶印花、宽幅数码印花三大工艺如何选择，看完这篇你就懂了。",
    "深度解读{}：200-320CM宽幅数码印花为何成为高端家纺首选工艺？解析五大核心优势。",
    "{}色牢度对比：分散印花vs涤纶印花vs宽幅数码印花，不同面料匹配哪种印花工艺？技术参数全解读。",
    "{}色彩还原技术突破：1670万色精准输出，花纹细腻度达到行业新高度。",
  ]),
  ("采购指南", [
    "{}采购必看：宽幅数码印花如何避坑？资深从业者总结五大验收标准。",
    "{}代工指南：从打样到量产全流程解析，1米起印、免费打样、5-7天交货是怎么做到的？",
    "{}询价技巧：影响数码印花单价的关键因素有哪些？面料、工艺、色数一文讲透。",
    "初次采购{}注意事项：幅宽确认（200-320CM六档）、色差标准、水洗要求，提前了解少走弯路。",
  ]),
  ("应用案例", [
    "案例分享：某高端酒店全面采用{}数码印花方案，200-320CM多幅宽一体成型墙布效果惊艳。",
    "{}实景案例：别墅窗帘采用宽幅数码印花，免拼接无缝隙的高端体验如何？",
    "{}应用新场景：从家居到商业空间，数码印花正重新定义织物表面装饰。",
    "客户案例：品牌服装公司采用{}数码印花实现快反模式，1米起印小单快返降本增效。",
  ]),
  ("环保与品质", [
    "环保数码印花：{}采用环保墨水，Oeko-Tex国际认证，出口欧美无门槛。",
    "品质对话：{}如何确保每米布色彩一致？看匠领数码的5道质检流程。",
    "{}绿色生产：数码印花比传统印花节水70%以上，低碳环保成行业新标准。",
    "客户关心的{}问题：耐水洗、耐日晒、耐摩擦，实测数据告诉你真实表现。",
  ]),
  ("行业问答", [
    "问：{}数码印花最小起订量多少？答：1米起印，单花型不限数量，免费打样。",
    "问：{}数码印花和传统印花的成本差异大吗？对比分析来了。",
    "问：做{}数码印花需要准备什么文件？AI/PSD/PDF格式要求说明。",
    "问：{}数码印花交期一般多久？标准5-7天，急单可协调加急3天出。",
  ]),
]

def gen_body(keyword, intro, category):
    paragraphs = {
        "市场趋势": [
            f"<p>{intro}</p>",
            f"<p>业内人士分析指出，{keyword}领域在2026年延续了强势增长态势。产能区域分布仍以绍兴柯桥为核心，占全国数码印花产能40%以上。</p>",
            f"<p>匠领数码作为柯桥产区代表企业之一，拥有进口高速数码印花产线，幅宽覆盖{WIDTH_LINE}，{PROCESS_LINE}，{MOQ_LINE}，满足国内外客户一站式加工需求。</p>",
        ],
        "技术解析": [
            f"<p>{intro}</p>",
            f"<p>数码印花是直接将设计图案通过数字喷墨方式打印在面料上的技术，相比传统印花具有无需制版、色彩丰富（1670万色）、小单快返等核心优势。</p>",
            f"<p>匠领数码配备{PROCESS_LINE}三条产线，分别适配涤纶化纤、家纺面料、大幅面整幅加工。{WIDTH_LINE}，{MOQ_LINE}，适用于窗帘、墙布、家纺等大幅面产品。</p>",
        ],
        "采购指南": [
            f"<p>{intro}</p>",
            f"<p>作为B端采购商，选择数码印花合作工厂时建议重点关注：设备品牌与成色、打样能力与色准、起印门槛与最小起印弹性、交期稳定性、品质一致性这五个维度。</p>",
            f"<p>匠领数码提供免费打样服务，{MOQ_LINE}，标准交期5-7天，支持来图来样定制、合同生产等多种合作模式。{WIDTH_LINE}，{PROCESS_LINE}，覆盖全品类需求。</p>",
        ],
        "应用案例": [
            f"<p>{intro}</p>",
            f"<p>在中国轻纺城深耕多年的匠领数码，已服务超过500家B端客户，涵盖软装品牌、家居厂商、外贸公司、设计师品牌等多类型合作伙伴。</p>",
            f"<p>无论您是需要1米起印单次打样还是长期稳定供货，我们都提供灵活的合作方式和可靠的品质保障。{MOQ_LINE}、{WIDTH_LINE}。</p>",
        ],
        "环保与品质": [
            f"<p>{intro}</p>",
            f"<p>环保已成为数码印花行业的核心竞争力之一。我们采用的进口墨水通过Oeko-Tex Standard 100国际认证，适用于欧美及日本等高标准出口市场。</p>",
            f"<p>品质控制方面，从进厂坯布检验到成品终检，匠领数码建立了5道全流程质检体系，确保每米布的色差、渗透、手感均达标。{MOQ_LINE}、5-7天交货。</p>",
        ],
        "行业问答": [
            f"<p>{intro}</p>",
            f"<p>更多关于{keyword}的常见问题，欢迎访问匠领数码官网或直接致电张先生 17769886009（微信同号），我们将根据您的具体需求给出专业建议。{MOQ_LINE}，{WIDTH_LINE}。</p>",
        ],
    }
    return "\n".join(paragraphs.get(category, [f"<p>{intro}</p>"]))

# 确保 articles 目录存在
os.makedirs("articles", exist_ok=True)

today = datetime.now().strftime("%Y-%m-%d")
count = random.randint(5, 10)
used_keywords = set()
slugs = []

for i in range(1, count + 1):
    # 选一个没用过的关键词
    available = [k for k in KEYWORDS if k not in used_keywords]
    if not available:
        used_keywords.clear()
        available = KEYWORDS
    keyword = random.choice(available)
    used_keywords.add(keyword)

    # 随机选一个话题类型
    category, intros = random.choice(TOPICS)
    intro = random.choice(intros).format(keyword)

    slug = f"articles/{today}-{i:02d}.html"
    title = f"{keyword}{category} | {today}"
    body = gen_body(keyword, intro, category)

    article_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{title} | 匠领数码 | 200-320CM六大幅宽 | 1米起印</title>
  <meta name="description" content="{intro} 匠领数码位于绍兴柯桥，幅宽覆盖200/220/240/260/280/320CM，分散印花/涤纶印花/宽幅数码印花三大工艺，1米起印、免费打样。">
  <meta name="keywords" content="{keyword},宽幅数码印花,分散印花,涤纶印花,200CM数码印花,220CM数码印花,240CM数码印花,260CM数码印花,280CM数码印花,320CM数码印花,1米起印,免费打样,绍兴数码印花,柯桥数码印花">
  <link rel="canonical" href="https://bu6789.com/{slug}">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{title}",
    "datePublished": "{today}",
    "publisher": {{"@type":"Organization","name":"匠领数码","url":"https://bu6789.com"}},
    "author": {{"@type":"Organization","name":"匠领数码"}}
  }}
  </script>
  <style>
    body{{font-family:system-ui,sans-serif;max-width:800px;margin:40px auto;padding:0 20px;color:#333;line-height:1.8}}
    h1{{color:#1a1a2e;font-size:1.5em}}
    .meta{{color:#888;font-size:.9em;margin-bottom:1.5em}}
    .back{{display:inline-block;margin-top:2em;color:#0066cc;text-decoration:none}}
    footer{{margin-top:3em;padding-top:1em;border-top:1px solid #eee;font-size:.85em;color:#999}}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="meta">发布日期：{today} | 分类：{category} | 匠领数码 J.LINK TEXTILE | 幅宽200-320CM | 1米起印 免费打样</div>
{body}
  <p><strong>联系我们：</strong>如有 {keyword} 相关采购或代工需求，欢迎联系张先生 17769886009（微信同号），或访问 <a href="https://bu6789.com">www.bu6789.com</a> 了解更多。幅宽覆盖200/220/240/260/280/320CM，分散印花/涤纶印花/宽幅数码印花三大工艺，1米起印、免费打样。</p>
  <a class="back" href="/">← 返回首页</a>
  <footer>© 2026 匠领数码 J.LINK TEXTILE | 浙江省绍兴市柯桥区齐贤镇兴浦路88号 | 1米起印 免费打样 5-7天交货</footer>
</body>
</html>"""

    with open(slug, "w", encoding="utf-8") as f:
        f.write(article_html)
    slugs.append(slug)
    print(f"[{i}/{count}] {slug} ({category}: {keyword})")

# ── 更新首页「最新资讯」区块，取最新10篇 ──────────────────────
index_path = "index.html"
with open(index_path, "r", encoding="utf-8") as f:
    index = f.read()

article_files = sorted(
    [fn for fn in os.listdir("articles") if fn.endswith(".html")],
    reverse=True
)[:10]

items_html = ""
for fn in article_files:
    try:
        with open(f"articles/{fn}", "r", encoding="utf-8") as af:
            content = af.read()
            m_title = re.search(r"<title>(.*?)\s*\|\s*匠领数码", content)
            m_cat = re.search(r"分类：(\S+)", content)
            atitle = m_title.group(1) if m_title else fn
            cat = m_cat.group(1) if m_cat else ""
    except:
        atitle = fn
        cat = ""
    items_html += f'        <li><span class="news-date">{cat}</span> <a href="articles/{fn}">{atitle}</a></li>\n'

news_block = f"""<!-- NEWS_START -->
<section id="news" style="padding:40px 20px;max-width:900px;margin:0 auto">
  <h2 style="font-size:1.4em;color:#1a1a2e;margin-bottom:16px">最新资讯</h2>
  <ul style="list-style:none;padding:0;margin:0">
{items_html}    </ul>
</section>
<!-- NEWS_END -->"""

if "<!-- NEWS_START -->" in index:
    index = re.sub(r"<!-- NEWS_START -->.*?<!-- NEWS_END -->", news_block, index, flags=re.DOTALL)
else:
    for marker in ["<footer", "</body>"]:
        if marker in index:
            index = index.replace(marker, news_block + "\n" + marker, 1)
            break

with open(index_path, "w", encoding="utf-8") as f:
    f.write(index)
print(f"首页已更新，展示最新10篇文章")

# ── 更新 sitemap.xml ──────────────────────────────────────────
sitemap_path = "sitemap.xml"
with open(sitemap_path, "r", encoding="utf-8") as f:
    sm = f.read()

new_urls = ""
for s in slugs:
    if s not in sm:
        new_urls += f"""
  <url>
    <loc>https://bu6789.com/{s}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>yearly</changefreq>
    <priority>0.6</priority>
  </url>"""

if new_urls:
    sm = sm.replace("</urlset>", new_urls + "\n</urlset>")
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write(sm)
    print("sitemap.xml 已更新")

print(f"\\n=== 本次共生成 {count} 篇文章 ===")
