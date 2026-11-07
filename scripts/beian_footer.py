# -*- coding: utf-8 -*-
"""全站页脚备案链接单一数据源（ICP + 公安备案 + 备案图标）。

老板 2026-11-07 提供：浙公网安备33060302001843号 + 备案图标，要求加在 ICP 备案右边。
所有生成器 / 批量脚本都从这里取，避免各处手写不一致。
"""

# 存量页面里的旧写法（无样式），批量脚本靠它精确匹配
ICP_LINK_LEGACY = (
    '<a href="https://beian.miit.gov.cn" target="_blank" rel="noopener">'
    '浙ICP备20007773号-3</a>'
)

# 现行写法：号码整体不换行，避免手机端从「浙ICP备20007773号-3」中间折断
ICP_LINK = (
    '<a href="https://beian.miit.gov.cn" target="_blank" rel="noopener" '
    'style="white-space:nowrap">浙ICP备20007773号-3</a>'
)

# 公安备案：图标 + 号码，紧跟在 ICP 备案右侧
GONGAN_LINK = (
    '<a href="https://beian.mps.gov.cn/#/query/webSearch?code=33060302001843" '
    'rel="noreferrer" target="_blank" class="beian-gongan" '
    'style="display:inline-flex;align-items:center;gap:3px;vertical-align:-4px;white-space:nowrap">'
    '<img src="/assets/gongan-beian.png" alt="公安备案" width="16" height="18" '
    'style="display:block;width:16px;height:18px" loading="lazy">'
    '浙公网安备33060302001843号</a>'
)

# 首版（图标被全局 img{display:block} 挤成单独一行）→ 用于一次性修复存量页面
GONGAN_LINK_V1 = (
    '<a href="https://beian.mps.gov.cn/#/query/webSearch?code=33060302001843" '
    'rel="noreferrer" target="_blank" style="white-space:nowrap">'
    '<img src="/assets/gongan-beian.png" alt="公安备案" width="16" height="18" '
    'style="width:16px;height:18px;vertical-align:-4px;margin-right:3px" loading="lazy">'
    '浙公网安备33060302001843号</a>'
)

# 两个备案并排（页面中 ICP 链接后面直接追加这段即可）
GONGAN_AFTER_ICP = " · " + GONGAN_LINK

# 整行备案（用于本来没有 ICP 的页脚，例如资讯中心模板）
BEIAN_LINE = "<p>" + ICP_LINK + " · " + GONGAN_LINK + "</p>"

# 首版分隔符用了 &nbsp;，手机上把两个备案粘成不可换行的一整块 → 存量页修复用
SEP_V1 = " &nbsp;·&nbsp; "
SEP_NOW = " · "

GONGAN_TEXT = "浙公网安备33060302001843号"
