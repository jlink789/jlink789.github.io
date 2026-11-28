#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
baidu_daily_push.py — 百度每日主动推送（去重 + 核心页优先 + 排除模板文章）

设计原则（老板 2026-11-28 定）：
  1. 每天用满 9 条配额，但绝不重复提交同一 URL（靠 baidu_pushed_history.json 去重）
  2. 优先推核心页（中文 + 英文版），其次 knowledge 专题页
  3. 严禁推送 /articles/ 下 1184 篇模板水文（老板已停更，再推只会稀释站级质量分）
  4. 每次运行把结果写入 reports/baidu-push-log.md，供自动化反馈给老板

用法：
  python scripts/baidu_daily_push.py              # 正常推送（最多 9 条）
  python scripts/baidu_daily_push.py --dry-run    # 只列候选，不真正提交
  python scripts/baidu_daily_push.py --limit 3    # 自定义本次上限

配额说明：百度主动推送接口响应里带 remain，本脚本一次提交 min(9, 候选数) 条，
成功数由接口返回；若当日配额已被其他通道消耗，接口只受理 remain 条，其余留到下次。
"""
import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

SITE = "https://bu6789.com"
BAIDU_TOKEN = "DK5oZIEFtapo56in"
API = f"http://data.zz.baidu.com/urls?site={SITE}&token={BAIDU_TOKEN}"
DAILY_LIMIT = 9

ROOT = Path(__file__).resolve().parent.parent
# 历史与日志放在 .github/ 下：deploy-aliyun.yml 的 rsync 已排除 .github，
# 不会被同步到线上 web 根，也不会被搜索引擎抓到。
HISTORY_PATH = ROOT / ".github" / "baidu-push-state.json"
LOG_PATH = ROOT / ".github" / "baidu-push-log.md"
SITEMAP_URL = f"{SITE}/sitemap.xml"

# 核心页白名单（线上 sitemap 实际存在的 14 个，按重要性排序）
CORE_PAGES = [
    "https://bu6789.com/",
    "https://bu6789.com/about.html",
    "https://bu6789.com/products/curtain.html",
    "https://bu6789.com/products/wallcovering.html",
    "https://bu6789.com/products/home-textile.html",
    "https://bu6789.com/applications.html",
    "https://bu6789.com/news.html",
    "https://bu6789.com/en.html",
    "https://bu6789.com/en-about.html",
    "https://bu6789.com/en-applications.html",
    "https://bu6789.com/en-news.html",
    "https://bu6789.com/products/en-curtain.html",
    "https://bu6789.com/products/en-wallcovering.html",
    "https://bu6789.com/products/en-home-textile.html",
]


def now_cn() -> datetime:
    return datetime.now(timezone(timedelta(hours=8)))


def fetch_sitemap_urls() -> list:
    """实时读取线上 sitemap（不依赖本地仓库），返回全部 URL。"""
    req = urllib.request.Request(SITEMAP_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        xml = resp.read().decode("utf-8", "ignore")
    return [u.strip() for u in re.findall(r"<loc>(.*?)</loc>", xml) if u.strip().startswith("http")]


def load_history() -> dict:
    if not HISTORY_PATH.exists():
        return {"pushed": {}, "last_run": None}
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        data.setdefault("pushed", {})
        return data
    except Exception:
        return {"pushed": {}, "last_run": None}


def save_history(history: dict):
    history["last_run"] = now_cn().isoformat(timespec="seconds")
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def build_candidates(sitemap_urls: list, history: dict) -> tuple:
    """返回 (候选列表, 统计信息)。核心页在前，knowledge 在后，排除 articles/。"""
    pushed = history["pushed"]
    seen = set(sitemap_urls)

    # 1) 核心页：白名单中线上确实存在的
    core = [u for u in CORE_PAGES if u in seen and u not in pushed]

    # 2) knowledge 专题页：按 sitemap 顺序，未推过的
    knowledge = [u for u in sitemap_urls if "/knowledge/" in u and u not in pushed]

    # 3) 严禁 articles/ 及任何其他路径
    candidates = core + knowledge
    stats = {
        "sitemap_total": len(sitemap_urls),
        "articles_excluded": sum(1 for u in sitemap_urls if "/articles/" in u),
        "core_remaining": len(core),
        "knowledge_remaining": len(knowledge),
        "already_pushed": len(pushed),
    }
    return candidates, stats


def push_to_baidu(urls: list) -> dict:
    post_data = "\n".join(urls).encode("utf-8")
    req = urllib.request.Request(
        API, data=post_data,
        headers={"Content-Type": "text/plain"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        return {"error": f"HTTP {e.code}: {e.reason}", "body": body}
    except Exception as e:
        return {"error": str(e)}


def append_log(lines: list):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = now_cn().strftime("%Y-%m-%d %H:%M:%S")
    header = f"\n## {ts}\n" if LOG_PATH.exists() else f"# 百度主动推送日志\n\n## {ts}\n"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(header)
        for line in lines:
            f.write(line + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只列候选，不提交")
    ap.add_argument("--limit", type=int, default=DAILY_LIMIT, help="本次推送上限（默认 9）")
    args = ap.parse_args()

    print("=" * 60)
    print("百度主动推送 · 每日去重版（核心页/knowledge，排除模板文）")
    print("=" * 60)

    try:
        sitemap_urls = fetch_sitemap_urls()
    except Exception as e:
        print(f"[ERROR] 读取 sitemap 失败：{e}")
        append_log([f"- 结果：❌ 读取 sitemap 失败 `{e}`"])
        sys.exit(1)

    history = load_history()
    candidates, stats = build_candidates(sitemap_urls, history)

    print(f"\n[1/3] sitemap 共 {stats['sitemap_total']} 条"
          f"（articles 模板文 {stats['articles_excluded']} 条已全部排除）")
    print(f"  历史已推送：{stats['already_pushed']} 条")
    print(f"  未推候选：核心页 {stats['core_remaining']} + knowledge {stats['knowledge_remaining']}"
          f" = {len(candidates)} 条")

    if not candidates:
        print("\n[2/3] 候选池已空：核心页与 knowledge 页全部推完，今日无可推 URL。")
        append_log(["- 结果：⚠️ 候选池已空（核心页+knowledge 全部推完），今日未提交"])
        sys.exit(0)

    batch = candidates[: args.limit]
    n_core = sum(1 for u in batch if u in CORE_PAGES)
    n_kn = len(batch) - n_core
    print(f"\n[2/3] 本次拟推 {len(batch)} 条（核心页 {n_core} + knowledge {n_kn}）")

    if args.dry_run:
        print("\n[dry-run] 候选 URL：")
        for u in batch:
            print("  -", u)
        return

    print("\n[3/3] 提交百度推送接口…")
    result = push_to_baidu(batch)

    if "error" in result:
        print(f"  ❌ 推送失败：{result['error']}")
        if "body" in result:
            print(f"     {result['body']}")
        append_log([
            f"- 本次拟推：{len(batch)} 条（核心 {n_core} + knowledge {n_kn}）",
            f"- 结果：❌ 接口失败 `{result['error']}`" + (f" / {result['body']}" if "body" in result else ""),
        ])
        sys.exit(1)

    success = result.get("success", 0)
    remain = result.get("remain", 0)
    not_same_site = result.get("not_same_site", [])
    not_valid = result.get("not_valid", [])

    # 只有接口确认成功的 URL 才写入历史，失败的留到下次重试
    pushed_today = batch[:success]
    ts = now_cn().strftime("%Y-%m-%d")
    for u in pushed_today:
        history["pushed"][u] = ts
    save_history(history)

    log_lines = [
        f"- 本次拟推：{len(batch)} 条（核心页 {n_core} + knowledge {n_kn}）",
        f"- 接口返回：成功 **{success}** 条 / 剩余配额 {remain} 条",
    ]
    if pushed_today:
        log_lines.append("- 成功入库（已去重，不再重复提交）：")
        for u in pushed_today:
            log_lines.append(f"  - `{u}`")
    if not_same_site:
        log_lines.append(f"- 非本站 URL：{len(not_same_site)} 条")
    if not_valid:
        log_lines.append(f"- 无效 URL：{len(not_valid)} 条 → {not_valid[:5]}")
    append_log(log_lines)

    print(f"\n✅ 推送完成：成功 {success} 条 / 剩余配额 {remain} 条")
    for u in pushed_today:
        print("   -", u)
    if not_valid:
        print(f"   ⚠️ 无效 URL {len(not_valid)} 条：{not_valid[:3]}")
    print(f"\n📝 已记录到 {HISTORY_PATH.relative_to(ROOT)}，累计去重 {len(history['pushed'])} 条")
    print(f"📝 日志：{LOG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
