# Shadowrocket Surf Rules

适用于 iOS Shadowrocket 的轻量配置。内置阿里公共 DNS DoH，以腾讯 DNSPod 和 Cloudflare DoH 备用。主配置包含 25 条精选广告域名规则的订阅入口，另有哔哩哔哩、微博、豆瓣、网易云音乐、QQ 音乐、高德地图开屏增强。 [阿里公共 DNS](https://alidns.com/) · [腾讯 DNSPod](https://cloud.tencent.com/document/product/302/110786) · [Cloudflare DNS](https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/make-api-requests/)

## 导入和选节点

1. 在 Shadowrocket 首页继续使用自己的服务器订阅。在该订阅的 `ⓘ → 过滤` 中可单独设置名称排除规则，然后更新这条订阅。 [订阅筛选语法](https://wiki.repcz.link/shadowrocket/node/#_9)
2. 在「配置」导入 [远程更新版](https://raw.githubusercontent.com/go1f/shadowrocket-surf-rules/release/surf.conf) 或 [内嵌广告规则版](https://raw.githubusercontent.com/go1f/shadowrocket-surf-rules/release/surf-offline.conf)，选择「使用配置」，并把「全局路由」设为「配置」。内嵌版适合初次导入时设备还无法读取 GitHub 的情况，也可以从本地文件导入。
3. 在配置的「代理分组」分别编辑 `ChatGPT` 和 `常规代理`，只加入已核验实际出口的单个服务器。日本、新加坡、美国适合作为首批候选。两组初始只有 `REJECT`，完成配置后手动选中合格服务器。关闭 Shadowrocket 全局路由里的「启用回退」，避免另一个服务器被选作故障回退。节点改名、删除或出口变化后重新核验两个分组。 [OpenAI 支持地区](https://help.openai.com/en/articles/7947663-chatgpt-and-openai-api-supported-countries-and-territories)

公网未知目的地默认走常规代理组。常用国内服务和局域网按配置直连。DoH 设置覆盖由 Shadowrocket 接管的 DNS 请求，代理服务端解析、App 自带解析和隧道关闭时的行为取决于各自环境。真实设备上重点检查冷启动能否建立 DoH、Wi-Fi 与蜂窝切换、代理组空成员时的行为，以及目标 App 的登录、播放和导航。

## 六个 App 的开屏增强

默认配置无需安装证书。广告和业务共用主机的 App 可以按需导入下表中的模块。每个模块可单独开关，只改写列出的广告请求。使用模块需要打开 HTTPS 解密，并在设备上生成、安装及信任 Shadowrocket 自己的 CA。建议逐个启用，彻底退出 App 后做冷启动对照。不同版本可能调整接口，已缓存的广告也可能继续显示。

| App | 主配置 | 可选模块 |
| --- | --- | --- |
| 哔哩哔哩 | 广告接口域名 | [开屏列表和展示接口](https://raw.githubusercontent.com/go1f/shadowrocket-surf-rules/release/modules/splash-bilibili.srmodule) |
| 微博 | 广告 SDK、素材和预载域名 | [微博主 App 广告预载接口](https://raw.githubusercontent.com/go1f/shadowrocket-surf-rules/release/modules/splash-weibo.srmodule) |
| 豆瓣 | 基础通用广告拦截 | [豆瓣开屏接口](https://raw.githubusercontent.com/go1f/shadowrocket-surf-rules/release/modules/splash-douban.srmodule) |
| 网易云音乐 | 广告图片和视频域名 | [广告投放接口](https://raw.githubusercontent.com/go1f/shadowrocket-surf-rules/release/modules/splash-netease-music.srmodule) |
| QQ 音乐 | 音乐广告平台域名 | [开屏图片路径](https://raw.githubusercontent.com/go1f/shadowrocket-surf-rules/release/modules/splash-qq-music.srmodule) |
| 高德地图 | 广告接口域名 | [广告启动请求](https://raw.githubusercontent.com/go1f/shadowrocket-surf-rules/release/modules/splash-amap.srmodule) |

模块依据公开资料中的广告主机和接口独立编写，不引用远程脚本。App 版本覆盖以真机实测为准。 [哔哩哔哩、高德、网易云、微博端点](https://github.com/letswish/Shadowrocket-Module/blob/main/All-in-One-AdBlock.sgmodule) · [微博主 App 端点](https://github.com/xchenliu/shadowrocket-config/blob/master/Shadowrocket.conf) · [豆瓣与 QQ 音乐端点](https://github.com/bai1zi/shadowrocket-surge-loon-qx/blob/main/ADs.sgmodule) · [QQ 音乐域名](https://github.com/vokins/ad/blob/main/ad.lsr)

## 更新、构建和回滚

- GitHub Actions 在 `main` 更新时、每周一北京时间 08:17，以及手动触发时，验证并发布已审核的规则。稳定地址位于 `release` 分支。相同内容跳过发布，验证失败保留上一版。
- 已使用远程更新版时，在 Shadowrocket 刷新远程广告规则即可保留本机已选节点。主配置、内嵌版和模块的更新通过重新下载生效。替换主配置前保存本机选择，更新后检查它们是否保留。回滚可从同一个历史发布提交恢复整套文件，或使用该提交的内嵌版。
- 本地运行 `python3 scripts/build.py` 生成带内嵌广告规则的 `dist/surf.conf`、`dist/surf-offline.conf`、独立广告表和模块。加 `--repository owner/repo` 可让 `surf.conf` 指向对应仓库的远程广告列表。运行 `python3 -m unittest discover -s tests -v` 进行离线测试。
- 可选的个人构建读取被 Git 忽略的 `.private/profile.json`，格式例如 `{"exclude_labels":["Trial"],"verified_nodes":[{"name":"JP 01","exit_region":"JP"}]}`。填写设备上已经核验过的节点备注名和地区代码，运行 `python3 scripts/build.py --personal`，再导入 `.private/surf.conf`。也可加 `--repository owner/repo` 使用远程广告规则。个人构建只引用已有节点名称，节点订阅仍由设备管理。未入组时会拒绝对应代理流量。CI 只构建公开产物。

[概要设计](DESIGN.md)记录了调研和验收范围，本文为当前实现的使用说明。
