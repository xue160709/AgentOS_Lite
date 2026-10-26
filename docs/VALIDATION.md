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
