# 来源、边界与简化

审查日期：2026-10-26。源项目全部只读，未运行其定时任务或读取密钥/业务库。

| 源 | 已查看的入口 | 采用的原则 | 简化 / 不移植 |
|---|---|---|---|
| `/Volumes/macOS/AgentOS` | `CLAUDE.md`、`data/CLAUDE.md`；仅列 `data/context` 文件名 | 关注/不关注/用途分开放 | 桥接文件引用的根 AGENT.md 缺失；未读取个人身份、记忆或私人偏好正文 |
| `/Volumes/macOS/Agent_OS/agentos-skills` | 上层与本层 AGENTS.md；`.claude/skills/daily-brief-generator/SKILL.md`、`weekly-trend-inference/SKILL.md` | 读 context、跨条目去重、来源与判断分离、0-N 合法 | 不复制产品主轴、用户画像、生产数据库、周月季推演或 context 自动维护 |
| `/Volumes/macOS/Github/newAgentOS` | AGENTS.md、CLAUDE.md、index.md；`collect/PIPELINE.md`、`core/bodies.py`、`core/readable.py` 的结构；`daily-brief/SKILL.md` | 合格正文先复用，路径+哈希追溯、失败可见、日报不是事实证据 | 新版为 HTTP→Jina→Crawl4AI；本项目按任务约定简化为复用→Jina→Crawl4AI，不接 Jev、本体、定时、账号或归档 |

在所查各根与旧 Skill 项目浅层未发现明确 LICENSE。以上仅借鉴流程，代码、Skill 文本和虚构 context 独立编写，不声称继承可再分发许可。后续若复制源代码必须先确认许可。本项目未擅自为用户添加开源许可证；公开可见不等于授予再许可。

官方技术依据（查阅 2026-10-26）：
- [Codex Skills](https://learn.chatgpt.com/docs/build-skills)：项目目录 `.agents/skills` 与显式 `$skill-name`；以本机 CLI 执行日志证明实际读取。
- [Codex 非交互模式](https://learn.chatgpt.com/docs/non-interactive-mode)：`exec --json --output-schema -o`；使用现有认证，模型可读文件，外层脚本保存结构化最终输出。
- [Jina Reader](https://docs.jina.ai/)：`https://r.jina.ai/{url}`，无新凭据。
- [Crawl4AI](https://docs.crawl4ai.com/core/quickstart/)：AsyncWebCrawler、CrawlerRunConfig、markdown；可选本地依赖，不绕登录/验证码。
- OpenCLI 以本机 `opencli hackernews --help -f json` 为准：top/newest/show 均标 read，browser=false。本版只允许 top/newest 两个只读入口。

本机可选 Crawl4AI 运行时独立调用项目脚本，不导入 newAgentOS 代码；环境路径可由用户指定。依赖自身许可由其发行包提供。

周报扩展点：未来可聚合一周已筛选材料并明确缺失日期；本轮不实现或自动维护长期判断。

## 2026-10-27：双 Skill 与分库参考

本轮只读实现规则与源码，没有读取源项目的 context 正文、凭据、业务数据库或运行源项目任务。

- AgentOS `workflow/agentos-skills/.claude/skills/intelligence-data-extractor/SKILL.md`：借鉴“context 决定相关性、1–5 分与理由留在前段”的职责分工。Lite 仅做评分/筛选，不移植实体关系、重点人物规则、业务主轴、高分配额或档案更新。
- 同项目 `daily-brief-generator/SKILL.md`：借鉴“日报读取已评估材料、不重新猜入库字段、同主题归并、0-N 合法、事实与建议区分”。不移植原项目固定栏目、个人画像、行动账本或看板后处理。
- New Agent OS `collect/core/store.py`、`collect/core/paths.py`：借鉴按平台分库、统一写库代码、未知指标不伪造的结构。Lite 使用独立编写的 source_schema.sql 和 analysis_schema.sql。
- New Agent OS `collect/opencli/mapping.py`、`collect/opencli/pipeline.py` 与 `collect/PIPELINE.md`：核对平台字段、小红书 note ID 去重、签名 URL 仅供读取、Twitter 直接复用列表文字、小红书串行调用间隔。未复制其采集配置或真实数据库。
- 本机 OpenCLI v2.0.1 的结构化 help：确认 xiaohongshu search/note、twitter search、tiktok search 为 read；TikTok 当前仅接搜索返回的视频描述，默认关闭，不宣称本轮真实跑通。
- Claude Code [非交互 CLI](https://code.claude.com/docs/en/headless) 与 [项目 Skill](https://code.claude.com/docs/en/skills)：核对项目入口与结构化输出。实际调用能力仍以本机 CLI 和本项目运行回执为准。

上述为流程与结构参考，没有整体复制源代码或 Skill 文本；来源许可边界仍沿用本文前述说明。
