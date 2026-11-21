# shadowrocket-surf-rules 概要设计

调研日期为 2026 年 11 月 21 日。目标设备为 iOS 上的 Shadowrocket，具体客户端版本需通过真机确认。配置的当前用法和定时发布机制见 [README](README.md)。

## 方案结论

首版采用一份轻量主配置 `surf.conf` 和一个域名级广告规则集 `ads.list`。在 Shadowrocket 的「配置」路由模式下，受客户端接管的公网 DNS 查询使用 DoH，开屏广告优先拦截独立广告域名，常规代理和 ChatGPT 组都只从已核验的受支持地区出口中选节点。哔哩哔哩、微博、豆瓣、网易云音乐、QQ 音乐和高德地图各有一个可选开屏模块。

配置订阅和节点订阅分别更新。个人 GitHub 仓库 `shadowrocket-surf-rules` 仅发布不含凭据的配置和规则，现有节点订阅由设备端的 Shadowrocket 单独管理。本次概设未访问该订阅，未采集节点样本。

## 社区方案对比

| 项目 | 优点 | 局限 | 本项目取舍 |
| --- | --- | --- | --- |
| [Hackl0us / SS-Rule-Snippet](https://github.com/Hackl0us/SS-Rule-Snippet) | 跨客户端整理了常见分流和规则结构，支持配置导入与快捷指令更新，README 也讨论了广告拦截误伤。 | 项目明确不提供网页广告规则。分流模板无法直接满足优先拦截 App 开屏、严格 DNS 回退和出口地区核验的要求。 | 借鉴精简的分流结构与直连例外。配置自行编写。 |
| [Johnshall / Shadowrocket-ADBlock-Rules-Forever](https://github.com/johnshall/Shadowrocket-ADBlock-Rules-Forever) | 面向 Shadowrocket 自动重建，通过固定链接发布。包括黑名单、白名单、国内外分流、仅去广告和策略组等配置。 | 完整广告配置汇集多个来源，逐条追踪误伤和来源的成本较高。开屏覆盖未见逐 App、逐版本的说明。 | 借鉴定时构建、固定入口和可回滚的发布流程。用小规则集保留可定位的误杀记录。 |
| [ithtelab / sr-adblock](https://github.com/ithtelab/sr-adblock) | 将域名拦截、可选 HTTPS 解密模块和主配置分开，展示了节点订阅与配置订阅独立的办法。 | 聚合域名和解密范围较大。其基础配置允许明文和系统 DNS，节点组按名称匹配。 | 借鉴分层和逐 App 模块，保留更小的默认范围。通过其产物了解配置语法，客户端行为以真机为准。 [示例主配置](https://raw.githubusercontent.com/ithtelab/sr-adblock/release/conf/base.conf) |
| [blackmatrix7 / ios_rule_script](https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/Shadowrocket/OpenAI) | 提供可直接阅读的 Shadowrocket 服务域名列表，适合做覆盖交叉检查。 | 服务域名、脚本和聚合数据的适用条件有差异，仓库另有资源使用声明，列表也会落后于服务变化。 | 以 OpenAI 官方资料为准，社区列表用于核对遗漏。 [上游说明](https://github.com/blackmatrix7/ios_rule_script) |
| [AdGuard DNS Filter](https://github.com/AdguardTeam/AdGuardSDNSFilter) | 包含移动广告过滤来源，已针对 DNS 级阻断做简化。 | 完整列表超出首版预算，语法还包括白名单和修饰符，直接抽域名可能改变语义。 | 作为候选域名线索，经验证后再决定纳入方式。使用上游数据时按实际文件核对授权、来源和署名要求。 |

## 客户端设计

### 路由和优先级

用户在 Shadowrocket 选择「全局路由 → 配置」。按以下逻辑顺序组织 `[Rule]`。独立域名规则和远程 `RULE-SET` 混排的优先级在真机确认。

| 顺序 | 匹配 | 动作 |
| --- | --- | --- |
| 1 | ChatGPT 和 OpenAI 核心服务域名 | 进入 `ChatGPT` 策略组，优先于所有广告规则 |
| 2 | 开屏误杀例外、已确认的局域网目标 | 例外显式指定原本应使用的策略，局域网直连 |
| 3 | 专用开屏广告域名、已验证的公共广告域名 | `REJECT`，从自托管 `ads.list` 加载 |
| 4 | 常用国内服务域名、`.cn`，以及地址已知时适用的国内 IP 规则 | `DIRECT` |
| 5 | 其他目的地 | `FINAL` 进入 `常规代理` |

核心域名基于 OpenAI 官方网络说明维护，覆盖认证、会话、静态资源和附件。共享第三方域名仅按实际依赖精确匹配。登录验证等经真机确认需要保持同一出口的主机加入 `ChatGPT` 组。共享支付、客服等域名可针对确切子域防误拦，保留其正常路由。使用 ChatGPT 的文本流式输出、附件、登录与 WebSocket 做回归验证。 [OpenAI 网络建议](https://help.openai.com/en/articles/9247338-network-recommendations-for-chatgpt-errors-on-web-and-apps)

### 默认出口地区

默认约束覆盖 `ChatGPT` 和 `常规代理`。初始候选地区取日本、新加坡和美国，均在调研日的 OpenAI 支持名单中。香港未列入该名单。以后以官方名单与个人选定地区的交集确定候选范围。 [OpenAI 支持地区](https://help.openai.com/en/articles/7947663-chatgpt-and-openai-api-supported-countries-and-territories)

1. **设备端先核验，再入组。** 核验的是通过该策略实际出去的公网 IP 和地区。节点名、旗帜、入口服务器位置和延迟测速只用来缩小候选范围。对地区冲突、未知地区或入口与出口混标的节点，先排除并单独核验。
2. **首版用显式选择。** 两组各自只包含设备端已核验的节点。`ChatGPT` 默认固定一个出口，减少会话期间的变化。根据实际节点命名，后续可用 `policy-regex-filter` 辅助查找候选节点。宽泛的地区关键词无法约束实际出口，也不能证明当前供应商的命名方式。
3. **无合格节点时明确不可用。** 两组均禁止回退到未筛选的节点或直连。实现先用虚构节点测试显式拒绝、订阅移除和节点改名后的行为。若客户端会替空组自动选其他节点，分发版的 ChatGPT 路由及代理兜底直接使用 `REJECT`，完成本机选组后再启用。订阅更新后重新验证发生变化的条目，完整配置更新后复核本机选组。

IP 地理库可能有偏差。地区核验只能提高路由选择的准确性，服务可用性仍取决于 OpenAI 的实际判定。首版上线门槛是验证没有意外回落到香港、未知出口或 `DIRECT`。

### DNS 加密

首版主用阿里公共 DNS `https://dns.alidns.com/dns-query`，备用腾讯 DNSPod `https://doh.pub/dns-query` 和 Cloudflare `https://cloudflare-dns.com/dns-query`。允许 `DIRECT` 的公网业务仍应使用 DoH。两条备用端点的调用顺序和故障表现待 Wi-Fi 与蜂窝网实测。 [阿里公共 DNS](https://alidns.com/) · [腾讯 DNSPod](https://cloud.tencent.com/document/product/302/110786) · [Cloudflare DoH](https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/make-api-requests/)

主配置应关闭系统 DNS 和明文备用解析。优先验证 DoH 引导、节点域名解析和代理侧解析。如果解析器需要经代理才能连通，先验证隧道启动时能否在无循环依赖的情况下建立 DoH。分别在本地接口观察冷启动、直连、代理、IPv6 切换和故障时的 TCP/UDP 53 请求。若该客户端版本有无法关闭的明文行为，记录具体触发条件，按实测结果决定是否达到发布条件。 [Shadowrocket App Store 能力与版本记录](https://apps.apple.com/us/app/shadowrocket/id932747118)

“全局”指 Shadowrocket 已接管并负责解析的公网流量。需单独记录的边界包括 VPN 断开、系统旁路、局域网发现、强制门户、App 内置 HTTPDNS/DoH，以及代理出口侧由服务商控制的解析。局域网发现与强制门户纳入兼容性验证。

### App 开屏广告

- **默认层。** 首先覆盖优先 App 调用的专用开屏域名，再补常用广告 SDK 的已验证域名。优先精确主机名，确认整个后缀专用于广告后才使用后缀规则。共享 API、登录、支付和通用 CDN 域名需要保留业务流量。
- **复现与修正。** 用目标 App 的版本、冷启动步骤、命中域名和业务复测记录每条关键规则。至少比较三轮冷启动，并区分本地预缓存与网络下发。遇到误杀先加最窄例外并验证登录、图片加载等功能，再收窄拦截范围。对无法验证的域名保留为候选。
- **可选模块。** 遇到广告与业务共用 HTTPS 主机，再按 App 评估 `.srmodule`。只对必要的主机和请求路径启用 HTTPS 解密与重写，规则本身须可审阅。启用者在自己的设备上生成并信任 CA。证书固定、客户端缓存和 App 改版都可能导致失效。默认配置无 HTTPS 解密、无远程脚本，也不全局拦截 HTTPDNS。

首版暂设广告规则 **500 条以内、50 KiB 以内**，以实际 App 覆盖和误杀率来调整。主配置引用一个广告规则集，优先用域名类型，避免用宽泛的关键词和常驻重写模块。以真机测得的启动表现、DNS 可用性和 App 兼容性判断轻量化效果。

## 构建和发布

| 拟建路径 | 用途 |
| --- | --- |
| `config/surf.conf.in` | 路由顺序、DoH 设置、策略和规则集地址 |
| `rules/` | 原创和允许再分发的域名清单、例外、来源与适用版本 |
| `scripts/build.py` | Python 标准库构建，按固定顺序输出、去重和生成摘要 |
| `.github/workflows/update.yml` | 计划任务、手动运行、校验和发布 |

1. **素材更新。** 代码默认分支维护审核过的规则。更新时对照已登记的公开上游以及 OpenAI 地区和网络说明。新增广告规则、地区和影响关键服务的调整经审核再并入。已确认地区撤下时，先暂停受影响的候选并复查设备端选择。定时任务发布审核后的版本。
2. **构建校验。** 检查域名和规则类型、行数和文件体积、重复规则、核心域名与广告规则的冲突、候选地区与官方资料的一致性，以及输出是否含节点凭据、私有订阅和本机信息。相同输入产物一致。上游异常、输出为空、变化超出预期或校验失败时，保留上个可用版本。
3. **发布。** 建议在个人帐号创建公开仓库并通过 `release` 分支的 Raw HTTPS 链接提供下载。固定入口为 `https://raw.githubusercontent.com/<github-user>/shadowrocket-surf-rules/release/surf.conf`，规则集同目录。定时构建提议每周一北京时间 08:17，UTC cron 为 `17 0 * * 1`，并支持手动触发。校验完成后一次提交更新两个产物，保留发布提交和下载地址用于回滚。GitHub 计划任务可能延后，公开仓库长期无活动也可能暂停。 [GitHub Actions 计划任务](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
4. **终端刷新。** 日常广告规则更新走远程 `RULE-SET`，从客户端实测刷新周期、失败缓存和重新连接后的生效行为。DNS、主配置和策略组变更走完整配置更新。本机节点选择或个人例外如会被覆盖，主配置只提示手动升级并在升级前备份。如果远程规则不能可靠自动刷新，再测试 Shadowrocket 的更新操作及快捷指令。全量回滚时从上个可用发布提交恢复两份产物，再刷新客户端。若只在本机回滚，旧配置内的规则集地址也要指向对应的历史提交。

仓库、构建和发布全程只读公开素材。个人订阅 URL、账户密钥、真实节点出口验证记录和未脱敏流量日志仅留在设备端，GitHub Actions 也无需持有节点订阅。使用虚构样本测试国家/地区标签、歧义命名和节点删除场景。若最终选择私有仓库，另行验证客户端可直接读取的 HTTPS 发布端点，避免把 GitHub 凭据放进订阅 URL。

## 实现顺序与验收

| 阶段 | 交付与验收 |
| --- | --- |
| 1. 客户端最小验证 | 用最小 `.conf` 和虚构节点验证规则顺序、远程规则导入、空组拒绝、改名和移除后行为。Wi-Fi 与蜂窝分别核验 DoH 对直连和代理业务的影响，验证冷启动和 DNS 故障时的回退。 |
| 2. 个性化首版 | 核验六个目标 App 的专用开屏域名和可选模块。核验日本、新加坡、美国候选样本及香港、歧义标签的排除路径。通过 ChatGPT 登录、文本流式输出和附件，以及目标 App 登录、内容、消息与支付等相关功能回归。记录每个 App 的开屏拦截结果与仍出现广告的情况。 |
| 3. GitHub 发布 | 在个人账号创建 `shadowrocket-surf-rules` 并发布。用固定链接做首次导入、规则更新和回滚测试，确认独立节点订阅更新、规则集变更和完整配置升级之间的关系。 |
| 4. 按需增强 | 对仍有开屏广告的高优先级 App 单独评估可选模块，并验证关闭该模块可恢复原行为。 |

实现前还有三项设备侧输入。Shadowrocket 的版本、最想处理的 App 与版本，以及脱敏后的节点名称样式和设备上确认的出口地区。它们分别决定配置兼容性、开屏覆盖范围和组成员，无需提供订阅链接给构建流程。
