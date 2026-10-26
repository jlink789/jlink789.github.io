# 官网 nginx：www → apex 站点级 301

> 本文件是**给老板在阿里云 ECS 上手动执行**的操作说明。WorkBuddy 不直接 SSH 改 ECS。
> 目标：把 `https://www.bu6789.com/...` 永久 301 跳转到 `https://bu6789.com/...`，统一首选域（利于 SEO 权重集中、GEO 实体一致）。

---

## ⚠️ 执行前必读：百度验证冲突

当前百度站长验证文件 `baidu_verify_codeva-r5qDCnEKAn.html` 放在**两个域名都能访问**（根域 + www 都 HTTP 200）。

一旦 `www` 301 跳转到 `apex`，访问 `https://www.bu6789.com/baidu_verify_*.html` 会返回 **301 重定向**而不是文件内容。
百度「文件验证」**通常不跟随 301**，会判定验证失败。

**执行 301 前，二选一：**
1. **（推荐）把百度验证方式改成 DNS 验证**：百度站长平台 → 站点属性 → 验证方式 → 选「DNS 验证」→ 在阿里云 DNS 给 `bu6789.com` 加一条 TXT 记录 → 点完成验证。DNS 验证不受 301 影响，最稳。
2. **或确认百度已在 `www.bu6789.com` 下验证通过**（验证通过后改域名指向不影响已收录站点），再执行 301。

> 同样要检查：抖音/头条站长验证文件 `ByteDanceVerify.html` 若也是用 www 文件验证，同理先改 DNS 验证。

---

## 步骤 1：SSH 上 ECS，核对当前配置

```bash
ssh root@47.98.252.216
cat /etc/nginx/conf.d/bu6789.com.conf
```

重点看三处：
- 443 那个 `server` 的 `server_name` 现在是 `bu6789.com www.bu6789.com` 还是分开的？
- 它的 `ssl_certificate` / `ssl_certificate_key` 路径（续期后是 `/etc/letsencrypt/live/bu6789.com/...`）。
- 80 那个 `server` 的跳转写法是 `return 301 https://$host...` 还是 `https://bu6789.com...`？

---

## 步骤 2：加 301（推荐：独立 server 块）

编辑 `/etc/nginx/conf.d/bu6789.com.conf`：

**(a) 把原 443 server 的 `server_name` 去掉 www**
```nginx
# 原：server_name bu6789.com www.bu6789.com;
server_name bu6789.com;
```

**(b) 在原 443 server 之前新增专门吃 www 的 301 块**（ssl 段照抄原 443 server 的写法）：
```nginx
server {
    listen 443 ssl http2;
    server_name www.bu6789.com;

    # ↓↓↓ 照抄原 443 server 的 ssl 配置 ↓↓↓
    ssl_certificate     /etc/letsencrypt/live/bu6789.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bu6789.com/privkey.pem;
    include             /etc/nginx/conf.d/options-ssl-nginx.conf;   # 若 certbot 生成了此文件
    ssl_dhparam         /etc/letsencrypt/ssl-dhparams.pem;          # 若 certbot 生成了此文件
    # ↑↑↑ 照抄原 443 server 的 ssl 配置 ↑↑↑

    # 永久 301 到 apex（保留完整路径与查询串）
    return 301 https://bu6789.com$request_uri;
}
```

**(c) 顺手统一 80 跳转**（若 80 server 用了 `$host`，改成固定 apex，避免 www 的 80 跳到 www 的 443 再跳）：
```nginx
server {
    listen 80;
    server_name bu6789.com www.bu6789.com;
    return 301 https://bu6789.com$request_uri;
}
```

> 备选（不想动原配置）：在原 443 server 的 `location /` 前加
> `if ($host ~* ^www\.) { return 301 https://bu6789.com$request_uri; }`
> ——能用，但 NGINX 官方不推荐 `if`，仅作应急。

---

## 步骤 3：测试并重载（不要 restart，避免中断）

```bash
nginx -t                 # 语法检查，必须 Syntax OK
nginx -s reload          # 平滑重载，不中断现有连接
```

---

## 步骤 4：验证

本地（或任意能联网的机器）：
```bash
curl -sI https://www.bu6789.com/      | grep -i "^location\|HTTP/"
# 期望：HTTP/2 301  +  location: https://bu6789.com/
curl -sI https://www.bu6789.com/products/curtain.html | grep -i "^location\|HTTP/"
# 期望：301 → https://bu6789.com/products/curtain.html
curl -sI https://bu6789.com/         | grep -i "HTTP/"
# 期望：200
```

---

## 续期注意（重要）

证书续期走 certbot DNS-01（阿里云 AK/SK），命令必须**始终包含 `-d www.bu6789.com`**：
```bash
certbot certonly --authenticator dns-aliyun --dns-aliyun-credentials /root/aliyun.ini \
  -d bu6789.com -d www.bu6789.com
```
否则续期后证书不含 www，上面 301 块的 SSL 握手会失败（www 访问报证书错误）。当前续期已含 www，勿删。

---

## 回滚

若出问题，删掉 (b) 的 www 301 块、把 (a) 的 `server_name` 改回 `bu6789.com www.bu6789.com`，再 `nginx -t && nginx -s reload` 即可。完全可逆。
