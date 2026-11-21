import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.build import build_public, read_ad_rules, render_config, select_nodes


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "example/shadowrocket-surf-rules"
PUBLIC_RULE_URL = f"https://raw.githubusercontent.com/{REPOSITORY}/release/ads.list"


class BuildTests(unittest.TestCase):
    def test_public_build_uses_remote_rules_and_embeds_offline_copy(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            build_public(ROOT, output, REPOSITORY)
            online = (output / "surf.conf").read_text(encoding="utf-8")
            offline = (output / "surf-offline.conf").read_text(encoding="utf-8")
            ads = (output / "ads.list").read_text(encoding="utf-8").splitlines()
            self.assertLess(online.index("DOMAIN-SUFFIX,chatgpt.com,ChatGPT"), online.index(PUBLIC_RULE_URL))
            self.assertLess(online.index(PUBLIC_RULE_URL), online.index("DOMAIN-SUFFIX,cn,DIRECT"))
            self.assertEqual(len(ads), len(set(ads)))
            self.assertTrue(all(f"{rule},REJECT" in offline for rule in ads))
            self.assertNotIn("RULE-SET,", offline)
            for config in (online, offline):
                self.assertIn("ChatGPT = select,REJECT\n", config)
                self.assertIn("常规代理 = select,REJECT\n", config)
                self.assertNotIn("{{", config)
                self.assertNotIn("[MITM]", config)
                self.assertNotIn("[Script]", config)
                self.assertIn("dns-server = https://dns.alidns.com/dns-query\n", config)
                self.assertIn("fallback-dns-server = https://doh.pub/dns-query,", config)
                self.assertIn("dns-direct-system = false\n", config)
                self.assertIn("dns-fallback-system = false\n", config)
            self.assertEqual(len(list((output / "modules").glob("*.srmodule"))), 6)

    def test_ad_rules_cannot_override_protected_hosts(self):
        template = (ROOT / "config/surf.conf.in").read_text(encoding="utf-8")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ads.list"
            for rule in ("DOMAIN,ws.chatgpt.com", "DOMAIN-SUFFIX,cloudflare.com", "DOMAIN,doh.pub"):
                with self.subTest(rule=rule):
                    path.write_text(rule, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "overlaps a protected host"):
                        read_ad_rules(path, template)

    def test_private_filters_both_policies_and_never_adds_public_fallback(self):
        profile = {
            "exclude_labels": ["Trial"],
            "verified_nodes": [
                {"name": "JP 01", "exit_region": "JP"},
                {"name": "SG trial preview", "exit_region": "SG"},
                {"name": "HK 01", "exit_region": "HK"},
                {"name": "🇭🇰 JP 02", "exit_region": "JP"},
                {"name": "US unknown", "exit_region": "UNKNOWN"},
            ],
        }
        self.assertEqual(select_nodes(profile), ["JP 01"])
        template = (ROOT / "config/surf.conf.in").read_text(encoding="utf-8")
        config = render_config(template, ["DOMAIN,ads.example.com"], nodes=select_nodes(profile))
        self.assertIn("ChatGPT = select,REJECT,JP 01\n", config)
        self.assertIn("常规代理 = select,REJECT,JP 01\n", config)
        self.assertNotIn("FINAL,PROXY", config)

    def test_private_name_cannot_inject_a_policy_or_url(self):
        for name in ("DIRECT", "PROXY", "REJECT", "JP,PROXY", "https://example.com/token", "JP\nFINAL,DIRECT"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    select_nodes({"exclude_labels": [], "verified_nodes": [{"name": name, "exit_region": "JP"}]})

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
