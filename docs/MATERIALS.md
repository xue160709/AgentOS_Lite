# 教学取材索引

本文件供协调会话取材，不代表已拍摄或课程审稿通过。未新增教学 UI，未改课程母稿、配音或模板。所有终端/文件取材后仍应实际查看截图，避免暴露其他会话状态。

| 讲解动作 | 可打开的文件或命令 | 实际证据及边界 |
|---|---|---|
| 决定关心什么 | `context/interests.md`、`disinterests.md`、`report.md` | 虚构图书馆读者；与原项目个人偏好无关 |
| 修改来源与关键词 | `config/rss.json`、`keywords.json` | RSS JSON，关键词提示不代替语义判断 |
| 手动加链接 | README 的 add → queue → status | SQLite 官方参考 URL 已真实入队、导入；队列与材料共用 URL 身份 |
| 固定离线导入 | `data/offline-clean/receipts/`；`fixtures/materials.json` | 3 条虚构演练，重跑 duplicate=3；2 复用、1 待补，无网络 |
| RSS 发现 | `data/public/raw/230fbf961b2071e3de2bc3dc1f9336f7f5d150ab95336a9c2e8914d1278bd269.xml` | Python 官方博客真实响应；重跑 new=0、duplicate=2、failed=0 |
| OpenCLI 只读 | `data/public/raw/50354b1736c89498e05a0ab32c4c4e57852bff0a97c5f0051bf2f0370eb67bed.json` | HN top 公共适配器真实 2 条；不能代表 X、小红书或浏览器桥接验证 |
| 正文获取与复用 | `data/public/library.sqlite` 的 attempts/body_versions | 最终 4 篇 Jina、1 篇自然质量降级后 Crawl4AI 成功；修正后 bodies 为 reused=5；提取覆盖未逐字核验 |
| 浏览器降级 | `data/crawl-probe/library.sqlite`、receipts | Jina 故障为受控模拟；其后 Crawl4AI 真实读取 SQLite 官方页成功，不能说自然网络触发 |
| 失败后恢复 | `tests/test_pipeline.py`，`test_failure_is_recoverable_and_not_zero_new` | 无网络受控故障和恢复测试；不伪装为真实服务故障 |
| 查看数据库 | README 的 sqlite3 查询 | 可看材料、观测、正文版本、尝试、队列、运行、决策七张表 |
| 模型真的读取 Skill | `runs/offline-filter/events.jsonl` / `read-evidence.json` | 已完成命令输出含 Skill 全文与三份 context 全文，不只是“我已读取”的自述 |
| 模型筛选 | `runs/offline-filter/model.json`；`runs/public-filter/model.json` | 前者 1/1/1，后者 4 keep、1 exclude；有原文短引与限制 |
| context 对照 | `fixtures/context-entertainment/`；`runs/context-alt-filter/model.json` | 同一原件的技术/娱乐决定反转；模糊标题仍 pending |
| 写日报 | `runs/offline-daily/daily.md` | 真实模型生成，但输入是虚构材料；待补项进入缺口，无真实经历声称 |
| 查看真实限流 | `runs/public-daily/receipt.json` 和 events | 真实 CLI 返回 429，该次未生成日报；有限重试结果见验证记录 |
| 可分享样例 | `examples/` | 仅经检查的少量内容、输出与哈希索引，不上传大段网页/数据库/完整运行日志 |

S4 可围绕采集入口、状态保存、正文路线、去重与恢复展开；S5 可围绕 context、Skill、决策依据、日报结构、输入失效和语义审查展开。具体课程集数由协调会话根据实际画面决定，本实现不宣称 31 集已验证。
