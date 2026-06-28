/**
 * seo-push.js — 匠领数码 国内搜索引擎自动推送
 * 包含：百度自动推送 + 360自动推送
 * 部署：所有页面 </body> 前引入
 * 更新日期：2026-06-28
 */

// ═══════════════════════════════════════════════════════════
// 1. 百度搜索资源平台 — 自动推送
// 访客浏览页面时自动向百度提交URL
// 验证码已配：codeva-LRmriqvnl3
// ═══════════════════════════════════════════════════════════
(function () {
    var bp = document.createElement('script');
    var curProtocol = window.location.protocol.split(':')[0];
    if (curProtocol === 'https') {
        bp.src = 'https://zz.bdstatic.com/linksubmit/push.js';
    } else {
        bp.src = 'http://push.zhanzhang.baidu.com/push.js';
    }
    var s = document.getElementsByTagName("script")[0];
    s.parentNode.insertBefore(bp, s);
})();

// ═══════════════════════════════════════════════════════════
// 2. 360搜索 — 自动收录
// 需要在360站长平台获取专属token后替换下方src中的hash
// 当前为占位，获取token后替换
// ═══════════════════════════════════════════════════════════
(function () {
    var src = (document.location.protocol == "https:") 
        ? "https://jspassport.ssl.qhimg.com/11.0.1.js?d182b3f28525f2db83acfaaf6e696dba" 
        : "http://js.passport.qihucdn.com/11.0.1.js?d182b3f28525f2db83acfaaf6e696dba";
    document.write('<script src="' + src + '" id="sozz"><\/script>');
})();

// ═══════════════════════════════════════════════════════════
// 3. 搜狗搜索 — 页面推送（通过meta标签验证，无需JS推送）
// 搜狗目前无客户端推送API，依赖主动提交sitemap
// ═══════════════════════════════════════════════════════════
