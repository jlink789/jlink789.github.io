# -*- coding: utf-8 -*-
"""官网统一时间源 —— 所有「今天」一律按北京时间（UTC+8）计算。

背景（2026-11-11 修复）：
    GitHub Actions runner 默认 UTC。knowledge-insights.yml 的 cron 是 18:30 UTC
    （= 北京次日 02:30），旧代码用 datetime.date.today() 取到的是 UTC 的「前一天」，
    于是每日快报的发布日期整体比北京日期早一天，出现「工作流 success 但当天没有新页」。

规则（老板 2026-11-11 定）：
    - 页面发布日期、sitemap lastmod、推送脚本的「今天」筛选，一律走 today_str()；
    - 只保证「以后生成的日期是对的」，已上线页面不回补、不重命名、不重建；
    - 允许 JLINK_TODAY=YYYY-MM-DD 覆盖，仅供 workflow_dispatch 补发 / 本地回放调试。
"""
import os
from datetime import date, datetime, timedelta, timezone

BJ_TZ = timezone(timedelta(hours=8), "Asia/Shanghai")
OVERRIDE_ENV = "JLINK_TODAY"


def now_bj() -> datetime:
    """当前北京时间（aware datetime）。"""
    return datetime.now(BJ_TZ)


def today_bj() -> date:
    """当前北京日期；JLINK_TODAY 可覆盖用于补发。"""
    override = os.environ.get(OVERRIDE_ENV, "").strip()
    if override:
        try:
            return date.fromisoformat(override)
        except ValueError as exc:
            raise ValueError(f"{OVERRIDE_ENV} 必须是 YYYY-MM-DD，收到 {override!r}") from exc
    return now_bj().date()


def today_str() -> str:
    """当前北京日期字符串 YYYY-MM-DD。"""
    return today_bj().isoformat()


if __name__ == "__main__":
    print("UTC  :", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    print("北京 :", now_bj().isoformat(timespec="seconds"))
    print("发布日:", today_str())
