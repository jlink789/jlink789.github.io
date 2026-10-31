import sys

p = "I:/jlink789.github.io/index.html"
s = open(p, encoding="utf-8").read()

start = '<section id="about">'
i = s.index(start)
j = s.index("</section>", i) + len("</section>")
old = s[i:j]

new = '''<section id="about">
  <div class="container" style="max-width:1100px">
    <span class="section-label">关于匠领</span>
    <h2 class="section-title">匠领数码 · J.LINK TEXTILE</h2>
    <p style="color:var(--muted);margin:0 0 10px;line-height:1.9;font-size:1.03rem">
      匠领数码（J.LINK TEXTILE）坐落于全球最大的纺织品集散地——绍兴柯桥中国轻纺城，是一家专注于超宽幅<strong>数码印花加工</strong>与面料印花代工的源头工厂。依托柯桥完善的纺织产业链集群优势，我们为软装设计师、软装门店及品牌工厂提供从纹样打样到宽幅大货生产的一站式<strong>数码印花加工</strong>解决方案。
    </p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:40px;margin-top:26px;align-items:start">
      <div>
        <h3 style="font-size:1.02rem;color:var(--brand);margin:0 0 6px">核心能力｜全系列宽幅，整幅一次成型</h3>
        <p style="color:var(--muted);margin:0 0 18px;line-height:1.8">
          工厂配置进口高速数码印花生产线，稳定承接 200 / 220 / 240 / 260 / 280 / 320CM 全幅宽订单。320CM 超宽幅可整幅一次印花、花纹连贯无切断，特别适配落地窗帘、宽幅墙布、整版床品等大尺寸软装面料。无论是桌布印花、卷帘印花、柯桥窗帘印花、墙布数码印花，还是<strong>床单印花</strong>、被套等家纺面料印花，均可按需定制。
        </p>
        <h3 style="font-size:1.02rem;color:var(--brand);margin:0 0 6px">工艺体系｜热转印 + 直喷印花，色彩牢度双保障</h3>
        <p style="color:var(--muted);margin:0 0 18px;line-height:1.8">
          我们采用<strong>热转印</strong>及直喷印花工艺，针对涤纶、棉麻、雪尼尔等不同软装面料做定向适配，确保花型色彩还原度高、色牢度达标、水洗不易分层。成熟工艺研发团队持续打磨宽幅对花精度与批次稳定性，让大货与打样“一个色”。
        </p>
        <h3 style="font-size:1.02rem;color:var(--brand);margin:0 0 6px">服务体系｜柔性排产，交期可控</h3>
        <p style="color:var(--muted);margin:0 0 18px;line-height:1.8">
          覆盖「纹样打样 → 面料适配 → 大货生产」全链路：小批量试单快速出样，大货柔性排产不压单，标准化品质管控贯穿每道工序。作为<strong>柯桥数码印花加工厂</strong>，我们更懂 B 端客户的定制节奏——急单可排、翻单同色、交期可承诺。
        </p>
        <h3 style="font-size:1.02rem;color:var(--brand);margin:0 0 6px">品质承诺</h3>
        <ul style="color:var(--muted);margin:0;padding-left:20px;line-height:1.9">
          <li>色彩还原：专业色彩管理，花型还原度行业领先</li>
          <li>色牢度：耐水洗、耐光照，适配中高端软装长期使用</li>
          <li>成品稳定：宽幅对花精准，整卷严丝合缝</li>
        </ul>
      </div>
      <div style="background:var(--bg2);border-radius:16px;padding:30px">
        <h3 style="font-size:1.05rem;margin:0 0 18px;color:var(--brand)">工厂核心指标</h3>
        <table style="width:100%;border-collapse:collapse;text-align:left">
          <tr style="border-bottom:1px solid var(--border)">
            <td style="padding:9px 0;color:var(--muted);font-size:.9rem">加工幅宽</td>
            <td style="padding:9px 0;font-weight:600">200 / 220 / 240 / 260 / 280 / 320 CM</td>
          </tr>
          <tr style="border-bottom:1px solid var(--border)">
            <td style="padding:9px 0;color:var(--muted);font-size:.9rem">印花工艺</td>
            <td style="padding:9px 0;font-weight:600">热转印 / 直喷印花 / 宽幅数码印花</td>
          </tr>
          <tr style="border-bottom:1px solid var(--border)">
            <td style="padding:9px 0;color:var(--muted);font-size:.9rem">最小起印</td>
            <td style="padding:9px 0;font-weight:600">1 米起印 · 免费打样</td>
          </tr>
          <tr style="border-bottom:1px solid var(--border)">
            <td style="padding:9px 0;color:var(--muted);font-size:.9rem">标准交期</td>
            <td style="padding:9px 0;font-weight:600">5-7 工作日</td>
          </tr>
          <tr style="border-bottom:1px solid var(--border)">
            <td style="padding:9px 0;color:var(--muted);font-size:.9rem">色牢度</td>
            <td style="padding:9px 0;font-weight:600">4 级以上</td>
          </tr>
          <tr>
            <td style="padding:9px 0;color:var(--muted);font-size:.9rem">色彩精度</td>
            <td style="padding:9px 0;font-weight:600">1670 万色</td>
          </tr>
        </table>
        <div style="margin-top:18px;border-top:1px solid var(--border);padding-top:16px;color:var(--muted);font-size:.92rem;line-height:1.95">
          🏭 工厂地址：浙江省绍兴市柯桥区齐贤镇兴浦路88号盛超针纺园区二幢南面五楼<br>
          👤 联系人：张先生<br>
          📞 电话 / 微信：17769886009
        </div>
      </div>
    </div>
    <div style="text-align:center;margin-top:30px">
      <a href="about.html" class="btn-primary" style="display:inline-block;text-decoration:none">📖 查看完整企业介绍</a>
    </div>
  </div>
</section>'''

if new.strip() == old.strip():
    print("WARN: 新旧内容相同，未改动")
    sys.exit(0)

s2 = s[:i] + new + s[j:]
open(p, "w", encoding="utf-8").write(s2)
print("OK: #about 区块已替换  旧=%d字 新=%d字" % (len(old), len(new)))
