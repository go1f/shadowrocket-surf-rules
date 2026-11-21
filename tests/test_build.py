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
            self.assertLess(config.index("DOMAIN,dns-detect.alicdn.com,PROXY"), config.index("DOMAIN-SUFFIX,alicdn.com,DIRECT"))
            for marker in ("RULE-SET,", "[Proxy Group]", "[Proxy]", "{{", "[MITM]", "[Script]"):
                self.assertNotIn(marker, config)
            self.assertEqual(len(list((output / "modules").glob("*.srmodule"))), 6)

    def test_ad_rules_cannot_override_protected_hosts(self):
        template = (ROOT / "config/surf.conf.in").read_text(encoding="utf-8")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ads.list"
            for rule in ("DOMAIN,ws.chatgpt.com", "DOMAIN-SUFFIX,cloudflare.com", "DOMAIN,captive.apple.com"):
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
        servers = settings["dns-server"].split(",") + settings["fallback-dns-server"].split(",")
        self.assertIn("tls://223.5.5.5", servers)
        for server in servers:
            with self.subTest(server=server):
                endpoint = urlsplit(server)
                self.assertIn(endpoint.scheme, {"https", "tls"})
                address = ip_address(endpoint.hostname)
                self.assertIn(f"IP-CIDR,{address}/32,DIRECT,no-resolve\n", template)

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


if __name__ == "__main__":
    unittest.main()
