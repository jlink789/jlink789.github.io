#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_sitemap.py — 全站 sitemap 生成器（单一数据源）

扫描仓库内所有真实 HTML 页面，生成完整 sitemap.xml：
- 核心页 + 英文版（含 hreflang zh/en + x-default 配对）
- 全部 articles/ 长尾文章
- 自动排除：搜索引擎验证页、重复副本页、孤立样例页
- lastmod 取该文件最近一次 git 提交日期（无则今天）

供 GH Actions 调用：在 auto_article.py / build_news.py 之后运行，
作为 sitemap.xml 的唯一来源（取代原先分散的增量追加逻辑）。
"""
import re
import subprocess
import xml.sax.saxutils as su
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
SITE = "https://bu6789.com"
SITEMAP = ROOT / "sitemap.xml"

# ── 排除项 ──────────────────────────────────────────────
# 搜索引擎验证页
EXCLUDE_NAMES = {
    "ByteDanceVerify.html",
    "baidu_verify_codeva-r5qDCnEKAn.html",
    "article.html",                       # 孤立样例页（无 canonical）
    "products-curtain.html",              # 根目录重复副本，canonical 指向 products/*.html
    "products-wallcovering.html",
    "products-home-textile.html",
    "products/products-curtain.html",     # 嵌套重复副本
    "products/products-wallcovering.html",
    "products/products-home-textile.html",
}
# 其它百度验证页（前缀匹配）
EXCLUDE_PREFIX = ("baidu_verify_",)

# ── hreflang 配对（中文页, 英文页），中文页在前 ───────────────
PAIRS = [
    ("index.html", "en.html"),
    ("about.html", "en-about.html"),
    ("applications.html", "en-applications.html"),
    ("news.html", "en-news.html"),
    ("products/curtain.html", "products/en-curtain.html"),
    ("products/wallcovering.html", "products/en-wallcovering.html"),
    ("products/home-textile.html", "products/en-home-textile.html"),
    # 知识库 GEO 白皮书栏目（中英双语）
    ("knowledge/index.html", "knowledge/index-en.html"),
    ("knowledge/wide-format-digital-printing.html", "knowledge/en-wide-format-digital-printing.html"),
    ("knowledge/320cm-wide-format-printing.html", "knowledge/en-320cm-wide-format-printing.html"),
    ("knowledge/digital-vs-traditional-printing.html", "knowledge/en-digital-vs-traditional-printing.html"),
    ("knowledge/how-to-choose-printing-factory.html", "knowledge/en-how-to-choose-printing-factory.html"),
    ("knowledge/curtain-digital-printing.html", "knowledge/en-curtain-digital-printing.html"),
    ("knowledge/wallcovering-digital-printing.html", "knowledge/en-wallcovering-digital-printing.html"),
    ("knowledge/home-textile-digital-printing.html", "knowledge/en-home-textile-digital-printing.html"),
    ("knowledge/disperse-dye-printing.html", "knowledge/en-disperse-dye-printing.html"),
    ("knowledge/small-batch-custom-printing.html", "knowledge/en-small-batch-custom-printing.html"),
    ("knowledge/shaoxing-keqiao-printing-factory.html", "knowledge/en-shaoxing-keqiao-printing-factory.html"),
]

# ── 页面属性 override：changefreq / priority ──────────────
PAGE_META = {
    "index.html": ("monthly", 1.0),
    "en.html": ("monthly", 0.9),
    "about.html": ("monthly", 0.8),
    "en-about.html": ("monthly", 0.7),
    "applications.html": ("monthly", 0.8),
    "en-applications.html": ("monthly", 0.7),
    "news.html": ("daily", 0.9),
    "en-news.html": ("daily", 0.8),
    "products/curtain.html": ("monthly", 0.8),
    "products/wallcovering.html": ("monthly", 0.8),
    "products/home-textile.html": ("monthly", 0.8),
    "products/en-curtain.html": ("monthly", 0.7),
    "products/en-wallcovering.html": ("monthly", 0.7),
    "products/en-home-textile.html": ("monthly", 0.7),
    # 知识库 GEO 白皮书栏目
    "knowledge/index.html": ("monthly", 0.7),
    "knowledge/index-en.html": ("monthly", 0.6),
    "knowledge/wide-format-digital-printing.html": ("monthly", 0.6),
    "knowledge/en-wide-format-digital-printing.html": ("monthly", 0.5),
    "knowledge/320cm-wide-format-printing.html": ("monthly", 0.6),
    "knowledge/en-320cm-wide-format-printing.html": ("monthly", 0.5),
    "knowledge/digital-vs-traditional-printing.html": ("monthly", 0.6),
    "knowledge/en-digital-vs-traditional-printing.html": ("monthly", 0.5),
    "knowledge/how-to-choose-printing-factory.html": ("monthly", 0.6),
    "knowledge/en-how-to-choose-printing-factory.html": ("monthly", 0.5),
    "knowledge/curtain-digital-printing.html": ("monthly", 0.6),
    "knowledge/en-curtain-digital-printing.html": ("monthly", 0.5),
    "knowledge/wallcovering-digital-printing.html": ("monthly", 0.6),
    "knowledge/en-wallcovering-digital-printing.html": ("monthly", 0.5),
    "knowledge/home-textile-digital-printing.html": ("monthly", 0.6),
    "knowledge/en-home-textile-digital-printing.html": ("monthly", 0.5),
    "knowledge/disperse-dye-printing.html": ("monthly", 0.6),
    "knowledge/en-disperse-dye-printing.html": ("monthly", 0.5),
    "knowledge/small-batch-custom-printing.html": ("monthly", 0.6),
    "knowledge/en-small-batch-custom-printing.html": ("monthly", 0.5),
    "knowledge/shaoxing-keqiao-printing-factory.html": ("monthly", 0.6),
    "knowledge/en-shaoxing-keqiao-printing-factory.html": ("monthly", 0.5),
}


def get_git_dates() -> dict:
    """返回 {相对路径: 最近提交日期 YYYY-MM-DD}，一条 git 命令搞定。"""
    dates = {}
    try:
        out = subprocess.check_output(
            ["git", "-C", str(ROOT), "log", "--name-only",
             "--format=__C__%cd", "--date=short"],
            stderr=subprocess.DEVNULL, text=True)
    except Exception:
        return dates
    cur = None
    for line in out.splitlines():
        if line.startswith("__C__"):
            cur = line[5:].strip()
        elif line.strip():
            f = line.strip()
            if f not in dates:        # log 倒序，首次出现即最新
                dates[f] = cur
    return dates


def loc_for(relpath: str) -> str:
    if relpath == "index.html":
        return SITE + "/"
    return SITE + "/" + relpath


_ART_RE = re.compile(r"articles/(\d{4}-\d{2}-\d{2})-\d{2}\.html$")


def article_date(relpath: str) -> str | None:
    """从文件名 articles/YYYY-MM-DD-NN.html 提取发布日期。"""
    m = _ART_RE.search(relpath)
    return m.group(1) if m else None


def build_alternates(relpath: str):
    """返回该页的 hreflang 配对 [(lang, url), ...]（含 x-default，统一指向中文页）。"""
    pair = next((p for p in PAIRS if relpath in p), None)
    if not pair:
        return []
    zh, en = pair                      # 中文页在前
    return [
        ("zh", loc_for(zh)),
        ("en", loc_for(en)),
        ("x-default", loc_for(zh)),
    ]


def main():
    git_dates = get_git_dates()
    today = date.today().isoformat()

    pages = []
    for p in sorted(ROOT.rglob("*.html")):
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith("articles/"):        # 文章全部收录
            pages.append(rel)
            continue
        name = p.name
        if rel in EXCLUDE_NAMES or name in EXCLUDE_NAMES:
            continue
        if any(name.startswith(pre) for pre in EXCLUDE_PREFIX):
            continue
        pages.append(rel)

    # 去重保序
    seen, uniq = set(), []
    for r in pages:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    pages = uniq

    urls_xml = []
    for rel in pages:
        loc = loc_for(rel)
        if rel.startswith("articles/"):
            lm = article_date(rel) or git_dates.get(rel) or today
            cf, pr = "yearly", 0.6
        else:
            lm = git_dates.get(rel) or today
            cf, pr = PAGE_META.get(rel, ("monthly", 0.5))
        alts = build_alternates(rel)
        alt_xml = "".join(
            f'    <xhtml:link rel="alternate" hreflang="{lang}" '
            f'href="{su.escape(url)}"/>\n'
            for lang, url in alts
        )
        urls_xml.append(
            f'  <url>\n'
            f'    <loc>{su.escape(loc)}</loc>\n'
            + alt_xml +
            f'    <lastmod>{lm}</lastmod>\n'
            f'    <changefreq>{cf}</changefreq>\n'
            f'    <priority>{pr}</priority>\n'
            f'  </url>'
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n\n'
        + "\n".join(urls_xml) + "\n"
        '</urlset>\n'
    )

    SITEMAP.write_text(xml, encoding="utf-8")
    core = [r for r in pages if not r.startswith("articles/")]
    art = [r for r in pages if r.startswith("articles/")]
    print(f"OK: sitemap.xml 生成完成，共 {len(urls_xml)} 条 URL"
          f"（核心/英文页 {len(core)} 篇 + 文章 {len(art)} 篇）")


if __name__ == "__main__":
    main()
