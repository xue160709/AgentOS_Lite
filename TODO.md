# 实现清单

协调源：videocreate/TODO.md；本文件仅负责独立实现，不代表课程验收。

- [x] 核实并复用已有 main / origin；工作树初始干净
- [x] 只读参考审查、许可证和简化记录
- [x] 离线最小链、正文质量与恢复测试（17项通过）
- [x] 小量真实 RSS、手动 URL、只读 OpenCLI（5条公开材料）
- [x] Jina / Crawl4AI 分支与真实缺口记录（自然HTML拒收→真实Crawl4AI，另有受控探针）
- [x] Codex CLI 实际读取两个项目 Skill 和 context 并产出（离线输入真实模型链）
- [ ] 最终公开清洗快照的模型筛选与日报：旧快照筛选已留证，2次公开日报429；按README串行续跑
- [x] context 对照筛选、离线日报语义核查与引用校验
- [ ] 娱乐context对日报呈现的第二轮模型对照：受服务缺口影响未执行
- [x] README、教学素材索引与验证记录
- [x] 暂存差异与秘密/私人信息检查（31个文本文件；原始日志/网页/数据库未暂存）
- [x] 实现提交 `8d8f37be267faba532e645bbab06f05912a102db` 正常推送 main；ls-remote 与本机 HEAD 一致。最终交付状态文档另作一次提交。

## 2026-10-27 较早修订记录（历史状态，后续进展见下）

- [x] profile.md 单独写用户画像，interests.md 只列信息主题；当前仍为虚构可替换模板。
- [x] 解释 tests/ 与 fixtures/ 是开发辅助，日常无需操作。
- [x] 准备共用 daily.py 与 macOS/Windows 调度脚本，顺序为采集→筛选→日报。
- [x] 只做预览、macOS plist语法检查与无网络测试；未安装、启用或真实触发任务。
- [ ] Windows 实机验证；macOS真实触发与完整每日流程尚未执行。

新增 profile 与 Skill文字会改变context/Skill哈希，旧模型结果保留为历史证据，不能当作新context已执行。

- [x] 按用户后续指示将OpenCLI接入每日采集：RSS、URL队列、HN top只读2条共用data/daily，全部采集后统一补正文/筛选/日报。
- [x] 保留仅准备、不启用的调度行为；本轮只做预览和受控离线验证，没有启动实际来源/模型请求。

## 2026-10-27：当前 MVP（替代前述同日较早轮次的范围）

- [x] 只读参考 AgentOS 的 intelligence-data-extractor / daily-brief-generator 和 New Agent OS 的分库、映射、去重代码；未读取私人 context、凭据或业务库。
- [x] 恢复两个独立 Skill：filter-materials 评分筛选、write-daily 只写日报；Claude Code 与 Codex 均有项目入口，共用规则。
- [x] 来源配置分 RSS / URL / OpenCLI；小红书、Twitter 各自 JSON 样例；TikTok 提供默认关闭的视频描述样例。
- [x] 按平台独立 SQLite，原件与来源状态分库存；分析库单独存评分、日报运行和处理状态，结构见 docs/STORAGE.md。
- [x] 小红书由固定代码执行 search → note → 原文归档；按 note ID 去重，临时签名不进入模型输入。
- [x] RSS 2 + URL 1 + Twitter 2 + 小红书 2，共 7 条真实采集、7 条正文；Claude 两阶段完整通过。
- [x] daily.py 组合入口真实完成 Codex 采集 → 评分 → 日报；各阶段成功且评分与引用校验通过。
- [x] 32 项测试、四个 Skill 格式校验、预览和 Git 忽略边界检查通过。
- [x] 共享 config/context/Skill 保留可提交；本机覆盖、原件、数据库、日志与真实日报忽略。
- [ ] TikTok 真实平台采集验证（默认关闭；本轮不计入验收）。
- [ ] Windows 实机定时验证。macOS/Windows 任务均未注册或启用；所有真实运行均手动触发。

Claude 的人工/模型审阅修正与原输出分别保留；机器引用校验不等于独立事实核查。完整路径与本机依赖边界见 docs/VALIDATION.md。
- [x] 同一分库资料库再次真实运行：来源 ok、待处理 0 条、两阶段均未再调用模型，重复执行退出 0。

## 发布前复查

- [x] README 补全从克隆、安装、登录/浏览器连接、正文后备配置到运行日报的步骤。
- [x] 再核 Claude/Codex 两个独立 Skill 的真实成功回执及日报文件。
- [x] OpenCLI 空结果退出码与基础设施失败区分，33 项测试通过。
- [x] 发布范围限定为代码、Skill、共享 config/context、测试与说明；原件/运行数据保持忽略，定时任务保持未启用。最终提交与推送状态以 Git 记录为准。
