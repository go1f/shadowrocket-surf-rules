# Shadowrocket Surf Rules

适用于 iOS Shadowrocket 的轻量配置。加密 DNS 使用阿里公共 DNS DoH、阿里 DoT 和腾讯 DNSPod DoH。主配置包含 25 条广告域名规则，另有哔哩哔哩、微博、豆瓣、网易云音乐、QQ 音乐、高德地图开屏增强。

## 导入和选节点

1. 在 Shadowrocket 首页更新自己的服务器订阅。需要筛选地区或名称时，打开该订阅的 `ⓘ → 过滤`，保存后刷新订阅。
2. 在「配置」导入 [远程更新版](https://raw.githubusercontent.com/go1f/shadowrocket-surf-rules/release/surf.conf) 或 [内嵌广告规则版](https://raw.githubusercontent.com/go1f/shadowrocket-surf-rules/release/surf-offline.conf)，选择「使用配置」，并把「全局路由」设为「配置」。内嵌版也可以从本地文件导入。
3. 在首页选择一个筛选后保留的节点。`PROXY` 使用首页当前节点，ChatGPT 和其他代理流量共用它。若要固定使用当前节点，在全局路由设置中关闭「启用回退」。节点地区以实际出口为准。

常用国内服务和局域网直连，其余流量由 `FINAL,PROXY` 处理。加密 DNS 端点都使用 IP 地址，可以直接建立 TLS 连接。配置关闭系统 DNS 回退，覆盖 Shadowrocket 接管的 DNS 请求。代理服务端解析和 App 自带解析取决于各自的环境。

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
- 在 Shadowrocket 更新远程广告规则可获取列表变更。主配置、内嵌版和模块的变更通过重新下载生效。配置文件和节点订阅分别管理。回滚可从同一个历史发布提交恢复整套文件，或使用该提交的内嵌版。
- 本地运行 `python3 scripts/build.py` 生成带内嵌广告规则的 `dist/surf.conf`、`dist/surf-offline.conf`、独立广告表和模块。加 `--repository owner/repo` 可让 `surf.conf` 指向对应仓库的远程广告列表。运行 `python3 -m unittest discover -s tests -v` 进行离线测试。

[概要设计](DESIGN.md)记录了调研和验收范围，本文为当前实现的使用说明。
