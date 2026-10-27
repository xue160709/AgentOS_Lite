# AgentOS Lite

这是可复制使用的信息采集与日报框架。先读 README.md；项目边界与原件保护规则见 AGENTS.md。

- Python 脚本负责采集；Claude Code 的 `.claude/skills/filter-materials/` 负责筛选评分，`.claude/skills/write-daily/` 负责写日报，Codex 入口保留在 `.agents/skills/`。
- 两阶段共用规则在 docs/filter-workflow.md、docs/daily-workflow.md。采集、评分、日报分别运行；daily.py 顺序调用这三步，不启用定时任务。分平台数据库结构见 docs/STORAGE.md。
- config/ 与 context/ 为公开可替换的示例；context 仅由用户修改。个人偏好放被忽略的 context/local/，本机配置用 *.local.json。
- 运行产物 data/、runs/、reports/、outputs/ 不提交；不把浏览器登录态、访问参数、密钥或 CLI 运行日志写入公开样例。
- 未获得明确启用指示，不安装定时任务；不发布、不推送。
