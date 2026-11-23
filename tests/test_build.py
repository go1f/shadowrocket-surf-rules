import re
import unittest
from ipaddress import ip_address
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from scripts.build import build_public, read_ad_rules


ROOT = Path(__file__).resolve().parents[1]


class BuildTests(unittest.TestCase):
    def test_public_build_embeds_rules_in_one_named_config(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            build_public(ROOT, output)
            self.assertEqual([path.name for path in output.glob("*.conf")], ["go1f-surf.conf"])
            config = (output / "go1f-surf.conf").read_text(encoding="utf-8")
            ads = (output / "ads.list").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(ads), len(set(ads)))
            for rule in ads:
                position = config.index(f"{rule},REJECT\n")
                self.assertLess(config.index("DOMAIN-SUFFIX,chatgpt.com,PROXY"), position)
                self.assertLess(position, config.index("DOMAIN-SUFFIX,cn,DIRECT"))
            self.assertIn("FINAL,PROXY\n", config)
            domain_rules = [line.split(",") for line in config.splitlines() if line.startswith(("DOMAIN,", "DOMAIN-SUFFIX,"))]
            for host in (
                "apps.apple.com", "buy.itunes.apple.com", "audio-ssl.itunes.apple.com", "music.apple.com",
                "testflight.apple.com", "developer.apple.com", "cvws.icloud-content.com", "apzones.com",
                "chat.deepseek.com", "api.deepseek.com", "cdn.deepseek.com", "dl.xunlei.com",
                "xunlei.net", "tracker.sandai.net", "thundercdn.com", "p2cdn.com",
                "puds.ucweb.com", "x.so123.com", "alibaba-cn-pvg-00001.oss-enet.aliyuncs.com",
                "sns-video-v6.xhscdn.com", "mediacloud.xiaohongshu.com", "aks.jdpay.com",
                "gw.alipayobjects.com", "acs.m.goofish.com", "frodo.douban.com", "wanproxy.127.net",
                "acgvideo.com", "lf-imfile-cn.feishucdn.com", "www.douyin.com", "www.1688.com",
                "example.oss-cn-hangzhou.aliyuncs.com", "ap-shanghai.cls.tencentcs.com",
                "example.cos.ap-shanghai.myqcloud.com", "bj.bcebos.com", "httpdns.baidubce.com",
                "demo-frontier.feishu.cn", "a.byteimg.com", "a.bdurl.net", "a.365yg.com",
                "a.ctobsnssdk.com", "a.snssdk.com", "a.pstatp.com", "a.toutiaocloud.com",
                "a.bytedance.com", "a.bytevcloud.com", "ntp1.aliyun.com", "time1.cloud.tencent.com",
                "m.quyundong.com", "api.day.app",
            ):
                with self.subTest(host=host):
                    policy = next((policy for kind, domain, policy in domain_rules
                                   if host == domain or (kind == "DOMAIN-SUFFIX" and host.endswith("." + domain))), "PROXY")
                    self.assertEqual(policy, "DIRECT")
            self.assertNotIn("DOMAIN,alibaba-cn-pvg-00001.oss-enet.aliyuncs.com,DIRECT", config)
            for host in ("time.windows.com", "android.pool.ntp.org"):
                self.assertLess(config.index(f"AND,((DOMAIN,{host}),(PROTOCOL,UDP),(DST-PORT,123)),DIRECT"), config.index("FINAL,PROXY"))
            self.assertLess(config.index("IP-CIDR,17.0.0.0/8,DIRECT,no-resolve"), config.index("FINAL,PROXY"))
            self.assertLess(config.index("IP-CIDR6,2409:8000::/20,DIRECT,no-resolve"), config.index("FINAL,PROXY"))
            for domain in ("mzstatic.com", "baidu.com", "meituan.net", "zhimg.com", "qiyipic.com"):
                self.assertLess(config.index(f"DOMAIN-SUFFIX,{domain},DIRECT"), config.index("FINAL,PROXY"))
            self.assertLess(config.index("DOMAIN,dns-detect.alicdn.com,PROXY"), config.index("DOMAIN-SUFFIX,alicdn.com,DIRECT"))
            for marker in ("RULE-SET,", "[Proxy Group]", "[Proxy]", "{{", "[MITM]", "[Script]"):
                self.assertNotIn(marker, config)
            self.assertEqual(len(list((output / "modules").glob("*.srmodule"))), 6)

    def test_ad_rules_cannot_override_protected_hosts(self):
        template = (ROOT / "config/surf.conf.in").read_text(encoding="utf-8")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ads.list"
            for rule in (
                "DOMAIN,ws.chatgpt.com", "DOMAIN-SUFFIX,cloudflare.com", "DOMAIN,captive.apple.com",
                "DOMAIN,mmsns.qpic.cn", "DOMAIN-SUFFIX,qq.com",
                "DOMAIN,m.quyundong.com", "DOMAIN-SUFFIX,day.app",
            ):
                with self.subTest(rule=rule):
                    path.write_text(rule, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "overlaps a protected host"):
                        read_ad_rules(path, template)

    def test_dns_endpoints_are_encrypted_and_need_no_host_lookup(self):
        template = (ROOT / "config/surf.conf.in").read_text(encoding="utf-8")
        general = template.split("[General]\n", 1)[1].split("[Rule]", 1)[0]
        settings = dict(line.split(" = ", 1) for line in general.splitlines() if " = " in line)
        self.assertEqual(settings["dns-direct-system"], "false")
        self.assertEqual(settings["dns-fallback-system"], "false")
        self.assertEqual(settings["dns-direct-fallback-proxy"], "false")
        primary = settings["dns-server"].split(",")
        fallback = settings["fallback-dns-server"].split(",")
        self.assertEqual(set(primary), {
            "https://223.5.5.5/dns-query", "https://120.53.53.53/dns-query",
        })
        self.assertEqual(set(fallback), {
            "https://1.0.0.1/dns-query", "https://8.8.8.8/dns-query", "tls://223.5.5.5",
        })
        self.assertEqual(settings["tun-excluded-routes"].split(","), ["224.0.0.251/32", "ff02::fb/128"])
        for server in primary + fallback:
            with self.subTest(server=server):
                endpoint = urlsplit(server)
                self.assertIn(endpoint.scheme, {"https", "tls"})
                address = ip_address(endpoint.hostname)
                self.assertIn(f"IP-CIDR,{address}/32,DIRECT,no-resolve\n", template)

    def test_wechat_media_routes_precede_ads_and_proxy_fallback(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            build_public(ROOT, output)
            rules = (output / "go1f-surf.conf").read_text(encoding="utf-8").splitlines()
        for rule in (
            "DOMAIN-SUFFIX,wechat.com,DIRECT", "DOMAIN-SUFFIX,qpic.cn,DIRECT",
            "DOMAIN,up-hl.3g.qq.com,DIRECT", "DOMAIN,wxapp.tc.qq.com,DIRECT",
            "DOMAIN,vweixinf.tc.qq.com,DIRECT", "DOMAIN,finder.video.qq.com,DIRECT",
        ):
            self.assertLess(rules.index(rule), rules.index("DOMAIN,ad.doubleclick.net,REJECT"))
        self.assertLess(rules.index("IP-ASN,132203,DIRECT,no-resolve"), rules.index("FINAL,PROXY"))
        self.assertIn("DOMAIN,gdt.qq.com,REJECT", rules)

    def test_splash_modules_match_ads_but_spare_business_paths(self):
        examples = {
            "bilibili": ("app.bilibili.com/x/v2/splash/list?x=1", "app.bilibili.com/x/v2/feed/index"),
            "weibo": ("api.weibo.cn/2/ad/preload?x=1", "api.weibo.cn/2/statuses/home_timeline"),
            "douban": ("api.douban.com/v2/app_ads/splash", "api.douban.com/v2/book/123"),
            "netease-music": ("interface3.music.163.com/eapi/ad/get", "interface3.music.163.com/eapi/song/enhance/player/url"),
            "qq-music": ("y.gtimg.cn/music/common/upload/t_splash_info/001.jpg", "y.gtimg.cn/music/photo/album.jpg"),
            "amap": ("m5.amap.com/ws/shield/dsp/app/startup/init?x=1", "m5.amap.com/ws/mapapi/location"),
        }
        for app, (blocked, allowed) in examples.items():
            with self.subTest(app=app):
                module = (ROOT / f"modules/splash-{app}.srmodule").read_text(encoding="utf-8")
                pattern, replacement, action = next(line for line in module.splitlines() if line.startswith("^")).split()
                self.assertEqual(replacement, "-")
                self.assertIn(action, {"reject-dict", "reject-img"})
                self.assertIsNotNone(re.match(pattern, "https://" + blocked))
                self.assertIsNone(re.match(pattern, "https://" + allowed))
                self.assertIsNone(re.match(pattern, "https://example.com/" + blocked))
                hosts = module.split("hostname = %APPEND% ", 1)[1].strip().split(",")
                self.assertIn(blocked.split("/", 1)[0], hosts)
                self.assertNotIn("[Script]", module)

    def test_douban_module_covers_ad_paths_without_rewriting_normal_content(self):
        module = (ROOT / "modules/splash-douban.srmodule").read_text(encoding="utf-8")
        rewrites = [re.compile(line.split()[0]) for line in module.splitlines() if line.startswith("^")]
        hosts = module.split("hostname = %APPEND% ", 1)[1].strip().split(",")
        for url in (
            "https://api.douban.com/v3/app_ads?version=3",
            "http://api.douban.com/v2/app_ads/splash",
            "https://api.douban.com/beta/common_ads?place=1",
            "https://frodo.douban.com/api/v2/movie/banner?version=2",
            "https://img9.doubanio.com/view/dale-online/dale_ad/asset.jpg",
            f"https://storage.360buyimg.com/material-video/video/{'a' * 32}.mp4?token=fixture",
        ):
            with self.subTest(url=url):
                self.assertTrue(any(pattern.match(url) for pattern in rewrites))
                self.assertIn(urlsplit(url).hostname, hosts)
        for url in (
            "https://api.douban.com/v2/book/123",
            "https://api.douban.com/v2/app_ads_settings",
            "https://frodo.douban.com/api/v2/movie/123",
            "https://img9.doubanio.com/view/photo/s/public/asset.jpg",
            "https://storage.360buyimg.com/other/clip.mp4",
        ):
            with self.subTest(url=url):
                self.assertFalse(any(pattern.match(url) for pattern in rewrites))
        quic_rules = [line for line in module.splitlines() if "(PROTOCOL,QUIC)" in line]
        self.assertEqual(quic_rules, [
            f"AND,((DOMAIN,{host}),(PROTOCOL,QUIC)),REJECT-NO-DROP"
            for host in ("api.douban.com", "frodo.douban.com")
        ])


if __name__ == "__main__":
    unittest.main()
