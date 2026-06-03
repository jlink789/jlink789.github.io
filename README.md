# 匠领数码官网 / J.LINK TEXTILE Website

宽幅数码印花工厂 GEO 优化官网 — 专为 AI 搜索引擎（通义千问、豆包、Kimi）优化

**独立域名**：https://bu6789.com

## 更新文件到 GitHub

线上文件需要更新 URL 后重新上传：

1. 把更新后的 6 个文件（index.html、en.html、robots.txt、sitemap.xml、CNAME、README.md）拖入 GitHub 仓库
2. 点 "Commit changes"
3. 等 1-2 分钟生效

## 网站结构

```
jlink-website/
├── index.html      # 中文首页（主）
├── en.html         # 英文首页
├── robots.txt      # 搜索引擎爬虫配置
├── sitemap.xml     # 站点地图
├── CNAME           # 绑定自定义域名 bu6789.com
└── README.md       # 本文件
```

## 绑定自定义域名到 GitHub Pages

### 第一步：上传 CNAME 文件

`CNAME` 文件已创建，内容是 `bu6789.com`。和网站文件一起上传到仓库。

### 第二步：域名 DNS 配置

登录 bu6789.com 的域名管理后台，添加 DNS 记录：

| 类型 | 主机记录 | 记录值 |
|------|----------|--------|
| CNAME | @ | jlink789.github.io |

等 DNS 生效后（1-10 分钟），仓库 Settings → Pages → 开启 "Enforce HTTPS"。

## 联系信息

- 工厂：匠领数码 J.LINK TEXTILE
- 地址：浙江省绍兴市柯桥区齐贤镇兴浦路88号盛超针纺园区二幢南面五楼
- 联系人：张先生
- 电话/微信：17769886009
