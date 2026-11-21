# shadowrocket-surf-rules 概要设计

调研日期为 2026 年 11 月 21 日。目标设备为 iOS 上的 Shadowrocket，具体客户端版本需通过真机确认。配置的当前用法和定时发布机制见 [README](README.md)。

## 方案结论

主配置 `go1f-surf.conf` 内嵌域名级广告规则，在 Shadowrocket 的「配置」路由模式下使用。受客户端接管的公网 DNS 查询采用加密解析，广告优先按域名拦截。代理流量使用首页选中的 `PROXY` 节点，节点地区和名称在设备端的服务器订阅中筛选。哔哩哔哩、微博、豆瓣、网易云音乐、QQ 音乐和高德地图各有一个可选开屏模块。

配置订阅和节点订阅分别更新。个人 GitHub 仓库 `shadowrocket-surf-rules` 仅发布公开配置和规则。设备端的 Shadowrocket 管理节点订阅及订阅过滤条件。

## 社区方案对比

| 项目 | 优点 | 局限 | 本项目取舍 |
| --- | --- | --- | --- |
| [Hackl0us / SS-Rule-Snippet](https://github.com/Hackl0us/SS-Rule-Snippet) | 跨客户端整理了常见分流和规则结构，支持配置导入与快捷指令更新，README 也讨论了广告拦截误伤。 | 项目明确不提供网页广告规则。分流模板无法直接满足优先拦截 App 开屏、严格 DNS 回退和出口地区核验的要求。 | 借鉴精简的分流结构与直连例外。配置自行编写。 |
| [Johnshall / Shadowrocket-ADBlock-Rules-Forever](https://github.com/johnshall/Shadowrocket-ADBlock-Rules-Forever) | 面向 Shadowrocket 自动重建，通过固定链接发布。包括黑名单、白名单、国内外分流、仅去广告和策略组等配置。 | 完整广告配置汇集多个来源，逐条追踪误伤和来源的成本较高。开屏覆盖未见逐 App、逐版本的说明。 | 借鉴定时构建、固定入口和可回滚的发布流程。用小规则集保留可定位的误杀记录。 |
| [ithtelab / sr-adblock](https://github.com/ithtelab/sr-adblock) | 将域名拦截、可选 HTTPS 解密模块和主配置分开，展示了节点订阅与配置订阅独立的办法。 | 聚合域名和解密范围较大。其基础配置允许明文和系统 DNS，节点组按名称匹配。 | 借鉴分层和逐 App 模块，保留更小的默认范围。通过其产物了解配置语法，客户端行为以真机为准。 [示例主配置](https://raw.githubusercontent.com/ithtelab/sr-adblock/release/conf/base.conf) |
| [blackmatrix7 / ios_rule_script](https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/Shadowrocket/OpenAI) | 提供可直接阅读的 Shadowrocket 服务域名列表，适合做覆盖交叉检查。 | 服务域名、脚本和聚合数据的适用条件有差异，仓库另有资源使用声明，列表也会落后于服务变化。 | 以 OpenAI 官方资料为准，社区列表用于核对遗漏。 [上游说明](https://github.com/blackmatrix7/ios_rule_script) |
| [AdGuard DNS Filter](https://github.com/AdguardTeam/AdGuardSDNSFilter) | 包含移动广告过滤来源，已针对 DNS 级阻断做简化。 | 完整列表超出首版预算，语法还包括白名单和修饰符，直接抽域名可能改变语义。 | 作为候选域名线索，经验证后再决定纳入方式。使用上游数据时按实际文件核对授权、来源和署名要求。 |
| [iKuuu 供应商配置](https://ikuuu.org/iKuuu_V1_Config.conf) | IP 形式的阿里 DoT、国内及局域网直连、默认代理兜底。将 DNS 检测域名单独走代理，避免被国内域名规则先匹配。 | 配置明确指定系统 DNS 作为备用。部分宽泛的关键词规则和系统旁路会扩大直连范围。 | 采用 IP 直连的加密端点和默认 `PROXY`，补充共享地址段、本地组播、国内常用服务直连及 DNS 检测域名例外。所有备用端点均使用加密协议。 |

## 客户端设计

### 路由和优先级

用户在 Shadowrocket 选择「全局路由 → 配置」。按以下逻辑顺序组织 `[Rule]`。

| 顺序 | 匹配 | 动作 |
| --- | --- | --- |
| 1 | ChatGPT 和 OpenAI 核心服务域名、DNS 检测域名例外 | 进入内置 `PROXY`，优先于广告和直连规则 |
| 2 | 开屏误杀例外、已确认的局域网目标和微信媒体域名 | 例外显式指定原本应使用的策略，局域网和微信媒体域名直连 |
| 3 | 专用开屏广告域名、已验证的公共广告域名 | `REJECT`，规则构建时写入主配置 |
| 4 | 常用国内服务域名、`.cn`，以及已有目标 IP 时适用的腾讯网络和国内 IP 规则 | `DIRECT` |
| 5 | 其他目的地 | `FINAL,PROXY` |

核心域名基于 OpenAI 官方网络说明维护，覆盖认证、会话、静态资源和附件。共享第三方域名按实际依赖精确匹配。使用 ChatGPT 的文本流式输出、附件、登录与 WebSocket 做回归验证。 [OpenAI 网络建议](https://help.openai.com/en/articles/9247338-network-recommendations-for-chatgpt-errors-on-web-and-apps)

### 默认出口地区

Shadowrocket 的 `PROXY` 使用首页当前节点。使用者在自己的服务器订阅里设置正则，按节点备注中的地区标识筛选，再核验所选节点的实际出口。供应商入口、旗帜或备注只能作为候选线索。节点因订阅刷新而消失或改名时，在同一条订阅里重新选择。需要固定路由时，关闭 Shadowrocket 的全局代理回退。 [OpenAI 支持地区](https://help.openai.com/en/articles/7947663-chatgpt-and-openai-api-supported-countries-and-territories)

### DNS 加密

主解析选择阿里公共 DNS 和腾讯 DNSPod 的 DoH，备用提供 Cloudflare 和 Google Public DNS 的 DoH，以及阿里 `tls://223.5.5.5`。端点用 IP 直接连接，DoH 冷启动无需先为解析器查询域名。四个 DoH 端点的 IP 证书与 DNS 应答已在开发环境验证。允许 `DIRECT` 的公网业务仍由客户端配置的加密 DNS 解析。不同网络下的解析选择与故障表现待 Wi-Fi 和蜂窝网实测。 [阿里公共 DNS](https://alidns.com/) · [腾讯 DNSPod](https://cloud.tencent.com/document/product/302/110786) · [Cloudflare DNS](https://developers.cloudflare.com/1.1.1.1/ip-addresses/) · [Google Public DNS](https://developers.google.com/speed/public-dns/docs/doh)

主配置应关闭系统 DNS 和明文备用解析。优先验证 DoH 引导、节点域名解析和代理侧解析。如果解析器需要经代理才能连通，先验证隧道启动时能否在无循环依赖的情况下建立 DoH。分别在本地接口观察冷启动、直连、代理、IPv6 切换和故障时的 TCP/UDP 53 请求。若该客户端版本有无法关闭的明文行为，记录具体触发条件，按实测结果决定是否达到发布条件。 [Shadowrocket App Store 能力与版本记录](https://apps.apple.com/us/app/shadowrocket/id932747118)

“全局”指 Shadowrocket 已接管并负责解析的公网流量。需单独记录的边界包括 VPN 断开、系统旁路、局域网发现、强制门户、App 内置 HTTPDNS/DoH，以及代理出口侧由服务商控制的解析。局域网发现与强制门户纳入兼容性验证。

### App 开屏广告

- **默认层。** 首先覆盖优先 App 调用的专用开屏域名，再补常用广告 SDK 的已验证域名。优先精确主机名，确认整个后缀专用于广告后才使用后缀规则。共享 API、登录、支付和通用 CDN 域名需要保留业务流量。
- **复现与修正。** 用目标 App 的版本、冷启动步骤、命中域名和业务复测记录每条关键规则。至少比较三轮冷启动，并区分本地预缓存与网络下发。遇到误杀先加最窄例外并验证登录、图片加载等功能，再收窄拦截范围。对无法验证的域名保留为候选。
- **可选模块。** 遇到广告与业务共用 HTTPS 主机，再按 App 评估 `.srmodule`。只对必要的主机和请求路径启用 HTTPS 解密与重写，规则本身须可审阅。启用者在自己的设备上生成并信任 CA。证书固定、客户端缓存和 App 改版都可能导致失效。默认配置无 HTTPS 解密、无远程脚本，也不全局拦截 HTTPDNS。

首版暂设广告规则 **500 条以内、50 KiB 以内**，以实际 App 覆盖和误杀率来调整。主配置内嵌构建后的广告规则，优先用域名类型，避免用宽泛的关键词和常驻重写模块。以真机测得的启动表现、DNS 可用性和 App 兼容性判断轻量化效果。

## 构建和发布

| 拟建路径 | 用途 |
| --- | --- |
| `config/surf.conf.in` | 路由顺序、DoH 设置和广告规则插入位置 |
| `rules/` | 原创和允许再分发的域名清单、例外、来源与适用版本 |
| `scripts/build.py` | Python 标准库构建，按固定顺序输出、去重和生成摘要 |
| `.github/workflows/update.yml` | 计划任务、手动运行、校验和发布 |

1. **素材更新。** 代码默认分支维护审核过的规则。更新时对照已登记的公开上游以及 OpenAI 地区和网络说明。新增广告规则、地区和影响关键服务的调整经审核再并入。已确认地区撤下时，先暂停受影响的候选并复查设备端选择。定时任务发布审核后的版本。
2. **构建校验。** 检查域名和规则类型、行数和文件体积、重复规则、核心域名与广告规则的冲突、候选地区与官方资料的一致性，以及输出是否含节点凭据、私有订阅和本机信息。相同输入产物一致。上游异常、输出为空、变化超出预期或校验失败时，保留上个可用版本。
3. **发布。** `release` 分支提供统一的 `go1f-surf.conf` 下载地址，旧配置地址继续提供相同内容。定时构建在每周一北京时间 08:17 运行，UTC cron 为 `17 0 * * 1`，并支持手动触发。校验后在一次提交中发布配置和模块。GitHub 计划任务可能延后，公开仓库长期无活动也可能暂停。 [GitHub Actions 计划任务](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
4. **终端刷新。** 通过同一地址重新下载完整配置即可获取广告和 DNS 变更，下载后的文件也可本地导入。客户端自动刷新周期和重新连接后的生效行为以真机实测为准。回滚时使用对应历史发布提交中的配置和所需模块。

仓库、构建和发布全程只读公开素材。个人订阅 URL、账户密钥、真实节点出口验证记录和未脱敏流量日志仅留在设备端，GitHub Actions 也无需持有节点订阅。使用虚构样本测试国家/地区标签、歧义命名和节点删除场景。若最终选择私有仓库，另行验证客户端可直接读取的 HTTPS 发布端点，避免把 GitHub 凭据放进订阅 URL。

## 实现顺序与验收

| 阶段 | 交付与验收 |
| --- | --- |
| 1. 客户端最小验证 | 用默认 `PROXY` 验证规则顺序、配置导入和节点订阅刷新。Wi-Fi 与蜂窝分别检查直连和代理业务，验证冷启动、DoT 备用和故障时是否出现系统 DNS 请求。 |
| 2. 个性化首版 | 核验六个目标 App 的专用开屏域名和可选模块。使用虚构节点测试订阅筛选，在设备上核验已选节点的实际出口。通过 ChatGPT 登录、文本流式输出和附件，以及目标 App 登录、内容、消息与支付等相关功能回归。记录开屏拦截结果。 |
| 3. GitHub 发布 | 在个人账号创建 `shadowrocket-surf-rules` 并发布。用固定链接做首次导入、规则更新和回滚测试，确认独立节点订阅更新、规则集变更和完整配置升级之间的关系。 |
| 4. 按需增强 | 对仍有开屏广告的高优先级 App 单独评估可选模块，并验证关闭该模块可恢复原行为。 |

实现前还有三项设备侧输入。Shadowrocket 的版本、最想处理的 App 与版本，以及脱敏后的节点名称样式和设备上确认的出口地区。它们分别决定配置兼容性、开屏覆盖范围和组成员，无需提供订阅链接给构建流程。
