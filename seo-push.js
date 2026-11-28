/**
 * seo-push.js — 匠领数码 国内搜索引擎自动推送
 * 包含：百度自动推送 + 360自动推送
 * 部署：所有页面 </body> 前引入
 * 更新日期：2026-11-28
 *
 * 2026-11-28 改动（老板确认）：/articles/ 下的 1184 篇模板水文全部跳过推送。
 * 原因：老板已停更水文，但访客浏览仍会经本脚本向百度/360 提交这些低质页，
 * 持续稀释站级质量分、挤占 9 条/天的主动推送配额。核心页与 knowledge 页照常推送。
 */

// 统一过滤：只要是 /articles/ 页面，百度与 360 两条通道都不推送
var SKIP_PUSH = /\/articles\//.test(window.location.pathname);

// ═══════════════════════════════════════════════════════════
// 1. 百度搜索资源平台 — 自动推送
// 访客浏览页面时自动向百度提交URL
// 验证码已配：codeva-LRmriqvnl3
// ═══════════════════════════════════════════════════════════
(function () {
    if (SKIP_PUSH) return;  // /articles/ 模板文不推百度
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
    if (SKIP_PUSH) return;  // /articles/ 模板文不推 360
    var src = (document.location.protocol == "https:") 
        ? "https://jspassport.ssl.qhimg.com/11.0.1.js?d182b3f28525f2db83acfaaf6e696dba" 
        : "http://js.passport.qihucdn.com/11.0.1.js?d182b3f28525f2db83acfaaf6e696dba";
    document.write('<script src="' + src + '" id="sozz"><\/script>');
})();

// ═══════════════════════════════════════════════════════════
// 3. 搜狗搜索 — 页面推送（通过meta标签验证，无需JS推送）
// 搜狗目前无客户端推送API，依赖主动提交sitemap
// ═══════════════════════════════════════════════════════════
