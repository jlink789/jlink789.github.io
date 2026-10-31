p = "I:/jlink789.github.io/index.html"
s = open(p, encoding="utf-8").read()

repls = [
    # 旧词 -> 新词（铁律合规，不含"拼"字）
    ("整幅无拼接数码印花", "宽幅整幅数码印花"),
    ("整幅无拼接。", "整幅一次成。"),
    ("整幅无拼接、", "整幅一次成、"),
    ("200-320CM整幅无拼接宽幅数码印花代工", "200-320CM整幅一次成宽幅数码印花代工"),
    ("六大幅宽数码印花，整幅无拼接。", "六大幅宽数码印花，整幅一次成。"),
    ("一幅到底，无拼缝，更美观。", "一幅到底，严丝合缝，更美观。"),
    ("整幅无拼接。", "整幅一次成。"),
    ("适合整幅窗帘（无需拼接）、", "适合整幅窗帘（整幅一次成）、"),
    ("一幅到底无拼接。", "一幅到底整幅连贯。"),
    # hero meta / og 旧工艺词
    ("热转印+活性直喷工艺", "热转印+直喷印花工艺"),
]

changed = 0
for old, new in repls:
    c = s.count(old)
    if c:
        s = s.replace(old, new)
        changed += c
        print(f"  ✓ {old!r} -> {new!r}  ×{c}")
    else:
        print(f"  – 未命中: {old!r}")

open(p, "w", encoding="utf-8").write(s)
print("共替换 %d 处" % changed)
