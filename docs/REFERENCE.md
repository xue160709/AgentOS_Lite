# 参考来源与边界

本项目独立编写，只参考流程与数据结构。运行不依赖其他 AgentOS 项目，不读取其画像、凭据或业务数据库。

- **AgentOS 的 intelligence-data-extractor Skill**：参考 context 决定相关性、1–5 分与评分理由留在前段；不移植实体关系、业务主轴、重点人物或高分配额。
- **AgentOS 的 daily-brief-generator Skill**：参考日报读取已评估材料、同主题归并、0-N 合法及事实/建议区分；不移植个人画像、看板、行动账本或固定栏目。
- **New Agent OS 的 collect/core/store.py、paths.py**：参考平台分库、统一写库和未知指标不补造。
- **New Agent OS 的 collect/opencli/mapping.py、pipeline.py**：参考平台字段、小红书 note ID 去重、签名链接仅供本机代码读取、Twitter 复用列表文字和平台调用间隔。

未整体复制源代码或 Skill 文本。所查源项目没有明确的可再分发许可记录；后续若复制代码需单独确认许可，不把公开可见当成再许可。本项目未擅自新增开源许可证。

技术依据：

- [Claude Code 项目 Skill](https://code.claude.com/docs/en/skills) 与 [非交互 CLI](https://code.claude.com/docs/en/headless)。
- [Codex Skills](https://learn.chatgpt.com/docs/build-skills) 与 [非交互模式](https://learn.chatgpt.com/docs/non-interactive-mode)。
- [OpenCLI](https://github.com/jackwener/opencli)：本机 v2.0.1 的结构化 help 已核对 xiaohongshu search/note、twitter search、tiktok search 的只读属性；空结果与基础设施失败按其退出码区分。
- [Jina Reader](https://docs.jina.ai/)。
- [Crawl4AI](https://docs.crawl4ai.com/core/quickstart/)。

技术接口仍以安装版本及真实运行结果为准。TikTok 默认关闭，未将帮助信息核对或字段测试当成真实平台验收。
