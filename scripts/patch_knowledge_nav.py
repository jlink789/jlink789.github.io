# -*- coding: utf-8 -*-
"""在核心页/英文版/产品页导航栏加入「知识库」入口（幂等）。

- 中文页 → /knowledge/index.html（标签「知识库」）
- 英文页 → /knowledge/index-en.html（标签「Knowledge」）
插入位置：导航块内、FAQ(#faq) 链接之前，与知识库页面自身顺序一致。
已含知识库链接的页面自动跳过。
"""
import os
import re

REPO = r"I:\jlink789.github.io"

# (相对路径, 目标 URL, 标签)
CN_PAGES = [
    ("index.html", "/knowledge/index.html", "知识库"),
    ("about.html", "/knowledge/index.html", "知识库"),
    ("applications.html", "/knowledge/index.html", "知识库"),
    ("news.html", "/knowledge/index.html", "知识库"),
    ("products-curtain.html", "/knowledge/index.html", "知识库"),
    ("products-wallcovering.html", "/knowledge/index.html", "知识库"),
    ("products-home-textile.html", "/knowledge/index.html", "知识库"),
    ("products/curtain.html", "/knowledge/index.html", "知识库"),
    ("products/wallcovering.html", "/knowledge/index.html", "知识库"),
    ("products/home-textile.html", "/knowledge/index.html", "知识库"),
    ("products/products-curtain.html", "/knowledge/index.html", "知识库"),
    ("products/products-wallcovering.html", "/knowledge/index.html", "知识库"),
    ("products/products-home-textile.html", "/knowledge/index.html", "知识库"),
]
EN_PAGES = [
    ("en.html", "/knowledge/index-en.html", "Knowledge"),
    ("en-about.html", "/knowledge/index-en.html", "Knowledge"),
    ("en-news.html", "/knowledge/index-en.html", "Knowledge"),
    ("en-applications.html", "/knowledge/index-en.html", "Knowledge"),
    ("products/en-curtain.html", "/knowledge/index-en.html", "Knowledge"),
    ("products/en-wallcovering.html", "/knowledge/index-en.html", "Knowledge"),
    ("products/en-home-textile.html", "/knowledge/index-en.html", "Knowledge"),
]

ALL = CN_PAGES + EN_PAGES


def nav_span(html):
    m = re.search(r"<nav[^>]*>", html)
    if not m:
        return None
    start = m.start()
    end = html.find("</nav>", start)
    if end == -1:
        return None
    return start, end + len("</nav>")


def patch(html, url, label):
    if url in html:
        return html, "skip"
    s = nav_span(html)
    if not s:
        return html, "no-nav"
    nav = html[s[0]:s[1]]
    # 在导航块内找 #faq 所在行
    lines = nav.split("\n")
    idx = None
    for i, line in enumerate(lines):
        if "#faq" in line:
            idx = i
            break
    if idx is None:
        # 退路：插在 nav-app / nav-cta / lang-switch 之前
        for i, line in enumerate(lines):
            if "nav-app" in line or "nav-cta" in line or "lang-switch" in line:
                idx = i
                break
    if idx is None:
        return html, "no-anchor"
    indent = lines[idx][:len(lines[idx]) - len(lines[idx].lstrip())]
    new_li = f'{indent}<li><a href="{url}">{label}</a></li>'
    lines.insert(idx, new_li)
    new_nav = "\n".join(lines)
    return html[:s[0]] + new_nav + html[s[1]:], "ok"


def run(rel, url, label):
    full = os.path.join(REPO, rel.replace("/", os.sep))
    if not os.path.exists(full):
        print("  !! 文件不存在:", rel)
        return
    with open(full, "r", encoding="utf-8") as f:
        html = f.read()
    if url in html:
        print("  跳过（已含）:", rel)
        return
    out, status = patch(html, url, label)
    if status != "ok":
        print(f"  !! 未更新({status}):", rel)
        return
    with open(full, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    print("  已更新:", rel)


print("== 中文页 ==")
for rel, url, label in CN_PAGES:
    run(rel, url, label)
print("== 英文页 ==")
for rel, url, label in EN_PAGES:
    run(rel, url, label)
print("完成")
