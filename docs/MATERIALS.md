# 教学取材索引

所有操作在本项目完成，不依赖其他 AgentOS 仓库。context 是虚构示例，fixtures 是无网络测试输入；运行日志与原始页面不在 GitHub。

| 讲解动作 | 文件或命令 | 说明 |
|---|---|---|
| 配置来源 | config/sources/rss.json、urls.json、opencli/*.json | 按类型/平台分开，enabled 控制启用 |
| 定义读者偏好 | context/ 的四份 Markdown | profile、interests、disinterests、report 各司其职 |
| 查看采集计划 | python3 scripts/collect.py --preview --out runs/demo/input.json | 不请求网络或模型 |
| 实际采集 | python3 scripts/collect.py --out runs/demo/input.json | 代码获取正文、按平台入库、导出净化快照 |
| 查看分库 | docs/STORAGE.md | 原文与模型结果分开，平台之间不混库 |
| 筛选评分 | python3 scripts/filter.py --input runs/demo/input.json --out runs/demo/filter | 第一个 Skill，输出分数、结论、原文依据 |
| 写日报 | python3 scripts/generate.py --input runs/demo/input.json --selection runs/demo/filter/model.json --out runs/demo/daily | 第二个 Skill，只用 keep 材料 |
| 一次完整运行 | python3 scripts/daily.py | 依次采集、评分、写日报；手动运行不启用定时任务 |
| 失败与恢复 | tests/test_pipeline.py、tests/test_sources.py | 引用/版本校验、失败保留、去重和日报失败不标完成 |
| 离线演练 | fixtures/materials.json，README 中的 fixture/export 命令 | 不需要网络，不冒充真实新闻或模型输出 |

实际网络/模型证据范围见 VALIDATION.md。取材时只打开本批次必要文件，避免展示其他会话或登录态。
