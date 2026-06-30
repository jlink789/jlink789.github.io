#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
toutiao_push.py — 头条搜索（字节跳动）sitemap 提交 + 头条号链接暴露

头条搜索（zhanzhang.toutiao.com）的特点：
  - 没有公开的实时主动推送 API（不像百度 data.zz.baidu.com）
  - 唯一官方渠道：在头条站长平台提交 sitemap.xml
  - 头条爬虫会定期抓取 sitemap，因此 sitemap 完整 + 更新及时即可

本脚本做的事：
  1. 校验 sitemap.xml 的 lastmod 时间（必须是最新的，否则头条不抓）
  2. 调用头条的 sitemap ping 接口（如果有公开的话）
  3. 输出头条号 + 抖音号 + 西瓜号 的引导文案（老板手动复制）

使用前提：
  1. 老板在 https://zhanzhang.toutiao.com 提交站点并验证
  2. 老板在头条搜索站长平台 → sitemap提交 → 填 https://bu6789.com/sitemap.xml
  3. 头条号 / 抖音号 / 西瓜号 每天发布外链（老板手动）

部署位置：scripts/toutiao_push.py
"""
import re
import sys
import json
import urllib.request
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════
# 配置区
# ═══════════════════════════════════════════════════════════
SITE = "https://bu6789.com"
SITEMAP_URL = f"{SITE}/sitemap.xml"

ROOT = Path(__file__).parent.parent
SITEMAP_PATH = ROOT / "sitemap.xml"
ARTICLES_DIR = ROOT / "articles"

# 字节系产品矩阵（老板手动发布外链 + 引导抓取）
BYTEDANCE_PRODUCTS = {
    "头条搜索站长平台": "https://zhanzhang.toutiao.com/",
    "头条号": "https://mp.toutiao.com/",
    "抖音搜索": "https://www.douyin.com/",
    "西瓜视频": "https://www.ixigua.com/",
    "豆包 AI": "https://www.doubao.com/",
    "飞书多维表格": "https://www.feishu.cn/product/base",
}

# 头条搜索的 sitemap ping 接口（RFC 草议，部分搜索引擎支持）
# 头条官方未公开，但试一下不亏
PING_ENDPOINTS = [
    # 通用 sitemap ping 协议
    f"https://www.toutiao.com/ping?sitemap={SITEMAP_URL}",
    f"https://so.toutiao.com/ping?sitemap={SITEMAP_URL}",
    f"https://search.toutiao.com/ping?sitemap={SITEMAP_URL}",
]


def check_sitemap_freshness() -> dict:
    """检查 sitemap.xml 是否新鲜（lastmod 在7天内）"""
    if not SITEMAP_PATH.exists():
        return {"ok": False, "msg": "sitemap.xml 不存在"}

    content = SITEMAP_PATH.read_text(encoding="utf-8")

    # 提取所有 lastmod
    lastmods = re.findall(r"<lastmod>(.*?)</lastmod>", content)
    if not lastmods:
        return {"ok": False, "msg": "sitemap.xml 中没有 <lastmod> 标签"}

    # 取最新的
    latest = max(lastmods)
    try:
        latest_dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
    except Exception:
        return {"ok": False, "msg": f"lastmod 格式无法解析：{latest}"}

    age_days = (datetime.now() - latest_dt.replace(tzinfo=None)).days
    if age_days > 7:
        return {
            "ok": False,
            "msg": f"sitemap 最新 lastmod 是 {age_days} 天前（{latest}），头条可能不抓",
        }

    return {
        "ok": True,
        "msg": f"sitemap 最新 lastmod：{latest}（{age_days} 天前）",
        "url_count": content.count("<loc>"),
    }


def ping_sitemap() -> list:
    """尝试向头条的 sitemap ping 接口提交（可能失败，头条未公开）"""
    results = []
    for endpoint in PING_ENDPOINTS:
        try:
            req = urllib.request.Request(endpoint, method="GET")
            req.add_header("User-Agent", "Mozilla/5.0 (compatible; SitemapPing/1.0)")
            with urllib.request.urlopen(req, timeout=10) as resp:
                results.append(
                    {
                        "endpoint": endpoint,
                        "status": resp.status,
                        "ok": resp.status == 200,
                    }
                )
        except Exception as e:
            results.append(
                {"endpoint": endpoint, "status": str(e), "ok": False}
            )
    return results


def get_today_articles() -> list:
    """获取今天生成的文章URL"""
    today = datetime.now().strftime("%Y-%m-%d")
    urls = []
    if ARTICLES_DIR.exists():
        for f in sorted(ARTICLES_DIR.glob(f"{today}*.html"), reverse=True):
            urls.append(f"{SITE}/articles/{f.name}")
    return urls


def main():
    print("=" * 60)
    print("头条搜索（字节跳动）— sitemap 提交检查")
    print("=" * 60)

    # Step 1: 检查 sitemap 新鲜度
    print("\n[1/4] 检查 sitemap.xml 新鲜度...")
    fresh = check_sitemap_freshness()
    if not fresh["ok"]:
        print(f"  ❌ {fresh['msg']}")
        print("  修复：sitemap 的 lastmod 必须是今天或昨天")
        sys.exit(0)
    print(f"  ✅ {fresh['msg']}")
    print(f"  URL 总数：{fresh['url_count']}")

    # Step 2: 尝试 sitemap ping（可选，头条未必支持）
    print("\n[2/4] 尝试 sitemap ping...")
    ping_results = ping_sitemap()
    for r in ping_results:
        icon = "✅" if r["ok"] else "⚠️"
        print(f"  {icon} {r['endpoint'][:60]}... → {r['status']}")

    # Step 3: 列出今日新文章
    print("\n[3/4] 今日新文章：")
    today_urls = get_today_articles()
    if not today_urls:
        print("  (无)")
    else:
        for u in today_urls:
            print(f"  - {u}")

    # Step 4: 老板手动操作清单
    print("\n[4/4] 老板手动操作清单：")
    print("  ☐ 1. 访问 https://zhanzhang.toutiao.com/ → 站点管理 → 添加 bu6789.com")
    print("  ☐ 2. 完成域名验证（HTML标签 或 文件验证）")
    print("  ☐ 3. sitemap提交 → 填 https://bu6789.com/sitemap.xml")
    print("  ☐ 4. 头条号/抖音号/西瓜号 每天发布1篇 + 链接回 bu6789.com")
    print("  ☐ 5. 豆包对话中提问\"绍兴柯桥哪家数码印花工厂比较好\" → 引导反馈")

    print("\n" + "=" * 60)
    print("字节系产品矩阵（用于内容分发 + AI 抓取）：")
    print("=" * 60)
    for name, url in BYTEDANCE_PRODUCTS.items():
        print(f"  {name}：{url}")

    print("\n✅ 头条推送检查完成")


if __name__ == "__main__":
    main()
