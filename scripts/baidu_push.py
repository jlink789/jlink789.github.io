#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
baidu_push.py — 百度搜索资源平台主动推送工具
智能推送：优先推送今日新文章URL，额度充足时推送更多。

使用前提：
  1. 在百度搜索资源平台 https://ziyuan.baidu.com 添加站点
  2. 验证通过后获取 API token
  3. 将 token 填入下方 BAIDU_TOKEN
  4. 运行：python baidu_push.py

推送策略：
  - 新站点配额较低（每天约10条），优先推送核心页面
  - 配额充足时推送全部 sitemap URL
  - GH Actions 每天自动调用，推送当天新文章
"""
import re
import os
import sys
import json
import urllib.request
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════
# 配置区
# ═══════════════════════════════════════════════════════════
SITE = "https://bu6789.com"
BAIDU_TOKEN = "DK5oZIEFtapo56in"  # 百度推送token（2026-06-28获取）

ROOT = Path(__file__).parent.parent
SITEMAP_PATH = ROOT / "sitemap.xml"
ARTICLES_DIR = ROOT / "articles"

# 核心页面（配额不足时只推这些）
PRIORITY_URLS = [
    "https://bu6789.com/",
    "https://bu6789.com/news.html",
    "https://bu6789.com/about.html",
    "https://bu6789.com/products/curtain.html",
    "https://bu6789.com/products/wallcovering.html",
    "https://bu6789.com/products/home-textile.html",
    "https://bu6789.com/en.html",
]


def get_today_articles() -> list:
    """获取今天生成的文章URL"""
    today = datetime.now().strftime("%Y-%m-%d")
    urls = []
    if ARTICLES_DIR.exists():
        for f in sorted(ARTICLES_DIR.glob(f"{today}*.html"), reverse=True):
            urls.append(f"https://bu6789.com/articles/{f.name}")
    return urls


def extract_urls_from_sitemap() -> list:
    """从 sitemap.xml 提取所有 URL"""
    if not SITEMAP_PATH.exists():
        return []
    content = SITEMAP_PATH.read_text(encoding="utf-8")
    urls = re.findall(r"<loc>(.*?)</loc>", content)
    return [u.strip() for u in urls if u.strip().startswith("http")]


def push_to_baidu(urls: list) -> dict:
    """调用百度推送API"""
    if not BAIDU_TOKEN:
        return {"error": "BAIDU_TOKEN 未配置"}

    api_url = f"http://data.zz.baidu.com/urls?site={SITE}&token={BAIDU_TOKEN}"
    post_data = "\n".join(urls).encode("utf-8")

    req = urllib.request.Request(
        api_url,
        data=post_data,
        headers={"Content-Type": "text/plain"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        return {"error": f"HTTP {e.code}: {e.reason}", "body": body}
    except Exception as e:
        return {"error": str(e)}


def main():
    print("=" * 60)
    print("百度搜索资源平台 — 主动推送")
    print("=" * 60)

    # Step 1: 先探测剩余配额（推送1个URL看remain）
    print("\n[1/3] 探测今日剩余配额...")
    probe = push_to_baidu([PRIORITY_URLS[0]])
    if "error" in probe:
        print(f"  ❌ {probe['error']}")
        if "body" in probe:
            print(f"     {probe['body']}")
        sys.exit(1)

    remain = probe.get("remain", 0)
    print(f"  剩余配额：{remain} 条")

    # Step 2: 准备推送URL列表
    today_urls = get_today_articles()
    print(f"\n[2/3] 今日新文章：{len(today_urls)} 篇")

    if remain <= 0:
        print("  ⚠️ 今日配额已用完，跳过推送")
        print("  提示：自动推送JS（seo-push.js）仍会在访客浏览时自动提交")
        sys.exit(0)

    # 智能选择URL：优先今日文章 → 核心页面 → sitemap
    push_urls = []
    if today_urls:
        push_urls.extend(today_urls)

    # 如果还有配额，补充核心页面（去掉已推的首页）
    remaining_slots = remain - len(push_urls)
    if remaining_slots > 0:
        for url in PRIORITY_URLS[1:]:  # 跳过首页（已用于探测）
            if url not in push_urls and remaining_slots > 0:
                push_urls.append(url)
                remaining_slots -= 1

    # 如果还有大量配额，推送sitemap中未推过的文章
    if remaining_slots > 5:
        all_urls = extract_urls_from_sitemap()
        for url in all_urls:
            if url not in push_urls and remaining_slots > 0:
                push_urls.append(url)
                remaining_slots -= 1

    print(f"  本次将推送：{len(push_urls)} 条")

    # Step 3: 执行推送
    if not push_urls:
        print("\n[3/3] 无需推送的URL")
        sys.exit(0)

    print(f"\n[3/3] 推送中...")
    result = push_to_baidu(push_urls)

    if "error" in result:
        print(f"  ❌ 推送失败：{result['error']}")
        if "body" in result:
            print(f"     {result['body']}")
        sys.exit(1)

    success = result.get("success", 0)
    remain_after = result.get("remain", 0)
    not_same_site = result.get("not_same_site", [])
    not_valid = result.get("not_valid", [])

    print(f"\n✅ 推送完成！")
    print(f"   成功：{success} 条")
    print(f"   剩余配额：{remain_after} 条")
    if not_same_site:
        print(f"   非本站URL：{len(not_same_site)} 条")
    if not_valid:
        print(f"   无效URL：{len(not_valid)} 条")
        for u in not_valid[:5]:
            print(f"     {u}")


if __name__ == "__main__":
    main()
