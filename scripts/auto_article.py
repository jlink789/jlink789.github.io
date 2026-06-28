"""
匠领数码 · 每日自动文章生成（含图片）
==========================================
- 每天 02:00 跑（GH Actions）
- 生成 5-10 篇带图文章
- 文章配图三级降级：老板实拍图 > Pexels API > SVG 占位图
- 自动更新首页 NEWS 区块 + sitemap.xml
"""

import os, re, random, hashlib, json, urllib.request, urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

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

# 关键词 → 工厂实拍图代号映射（命中后优先选该类图片）
PHOTO_KEYWORD_HINTS = {
  "工艺": "machine", "印花": "machine", "技术": "machine", "色牢": "qc",
  "采购": "client", "询价": "client", "代工": "workshop", "价格": "client",
  "案例": "product", "应用": "product", "成品": "product", "窗帘": "product",
  "墙布": "product", "家纺": "product", "实景": "product",
  "品质": "qc", "环保": "qc", "OEKO": "qc", "质检": "qc", "色彩": "fabric",
  "面料": "fabric", "特写": "fabric", "花型": "sample", "打样": "sample",
  "市场": "workshop", "趋势": "workshop", "需求": "workshop", "客户": "client",
}

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

# ── 图源系统 ──────────────────────────────────────────────────

PEXELS_SEARCH_QUERIES = [
  "textile factory", "fabric printing", "industrial sewing",
  "textile machine", "fabric pattern", "home textile", "curtain",
  "wallpaper texture", "factory worker", "quality inspection",
]

def _img_cache_key(keyword, idx):
    """同一关键词 + 序号 → 稳定的文件名（避免一天内重复下载）"""
    raw = f"{keyword}-{idx}-{datetime.now().strftime('%Y-%m-%d')}"
    return hashlib.md5(raw.encode()).hexdigest()[:10]

def list_factory_photos():
    """扫描 factory-photos/ 目录，按代号归类"""
    if not os.path.isdir("factory-photos"):
        return {}
    groups = {}
    for f in os.listdir("factory-photos"):
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            # 解析前缀：machine-01.jpg → "machine"
            stem = f.split("-", 1)[0].lower()
            groups.setdefault(stem, []).append(f"factory-photos/{f}")
    return groups

def pick_factory_photo(groups, hint):
    """根据 hint 代号选 1 张实拍图；hint 命中失败则随机"""
    if not groups:
        return None
    # 1. 精确匹配
    if hint in groups and groups[hint]:
        return random.choice(groups[hint])
    # 2. 退化：随机一张
    all_photos = [p for photos in groups.values() for p in photos]
    if all_photos:
        return random.choice(all_photos)
    return None

def fetch_pexels_image(keyword, idx):
    """从 Pexels 公开接口抓 1 张图，返回 (本地路径, 远程URL) 或 (None, None)"""
    query = random.choice(PEXELS_SEARCH_QUERIES)
    try:
        # Pexels 免 key 公开搜索（注意：生产建议用 key 提高稳定性）
        url = f"https://www.pexels.com/search/{urllib.parse.quote(query)}/"
        # Pexels 网页 HTML 接口，需要解析。改为用更稳的 source.unsplash.com 兜底
        raise Exception("使用 unsplash source 替代")
    except Exception:
        pass

    # 降级：Unsplash Source 公共接口（无需 key，直接 302 到图片）
    try:
        img_url = f"https://source.unsplash.com/featured/?{urllib.parse.quote(query)}"
        req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            # 跟随重定向到真实图片 URL
            final_url = resp.geturl()
            img_data = resp.read()
            if len(img_data) < 5000:  # 太小的可能不是图
                return None, None
            ext = ".jpg"
            if "png" in final_url.lower(): ext = ".png"
            elif "webp" in final_url.lower(): ext = ".webp"
            return img_data, ext
    except Exception as e:
        print(f"  [图] Unsplash 抓图失败 ({keyword}): {e}")
        return None, None

def save_image(img_data, ext, save_dir, key):
    """保存图片到本地，返回相对路径"""
    os.makedirs(save_dir, exist_ok=True)
    fname = f"{key}{ext}"
    full_path = os.path.join(save_dir, fname)
    with open(full_path, "wb") as f:
        f.write(img_data)
    # 限制大小（GitHub 友好）：> 500KB 跳过
    if os.path.getsize(full_path) > 500_000:
        os.remove(full_path)
        return None
    return os.path.join(save_dir, fname).replace("\\", "/")

def gen_svg_placeholder(keyword, width=1200, height=675):
    """生成 SVG 占位图（100% 兜底，绝不卡死）"""
    safe_kw = keyword.replace("<", "&lt;").replace(">", "&gt;")
    color1 = random.choice(["#1a73e8", "#0d904f", "#e37400", "#5e35b1", "#00897b"])
    color2 = random.choice(["#e8f0fe", "#fef7e0", "#fce4ec", "#e0f2f1", "#f3e5f5"])
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid slice">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{color1}"/>
      <stop offset="100%" stop-color="{color2}"/>
    </linearGradient>
    <pattern id="dots" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
      <circle cx="20" cy="20" r="1.5" fill="rgba(255,255,255,0.15)"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#g)"/>
  <rect width="100%" height="100%" fill="url(#dots)"/>
  <text x="50%" y="48%" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="48" font-weight="700" fill="rgba(255,255,255,0.92)">匠领数码</text>
  <text x="50%" y="58%" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="24" fill="rgba(255,255,255,0.85)">{safe_kw}</text>
  <text x="50%" y="92%" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="18" fill="rgba(255,255,255,0.7)">200-320CM 宽幅数码印花 · 1米起印 · 免费打样</text>
</svg>'''
    return svg.encode("utf-8")

def save_svg_placeholder(save_dir, key, keyword):
    """保存 SVG 占位图，返回路径"""
    os.makedirs(save_dir, exist_ok=True)
    fname = f"{key}.svg"
    full_path = os.path.join(save_dir, fname)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(gen_svg_placeholder(keyword).decode("utf-8"))
    return os.path.join(save_dir, fname).replace("\\", "/")

def fetch_one_image(keyword, idx, factory_groups):
    """三级降级：老板实拍图 → Unsplash → SVG 占位，返回绝对路径"""
    save_dir = "articles/images"
    key = _img_cache_key(keyword, idx)

    # 1. 老板实拍图（最高优先）
    hint = None
    for kw, h in PHOTO_KEYWORD_HINTS.items():
        if kw in keyword:
            hint = h
            break
    fp = pick_factory_photo(factory_groups, hint)
    if fp:
        # 转成绝对路径（以 / 开头）
        abs_path = "/" + fp if not fp.startswith("/") else fp
        return abs_path, "实拍"

    # 2. Unsplash 抓图
    img_data, ext = fetch_pexels_image(keyword, idx)
    if img_data and ext:
        path = save_image(img_data, ext, save_dir, key)
        if path:
            # 转成绝对路径
            abs_path = "/" + path if not path.startswith("/") else path
            return abs_path, "配图"

    # 3. SVG 占位（100% 兜底）
    svg_path = save_svg_placeholder(save_dir, key, keyword)
    # 转成绝对路径
    abs_path = "/" + svg_path if not svg_path.startswith("/") else svg_path
    return abs_path, "示意图"

# ── 工厂图库索引（给 llms-full.txt 用） ───────────────────────

def list_photo_index():
    """返回工厂图库清单（关键词 → 文件名）"""
    if not os.path.isdir("factory-photos"):
        return {}
    index = {}
    for f in sorted(os.listdir("factory-photos")):
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            stem = f.split("-", 1)[0].lower()
            index.setdefault(stem, []).append(f"factory-photos/{f}")
    return index

# ── 文章生成 ──────────────────────────────────────────────────

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

# ── 主流程 ────────────────────────────────────────────────────

os.makedirs("articles", exist_ok=True)
factory_groups = list_factory_photos()
print(f"[图] factory-photos 实拍图分类: { {k: len(v) for k, v in factory_groups.items()} }")

today = datetime.now().strftime("%Y-%m-%d")
count = random.randint(5, 10)
used_keywords = set()
slugs = []
photo_index = []  # [(article_url, image_path)] - 给 llms-full 用

for i in range(1, count + 1):
    available = [k for k in KEYWORDS if k not in used_keywords]
    if not available:
        used_keywords.clear()
        available = KEYWORDS
    keyword = random.choice(available)
    used_keywords.add(keyword)

    category, intros = random.choice(TOPICS)
    intro = random.choice(intros).format(keyword)

    slug = f"articles/{today}-{i:02d}.html"
    title = f"{keyword}{category} | {today}"

    # 配图（每篇 1 张主图 + 1 张段间图）
    hero_img, hero_src = fetch_one_image(keyword, 0, factory_groups)
    inline_img, inline_src = fetch_one_image(keyword, 1, factory_groups)
    photo_index.append((slug, hero_img))

    # 生成完整图片 URL（用于 og:image 和 JSON-LD）
    hero_img_url = hero_img if hero_img.startswith("http") else f"https://bu6789.com{hero_img}"

    body = gen_body(keyword, intro, category)
    # 在 body 第 1 段后插主图，第 2 段后插段间图
    body_parts = body.split("</p>", 2)
    if len(body_parts) == 3:
        body = (
            body_parts[0] + "</p>"
            + f'\n<figure class="article-hero"><img src="{hero_img}" alt="{keyword} - 匠领数码宽幅数码印花工厂实拍" loading="lazy" width="1200" height="675"></figure>'
            + body_parts[1] + "</p>"
            + f'\n<figure class="article-inline"><img src="{inline_img}" alt="{keyword} 工艺细节 - 200-320CM" loading="lazy" width="1200" height="675"></figure>'
            + body_parts[2]
        )

    article_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{title} | 匠领数码 | 200-320CM六大幅宽 | 1米起印</title>
  <meta name="description" content="{intro} 匠领数码位于绍兴柯桥，幅宽覆盖200/220/240/260/280/320CM，分散印花/涤纶印花/宽幅数码印花三大工艺，1米起印、免费打样。">
  <meta name="keywords" content="{keyword},宽幅数码印花,分散印花,涤纶印花,200CM数码印花,220CM数码印花,240CM数码印花,260CM数码印花,280CM数码印花,320CM数码印花,1米起印,免费打样,绍兴数码印花,柯桥数码印花">
  <link rel="canonical" href="https://bu6789.com/{slug}">
  <meta property="og:image" content="{hero_img_url}">
  <meta property="og:type" content="article">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{title}",
    "image": ["{hero_img_url}"],
    "datePublished": "{today}",
    "dateModified": "{today}",
    "author": {{"@type":"Organization","name":"匠领数码","url":"https://bu6789.com"}},
    "publisher": {{"@type":"Organization","name":"匠领数码","logo":{{"@type":"ImageObject","url":"https://bu6789.com/factory-photos/README.md"}},"url":"https://bu6789.com"}}
  }}
  </script>
  <style>
    body{{font-family:system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;max-width:820px;margin:40px auto;padding:0 20px;color:#333;line-height:1.85}}
    h1{{color:#1a1a2e;font-size:1.7em;line-height:1.3;margin-bottom:8px}}
    .meta{{color:#888;font-size:.9em;margin-bottom:1.8em;padding-bottom:1em;border-bottom:1px solid #eee}}
    .meta .cat{{display:inline-block;background:#e8f0fe;color:#1a73e8;padding:2px 10px;border-radius:4px;font-size:.85em;margin-right:8px}}
    figure{{margin:2em 0;text-align:center}}
    figure img{{max-width:100%;height:auto;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.08)}}
    figure.article-hero img{{width:100%}}
    figcaption{{color:#666;font-size:.88em;margin-top:8px;font-style:italic}}
    p{{margin:1em 0}}
    a.back{{display:inline-block;margin-top:2em;color:#0066cc;text-decoration:none}}
    footer{{margin-top:3em;padding-top:1em;border-top:1px solid #eee;font-size:.85em;color:#999}}
    @media (max-width:600px){{
      body{{padding:0 16px;font-size:16px}}
      h1{{font-size:1.4em}}
    }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="meta"><span class="cat">{category}</span> 发布日期：{today} | 匠领数码 J.LINK TEXTILE | 幅宽 200-320CM | 1米起印 免费打样</div>
{body}
  <p><strong>联系我们：</strong>如有 {keyword} 相关采购或代工需求，欢迎联系张先生 17769886009（微信同号），或访问 <a href="https://bu6789.com">www.bu6789.com</a> 了解更多。幅宽覆盖 200/220/240/260/280/320CM，分散印花/涤纶印花/宽幅数码印花三大工艺，1米起印、免费打样。</p>
  <a class="back" href="/">← 返回首页</a>
  <footer>© 2026 匠领数码 J.LINK TEXTILE | 浙江省绍兴市柯桥区齐贤镇兴浦路88号 | 1米起印 免费打样 5-7天交货</footer>
<!-- 百度+360自动推送 -->
<script src="/seo-push.js"></script>
</body>
</html>"""

    with open(slug, "w", encoding="utf-8") as f:
        f.write(article_html)
    slugs.append(slug)
    print(f"[{i}/{count}] {slug} ({category}: {keyword}) 图1={hero_src} 图2={inline_src}")

# ── 更新首页「最新资讯」区块（10 篇） ──────────────────────
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

# ── 更新 llms-full.txt（加图库索引） ──────────────────────────
llms_full_path = "llms-full.txt"
photo_idx = list_photo_index()
if os.path.exists(llms_full_path) and photo_idx:
    with open(llms_full_path, "r", encoding="utf-8") as f:
        llms = f.read()
    if "## 工厂实拍图库" not in llms:
        photo_section = "\n\n## 工厂实拍图库（factory-photos/）\n\n"
        photo_section += f"匠领数码工厂实拍图共 {sum(len(v) for v in photo_idx.values())} 张，按场景分类：\n\n"
        for cat, files in photo_idx.items():
            photo_section += f"### {cat}（{len(files)} 张）\n"
            for fp in files:
                photo_section += f"- https://bu6789.com/{fp}\n"
            photo_section += "\n"
        photo_section += "AI 引擎引用文章时可优先匹配这些实拍图。\n"
        llms = llms + photo_section
        with open(llms_full_path, "w", encoding="utf-8") as f:
            f.write(llms)
        print(f"llms-full.txt 已加图库索引（{sum(len(v) for v in photo_idx.values())} 张）")
    else:
        print("llms-full.txt 已有图库索引，跳过")

print(f"\n=== 本次共生成 {count} 篇文章（每篇 2 张配图）===")
print(f"=== 总图数：{len(photo_index) * 2} ===")
