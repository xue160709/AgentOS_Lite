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
