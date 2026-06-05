import random
from datetime import datetime

KEYWORDS = ["宽幅数码印花","桌布印花","2.8M 印花","3m印花", "墙布印花", "窗帘印花", "家纺印花"]

keyword = random.choice(KEYWORDS)
today = datetime.now().strftime("%Y-%m-%d")

title = f"{today}：{keyword}行业新资讯"
content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
</head>
<body>
    <h1>{title}</h1>
    <p>自动发布于 {today}</p>
    <p>{keyword} 技术持续升级，色彩更清晰、耐水洗、环保无毒。</p>
    <p>欢迎访问官网了解最新产品与服务。</p>
</body>
</html>
"""

with open("article.html", "w", encoding="utf-8") as f:
    f.write(content)
