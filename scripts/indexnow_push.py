#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
indexnow_push.py — IndexNow 批量推送（Bing / Yandex / Naver / Seznam 共享协议）

为什么用它：
  - 不需要登录任何站长后台，不需要 OAuth，不需要账号
  - 一次 POST 最多 10000 条 URL，Bing 通常几分钟内开始抓
  - 是绕过「Google 在国内打不开、Bing 后台登录麻烦」的最实用通道

前提（已内置于仓库）：
  根目录存在 <KEY>.txt，内容必须等于 KEY 本身，且可通过
  https://bu6789.com/<KEY>.txt 访问到（否则返回 403）。

用法：
  python scripts/indexnow_push.py              # 推 sitemap 全部 URL
  python scripts/indexnow_push.py --today      # 只推今天的文章
  python scripts/indexnow_push.py --dry-run    # 只看不推
"""
import re
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

SITE = "https://bu6789.com"
HOST = "bu6789.com"
KEY = "98495fd3a172df1ba8e53313c1197dba"
KEY_LOCATION = f"{SITE}/{KEY}.txt"

ROOT = Path(__file__).parent.parent
SITEMAP_PATH = ROOT / "sitemap.xml"
ARTICLES_DIR = ROOT / "articles"

ENDPOINTS = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
]


def urls_from_sitemap() -> list:
    if not SITEMAP_PATH.exists():
        return []
    content = SITEMAP_PATH.read_text(encoding="utf-8")
    return [u.strip() for u in re.findall(r"<loc>(.*?)</loc>", content) if u.strip().startswith("http")]


def urls_today() -> list:
    today = datetime.now().strftime("%Y-%m-%d")
    if not ARTICLES_DIR.exists():
        return []
    return [f"{SITE}/articles/{f.name}" for f in sorted(ARTICLES_DIR.glob(f"{today}*.html"), reverse=True)]


def check_key_live() -> bool:
    try:
        with urllib.request.urlopen(KEY_LOCATION, timeout=15) as r:
            return r.read().decode().strip() == KEY
    except Exception as e:
        print(f"  ⚠️ key 文件不可访问: {e}")
        return False


def submit(urls: list) -> None:
    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }
    data = json.dumps(payload).encode("utf-8")
    for ep in ENDPOINTS:
        req = urllib.request.Request(
            ep,
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                # 200/202 均表示已受理
                print(f"  ✅ {ep} -> HTTP {resp.status}（已受理 {len(urls)} 条）")
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode()[:200]
            except Exception:
                pass
            print(f"  ⚠️ {ep} -> HTTP {e.code} {body}")
        except Exception as e:
            print(f"  ⚠️ {ep} -> {e}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", action="store_true", help="只推今天的文章")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("=" * 60)
    print("IndexNow 推送（Bing / Yandex / Naver）")
    print("=" * 60)

    urls = urls_today() if args.today else urls_from_sitemap()
    if not urls:
        print("  无 URL 可推")
        return

    print(f"\n[1/2] 待推 URL：{len(urls)} 条")
    print(f"      key 文件：{KEY_LOCATION}")

    if args.dry_run:
        print("  (dry-run，不实际提交)")
        return

    if not check_key_live():
        print("  ❌ key 文件未上线，跳过推送。请先把 key 文件提交并部署到站点根目录。")
        sys.exit(0)

    print("  ✅ key 文件校验通过")
    print("\n[2/2] 提交中...")
    # IndexNow 单次上限 10000 条
    for i in range(0, len(urls), 10000):
        submit(urls[i:i + 10000])


if __name__ == "__main__":
    main()
