# -*- coding: utf-8 -*-
"""
Phase 1 Schema 补齐：
1) 给全站核心页 + 已发文章补 LocalBusiness（与首页同 @id，声明同一实体）
2) 给 3 个产品页（有真实 FAQ 区块）补 FAQPage（精确镜像可见问答）
3) 同步更新 auto_article.py 模板，未来自动文章也带 LocalBusiness
幂等：已含对应 schema 的跳过。
"""
import re, json, os, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LB_BLOCK = '''  <!-- 结构化数据：LocalBusiness（与首页同一实体，全站统一 @id） -->
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    "@id": "https://bu6789.com/#localbusiness",
    "name": "匠领数码",
    "alternateName": "J.LINK TEXTILE 绍兴柯桥宽幅数码印花厂",
    "description": "绍兴柯桥宽幅数码印花加工厂，专注窗帘、墙布、家纺数码印花，幅宽200-320CM，分散印花/涤纶印花/宽幅数码印花，1米起印、免费打样",
    "image": "https://bu6789.com/logo.png",
    "url": "https://bu6789.com/",
    "telephone": "+86-177-6988-6009",
    "priceRange": "$$",
    "currenciesAccepted": "CNY",
    "paymentAccepted": "Cash, Bank Transfer, Alipay, WeChat Pay",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "齐贤镇兴浦路88号盛超针纺园区二幢南面五楼",
      "addressLocality": "绍兴市柯桥区",
      "addressRegion": "浙江省",
      "postalCode": "312000",
      "addressCountry": "CN"
    },
    "geo": {
      "@type": "GeoCoordinates",
      "latitude": 30.0729,
      "longitude": 120.4921
    },
    "openingHoursSpecification": [
      {
        "@type": "OpeningHoursSpecification",
        "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "opens": "08:00",
        "closes": "18:00"
      }
    ],
    "areaServed": [
      {"@type": "Country", "name": "中国"},
      {"@type": "City", "name": "绍兴"},
      {"@type": "City", "name": "杭州"},
      {"@type": "City", "name": "宁波"},
      {"@type": "City", "name": "上海"},
      {"@type": "City", "name": "广州"},
      {"@type": "City", "name": "义乌"}
    ],
    "hasOfferCatalog": {
      "@type": "OfferCatalog",
      "name": "宽幅数码印花服务",
      "itemListElement": [
        {"@type": "OfferCatalog", "name": "窗帘数码印花"},
        {"@type": "OfferCatalog", "name": "墙布数码印花"},
        {"@type": "OfferCatalog", "name": "家纺数码印花"}
      ]
    }
  }
  </script>
'''

def extract_faq(path):
    html = open(path, encoding='utf-8').read()
    qs = re.findall(r'class="faq-q"[^>]*>(.*?)</p>', html, re.S)
    as_ = re.findall(r'class="faq-a"[^>]*>(.*?)</p>', html, re.S)
    pairs = []
    for q, a in zip(qs, as_):
        q = re.sub(r'<[^>]+>', '', q).strip()
        a = re.sub(r'<[^>]+>', '', a).strip()
        q = re.sub(r'^Q[：:]\s*', '', q).strip()
        if q and a:
            pairs.append((q, a))
    return pairs

def build_faq_block(pairs):
    items = []
    for q, a in pairs:
        items.append('      {\n'
                     '        "@type": "Question",\n'
                     f'        "name": {json.dumps(q, ensure_ascii=False)},\n'
                     f'        "acceptedAnswer": {{"@type": "Answer", "text": {json.dumps(a, ensure_ascii=False)}}}\n'
                     '      }')
    body = ',\n'.join(items)
    return ('  <!-- 结构化数据：FAQPage（镜像本页可见 FAQ） -->\n'
            '  <script type="application/ld+json">\n'
            '  {\n'
            '    "@context": "https://schema.org",\n'
            '    "@type": "FAQPage",\n'
            '    "mainEntity": [\n'
            f'{body}\n'
            '    ]\n'
            '  }\n'
            '  </script>\n')

def insert_before_head(html, block):
    if '</head>' in html:
        return html.replace('</head>', block + '</head>', 1)
    return html  # 无 head 则不插

def process(path, lb=True, faq_pairs=None):
    html = open(path, encoding='utf-8').read()
    added = []
    # LocalBusiness
    if lb and '"@type": "LocalBusiness"' not in html:
        html = insert_before_head(html, LB_BLOCK)
        added.append('LocalBusiness')
    # FAQPage
    if faq_pairs and '"@type": "FAQPage"' not in html:
        html = insert_before_head(html, build_faq_block(faq_pairs))
        added.append('FAQPage')
    if added:
        open(path, 'w', encoding='utf-8').write(html)
        print(f"  + {os.path.relpath(path, ROOT)}: 注入 {', '.join(added)}")
    return added

# ---- 1) 核心页 ----
CORE_LB_ONLY = ['about.html', 'en.html', 'news.html']
PRODUCTS = ['products-curtain.html', 'products-home-textile.html', 'products-wallcovering.html']

print("== 核心页 LocalBusiness ==")
for f in CORE_LB_ONLY:
    p = os.path.join(ROOT, f)
    if os.path.exists(p):
        process(p, lb=True, faq_pairs=None)

print("== 产品页 LocalBusiness + FAQPage ==")
for f in PRODUCTS:
    p = os.path.join(ROOT, f)
    if os.path.exists(p):
        pairs = extract_faq(p)
        print(f"  {f}: 抽得 FAQ {len(pairs)} 条")
        process(p, lb=True, faq_pairs=pairs)

# ---- 2) 已发文章补 LocalBusiness ----
print("== 已发文章 LocalBusiness ==")
cnt = 0
for art in glob.glob(os.path.join(ROOT, 'articles', '*.html')):
    r = process(art, lb=True, faq_pairs=None)
    if r:
        cnt += 1
print(f"  文章注入 LocalBusiness 共 {cnt} 篇")

# ---- 3) 更新 auto_article.py 模板 ----
TPL = os.path.join(ROOT, 'scripts', 'auto_article.py')
t = open(TPL, encoding='utf-8').read()
if '"@type": "LocalBusiness"' not in t:
    # 在 Article 的 </script> 后追加 LocalBusiness 块（双花括号供 .format 使用）
    lb_tpl = (
        '  <script type="application/ld+json">\n'
        '  {{\n'
        '    "@context": "https://schema.org",\n'
        '    "@type": "LocalBusiness",\n'
        '    "@id": "https://bu6789.com/#localbusiness",\n'
        '    "name": "匠领数码",\n'
        '    "alternateName": "J.LINK TEXTILE 绍兴柯桥宽幅数码印花厂",\n'
        '    "description": "绍兴柯桥宽幅数码印花加工厂，专注窗帘、墙布、家纺数码印花，幅宽200-320CM，分散印花/涤纶印花/宽幅数码印花，1米起印、免费打样",\n'
        '    "image": "https://bu6789.com/logo.png",\n'
        '    "url": "https://bu6789.com/",\n'
        '    "telephone": "+86-177-6988-6009",\n'
        '    "address": {{\n'
        '      "@type": "PostalAddress",\n'
        '      "streetAddress": "齐贤镇兴浦路88号盛超针纺园区二幢南面五楼",\n'
        '      "addressLocality": "绍兴市柯桥区",\n'
        '      "addressRegion": "浙江省",\n'
        '      "postalCode": "312000",\n'
        '      "addressCountry": "CN"\n'
        '    }}\n'
        '  }}\n'
        '  </script>\n'
    )
    # 锚点：Article 块结束的 </script>\n  <style>
    marker = '  </script>\n  <style>'
    if marker in t:
        t = t.replace(marker, '  </script>\n' + lb_tpl + '  <style>', 1)
        open(TPL, 'w', encoding='utf-8').write(t)
        print("== auto_article.py 模板已加 LocalBusiness ==")
    else:
        print("!! 未找到模板锚点，跳过模板更新")
else:
    print("== auto_article.py 模板已有 LocalBusiness，跳过 ==")

print("DONE")
