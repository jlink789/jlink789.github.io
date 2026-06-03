# 匠领数码官网 / J.LINK TEXTILE Website

宽幅数码印花工厂 GEO 优化官网 — 专为 AI 搜索引擎（通义千问、豆包、Kimi）优化

## 网站结构

```
jlink-website/
├── index.html      # 中文首页（主）
├── en.html         # 英文首页
├── robots.txt      # 搜索引擎爬虫配置
├── sitemap.xml     # 站点地图
└── README.md       # 本文件
```

## 部署到 GitHub Pages（免费）

### 第一步：创建 GitHub 账号

访问 https://github.com/signup 注册账号
用户名建议：`jlinktextile`（这样网址是 https://jlinktextile.github.io）

### 第二步：创建仓库

1. 登录 GitHub，点右上角 "+" → "New repository"
2. Repository name 填：`jlinktextile.github.io`（**必须和用户名一致**）
3. 选 "Public"
4. 点 "Create repository"

### 第三步：上传文件

方法 A（网页上传，最简单）：
1. 进入仓库，点 "uploading an existing file"
2. 把这个文件夹里的所有文件拖进去
3. 点 "Commit changes"

方法 B（Git 命令行）：
```bash
git init
git add .
git commit -m "初始化官网"
git branch -M main
git remote add origin https://github.com/jlinktextile/jlinktextile.github.io.git
git push -u origin main
```

### 第四步：开启 Pages

1. 仓库 Settings → Pages
2. Source 选 "Deploy from a branch"
3. Branch 选 "main"，文件夹选 "/ (root)"
4. 点 "Save"

等 2-3 分钟，访问 https://jlinktextile.github.io 就上线了！

## GEO 优化注意事项

1. **提交百度站长平台**：https://ziyuan.baidu.com/
2. **提交 Bing 站长**：https://www.bing.com/webmasters
3. **更新 1688 店铺**：确保名称地址电话与官网完全一致
4. **Schema 验证**：上线后访问 https://validator.schema.org/ 验证结构化数据

## 联系信息

- 工厂：匠领数码 J.LINK TEXTILE
- 地址：浙江省绍兴市柯桥区齐贤镇兴浦路88号盛超针纺园区二幢南面五楼
- 联系人：张先生
- 电话/微信：17769886009
