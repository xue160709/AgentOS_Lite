# 验证记录

2026-10-26，北京时间；执行者为实现会话，协调会话另行复核与教学验收。阶段：参考梳理 → 离线链 → 少量实采 → 真实模型 → 校验 → GitHub 交付。以下不以命令退出码代替语义审稿。

## 环境与本轮范围

- Python 3.14.3；Codex CLI 0.162.1；OpenCLI 2.0.1。
- 可选 Crawl4AI 0.9.3：本机已有 `/Volumes/macOS/Github/newAgentOS/.venv-collect/bin/python`，仅作为依赖运行时执行本项目 `scripts/crawl_body.py`；未改源项目或加载其业务代码/凭据。
- 源项目许可未确认，未复制源代码、私人 context、生产库或密钥；参考索引见 REFERENCE.md。
- 没有 ASR、配音、前端、定时任务、线上日报归档、X/小红书操作或视频制作。

## 无网络代码验证

`python3 -m unittest discover -s tests -v`：17 项通过。覆盖 URL 去重与观测保留、成功正文不发网络、Jina 成功即停止、坏 Jina 转浏览器、双失败恢复、缓存篡改、刷新失败保留版本、关键词不作语义排除、RSS summary 不作正文、Atom、错误 XML、HTML 文档外壳拒收且正常 Markdown 中 HTML 示例不误拒、context 变化、快照变化与输出篡改拒绝、完整 Skill/context 读取证据、伪造引文拒绝。

两个项目 Skill 均通过 skill-creator 的 `quick_validate.py`；该检查只证明格式合格。

干净离线目录：`data/offline-clean/`。fixture 首导 new=3；`bodies --offline` reused=2、pending=1；重导 duplicate=3。此前开发中未加离线开关的 `data/offline/` 留作历史记录，不作为离线证据；最终 README 始终使用 `--offline`。

## 真实公开采集

| 入口 | 本机结果 | 证据范围 |
|---|---|---|
| Python 官方 RSS | 首次成功 2 条；重跑 new=0、duplicate=2、failed=0 | RSS 真返回及链接，不保证今日完整新闻覆盖 |
| 手动 URL | SQLite 官方 whentouse 页面，队列导入 1 条 | URL 身份、原件、观测与状态可查 |
| OpenCLI | `hackernews top --limit 2 -f json` 成功 2 条 | 公共 API 适配器，不能据此声称 X、小红书或浏览器 Bridge 已通过 |
| Jina | 最终 4 篇有效正文成功 | 两条 RSS 公告、两条 OpenCLI 链接；提取覆盖未独立逐字核验 |
| 自然质量降级 | SQLite 的 Jina Markdown 字段实际上是 HTML 文档，最终质量门拒收后 Crawl4AI 真实成功 | 没有绕登录/验证码；保留旧误收版本、rejected attempt 与新版本 2 |
| 受控路由探针 | `data/crawl-probe/` 模拟 Jina TimeoutError，其后 Crawl4AI 真实读 SQLite 成功 | 仅 Jina 故障是模拟，浏览器请求是真实；与自然质量降级分开 |
| 重复正文 | 最终新质量门重跑 reused=5，无正文网络请求 | 旧 SQLite HTML 的复用属于已修复缺陷；最终复用的是版本2的 Crawl4AI 正文 |

全部实采材料位于 `data/public/library.sqlite`（5 条）。原始 RSS/OpenCLI/Reader 返回、正文和失败尝试按 SHA256 留在 `data/public/raw/`。最终快照是 `outputs/public-current-input.json`，旧 `outputs/public-input.json` 保留以回查早期模型输入。源的发布时间与观察/抓取时间分开；BBC 来源无绝对发布时间，不补成采集日。

开发时曾因本机代理合成 DNS 被自行加入的地址检查误拒收 RSS；已修正并成功读取，初次失败回执保留。它不是 RSS 零新增，也不是远端服务失败。

## 真实模型和内容核查

本轮用现有正常认证执行，没有读取密钥、换模型或更改账号。实际 CLI 先出现 WebSocket 426 后回退 HTTP，成功运行的最终 returncode=0；不能把启动警告等同失败。

| 本机目录 | 结果 | 内容核查 |
|---|---|---|
| `runs/offline-filter` | 1 keep / 1 exclude / 1 pending | SQLite 练习支持小林任务；星座演练排除；模糊标题缺正文待补，理由和短引均可回查 |
| `runs/offline-daily` | 实际模型日报通过最终校验 | 明标虚构演练，原文陈述与建议分开；没有把建议写成已完成验证；pending 进入缺口，说明离线未请求网络 |
| `runs/context-alt-filter` | 技术 exclude、娱乐 keep、缺正文 pending | 同一原件、改虚构关注/不关注后决定反转；只当娱乐栏目编排例子，不认可预测真实性 |
| `runs/public-filter` | 早期 4 keep / 1 exclude | 关键短引真实存在；技术文档/公告与任务相关，观鸟报道排除；但 SQLite 当时误收 HTML，此结果仅归属早期快照，最终快照待重筛 |
| `runs/public-daily` | failed / 429 | 没有最终日报；原错误事件保留 |
| `runs/public-daily-retry1` | failed / 429 | 有限重试仍失败；未更换认证、模型或权限 |

成功日志的已完成工具输出中逐一找到 Skill 全文和三份 context 全文，已运行 `trace_reads` 复核；`read-evidence.json` 留本机。脱敏汇总在 `examples/evidence.json`，完整日志不提交。前 3 次运行早于输出哈希字段，之后只补做完整性复核并标 `post_run_integrity_checked_at`，没有修改模型输出/events，也没有伪称重新模型执行。

语义检查是实现代理对照正文做的审查，不代表讲师人工签字或最终教学批准。SQLite 初次 HTML 误收的修复说明“静态通过”和“来源抽取正确”必须分别核对。

## 当前未满足及重跑

公开材料最终清洗快照尚需重新筛选并生成真实日报；公开旧清单不能静默用在最终快照。两次日报 429 是真实服务缺口，不以自写日报补齐。娱乐 context 对日报呈现的第二轮模型对照尚未执行；本轮已实测其对筛选的影响。

服务恢复后按顺序运行，out 使用不存在的新目录；现有日志不覆盖：

```bash
python3 scripts/run_skills.py filter --input outputs/public-current-input.json --out runs/public-final-filter
python3 scripts/run_skills.py daily --input outputs/public-current-input.json --selection runs/public-final-filter/model.json --out runs/public-final-daily
python3 scripts/run_skills.py daily --input outputs/offline-clean-input.json --selection runs/context-alt-filter/model.json --context fixtures/context-entertainment --out runs/context-alt-daily
```

在全新电脑先按 README 重新采集/export，文件内容与哈希会变化，再按自己的快照筛选；不要求重新出现本轮新闻。模型若继续 429，保留 failed 回执后停止，不轮询、不换账号、不用 fixture 冒充实采。

实现已提交并正常推送至 `https://github.com/xue160709/AgentOS_Lite` 的 main：`8d8f37be267faba532e645bbab06f05912a102db`；`git ls-remote origin refs/heads/main` 与本机 HEAD 核对一致。此后仅更新交付状态文档，最终文档提交由交付报告给出。协调者仍需复核远端与教学适用性；本文件不宣称整个课程或所有平台验证完成。

## 2026-10-27：画像分离与定时脚本（本机未提交修改）

按用户新要求，profile.md放画像、interests.md只列关注信息；当前仍为虚构可替换示例。两个Skill说明画像与主题的区别。新增daily.py统一顺序执行采集、筛选和日报，macOS/Windows脚本默认只准备配置，显式安装选项才注册。

本次只运行daily.py --preview、生成macOS plist并通过plutil -lint，以及20项快速离线测试。测试确认预览不发起进程/网络/模型、采集失败不会继续模型步骤、--pending只选缺正文项。未执行真实每日全链，未注册或启用任务；本机没有PowerShell，Windows脚本只核对Microsoft官方接口，尚未语法运行或实机验证。

profile和Skill变更会使旧context/Skill哈希失效，已有模型产物只保留为历史证据，不代表新context已执行。此前未提交的Flash单次参数修改继续保留，本次不自动推送。

### 2026-10-27 后续：OpenCLI纳入自动采集

按用户明确指示，daily.py在RSS/URL队列之后调用现有只读入口 `opencli --feed top --limit 2`，再统一补正文、export、filter、daily；三路共用data/daily。两个平台的配置引用同一个daily.py，因此无需分别添加平台采集逻辑。

本次预览为7步；新增受控测试检查三路共用材料库、OpenCLI早于筛选、OpenCLI失败阻止筛选/日报。只做无网络测试和预览，不启用/注册任务，也未把Hacker News适配器的覆盖范围扩大宣称为其他平台。此前6步预览是接入OpenCLI前的历史结果。

## 2026-10-27：独立评分 Skill、日报 Skill 与分平台数据库

本节为当前 MVP 验证。前述历史轮次的服务失败、旧快照和旧流程保持记录，不能与本轮混算。

### 本机真实采集（固定代码）

- 执行：`python3 scripts/collect.py --home data/platform-e2e --out runs/platform-e2e/input.json`。
- RSS python-blog 2 条、固定 URL sqlite-guide 1 条、Twitter 搜索 2 条、小红书搜索 2 条，总计 7 条且 7 条均有正文，采集状态 ok、0 item_errors。
- 数据分别在 `data/platform-e2e/sources/{rss,urls,twitter,xiaohongshu}/<平台>.sqlite`，各有独立 raw/。小红书是 Python 固定调用 OpenCLI search/note，没有模型参与网页操作或改采集代码。
- SQLite 网页正文先经 Jina 质量拒收，再由已有隔离 Crawl4AI 运行时成功取得。本机路径放在忽略的 runtime.local.json；未把该机器路径写入共享 runtime.json。其他使用者需要按 README 安装自己的可选后备环境。
- TikTok 搜索能力按本机 help 核对为只读，配置默认关闭。仅验证其独立存储与字段映射的无网络测试，不宣称真实 TikTok 抓取通过。

### Claude Code 两阶段（真实模型）

- `scripts/filter.py --input runs/platform-e2e/input.json --out runs/platform-e2e/filter`：实际调用筛选评分 Skill，7 项覆盖，keep=5/exclude=2/pending=0，评分与短引校验通过。
- `scripts/generate.py --input runs/platform-e2e/input.json --selection runs/platform-e2e/filter/model.json --out runs/platform-e2e/daily`：独立调用日报 Skill，输入/评分/context 版本绑定及原链接校验通过。
- 两份 receipt.json 均为 validated。analysis.sqlite 有 filter/daily 各 1 次 stage_runs、7 条 scores、7 条 processed；只有日报成功后才更新 processed。
- 对照原文审阅后，修正 daily.md 中小红书 method 标注和未获原文支持的“付费/未公开”推断；原 model.json 不改，review.json 记录改前后哈希与原因。审阅仅针对采集文本支持范围，不是对帖子涉及的外部技术声明做独立事实核查。

### Codex 组合入口（真实模型）

- 执行：`python3 scripts/daily.py --engine codex --model ccs-deepseek/deepseek-flash --home data/platform-job`。模型只在本次命令指定，未改共享默认或全局配置。
- 完整批次：`reports/2026-10-27_10-24-17_208478/`。来源状态 ok、7 条正文；filter 与 daily 各自 validated，主命令退出 0。
- keep=6/exclude=1/pending=0，日报采用 6 条。与 Claude 的一条边界材料评分不同，是相关性判断差异，不当作确定性一致性通过。
- 日报已对照输入查看来源时间、归并、原链接/ID、平台文字限制和未独立核实的说法。两条路径使用不同资料库，未相互污染处理状态。

### 机器检查与提交边界

- 当前 32 项无网络测试通过：包含平台物理分库、源库不含模型表、跨来源快照去重、帖子 ID/签名/路径去重、评分门槛与 pending 规则、被篡改筛选清单拒收、日报失败不标完成、context 变化重评、签名输入在调用模型前拒收、部分采集退出码与三阶段顺序等。
- Claude/Codex 四个 Skill 的 quick_validate 通过；diff 空白检查、编译检查与预览通过。
- 共享 config/context/项目 Skill 均未忽略；运行库/原件/快照/日志/个人覆盖均忽略。未暂存、提交或推送本轮改动，保留工作区其他会话原有修改。
- 定时任务只准备过配置并检查 macOS plist 语法；未安装、注册或启用。Windows 实机调度仍未验证。

### 保留的旧尝试

先前单次合并评分/日报的试跑是已放弃的实现，不代表当前双 Skill 验证。其旧快照曾含小红书临时访问参数，后续一次调用被自动审批拦截；现采集快照移除参数，CLI 入口在模型调用前拒绝含签名输入。旧响应与失败回执仅在本机忽略目录保留，不作为可提交样例。

### 同库重复执行

再次执行相同 Codex daily 命令，批次 `reports/2026-10-27_10-28-58_300643/`：四个来源状态 ok，新增待处理快照为 0 条，筛选/日报均 validated 且 model_called=false、outcome=no_new_materials，主命令退出 0。证明已处理内容没有重复报道，也没有为凑日报再次调用模型；不据此推断将来平台不会变化或不会失效。

## 2026-10-27：发布前可复制性检查

README 已补克隆、Python/CLI 安装入口、Browser Bridge 与平台登录前提、四路采集所需的独立 Crawl4AI 安装命令和完整本机覆盖配置步骤。明确不依赖维护者的其他仓库路径、不自动启用定时任务。

复查真实回执：Claude 的 filter/daily 均 validated、model_called=true、returncode=0；Codex 完整组合批次的两个阶段相同；重复执行批次两个阶段均无模型调用。对应的原始响应、日志和数据库只留在本机忽略目录，不提交。

发布前还修正 OpenCLI 空结果退出码 66 的处理：与基础设施失败 69 分开，保留本机响应。新增回归验证后共 33 项无网络测试通过；README 相对链接、共享 JSON、差异空白检查均通过。真实网络与模型证据来自上述明确列出的批次，离线检查不冒充新的真实采集。

待提交 Git 索引已导出到不含 runtime.local.json、context/local/、data/ 的干净临时目录；在该目录独立通过 33 项测试、collect/daily 两种预览、离线 fixture 导入与 3 条材料导出。暂存文件逐项检查，共享配置与虚构 context 包含在发布范围，原件/数据库/日志/本机覆盖未暂存。签名拒收测试中的字面假 token 已人工确认是合成测试输入；未发现真实密钥或访问签名。
