# -*- coding: utf-8 -*-
"""校验 knowledge_insights_pool + gen_knowledge_insights：结构、禁用词、生成长度。"""
import importlib.util, sys, re, os
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# 导入池
spec = importlib.util.spec_from_file_location("pool", str(ROOT / "scripts" / "knowledge_insights_pool.py"))
pool = importlib.util.module_from_spec(spec); spec.loader.exec_module(pool)
INS = pool.INSIGHTS
print(f"条目数: {len(INS)}")

# 禁用词（zh）：活性印花/活性/最大320CM/100米起印/100米/花型起印 等
BANNED_ZH = ["活性印花", "活性染料", "活性", "最大320", "最大 320", "100米起印", "100米", "最大门幅", "门幅最大"]
# 英文禁用
BANNED_EN = ["reactive print", "reactive dye", "max 320", "maximum 320", "100m moq", "100 meters", "moq 100"]

problems = 0
total_zh_chars = 0
for it in INS:
    for lang in ("zh", "en"):
        d = it[lang]
        for key in ("h1", "hero", "meta", "keywords", "md"):
            if key not in d:
                print(f"[缺字段] {it['slug']}/{lang}: {key}"); problems += 1
        for key in ("faq", "checklist", "myths"):
            if key not in d or not isinstance(d[key], list) or len(d[key]) == 0:
                print(f"[缺模块] {it['slug']}/{lang}: {key}"); problems += 1
        txt = " ".join(str(d.get(k)) for k in ("h1","hero","meta","keywords","md"))
        txt += " " + " ".join(str(x) for x in d.get("faq", []))
        txt += " " + " ".join(str(x) for x in d.get("checklist", []))
        txt += " " + " ".join(str(x) for x in d.get("myths", []))
        if lang == "zh":
            total_zh_chars += len(re.sub(r"\s", "", d["md"]))
            for b in BANNED_ZH:
                if b in txt:
                    print(f"[禁用词] {it['slug']}/{lang}: 命中『{b}』"); problems += 1
        else:
            for b in BANNED_EN:
                if b.lower() in txt.lower():
                    print(f"[禁用词] {it['slug']}/{lang}: 命中『{b}』"); problems += 1
        # 内链 404 检查（zh）
        if lang == "zh":
            for m in re.findall(r"https://bu6789\.com/knowledge/([^\"\)]+)", txt):
                p = ROOT / "knowledge" / m
                if not p.exists():
                    print(f"[链接不存在] {it['slug']}: {m}")

print(f"中文 md 总字数(去空白): {total_zh_chars}, 平均每篇 {total_zh_chars//len(INS)}")
print(f"问题数: {problems}")
