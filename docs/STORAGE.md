# MVP 数据库结构

原则：按平台分库存原件与采集状态，模型产物另存分析库。日报通过一次性 JSON 快照跨库读取，不将所有平台原文复制进统一数据库。

```text
data/<批次或持续资料库>/
  sources/
    rss/rss.sqlite
    rss/raw/<sha256>.<扩展名>
    urls/urls.sqlite
    urls/raw/...
    xiaohongshu/xiaohongshu.sqlite
    xiaohongshu/raw/...
    twitter/twitter.sqlite
    twitter/raw/...
    tiktok/tiktok.sqlite             启用并实际采集后才创建
    tiktok/raw/...
    hackernews/hackernews.sqlite     同上，可选
  analysis.sqlite
```

RSS 和固定 URL 分开；小红书、Twitter、TikTok 互不混库。平台未启用时不创建其业务数据库，也不发送请求。源库统一使用 `scripts/source_schema.sql`，分析库使用 `scripts/analysis_schema.sql`，新结构 schema 版本为 1。旧的 `library.sqlite` 与原始运行记录保持原样，不自动搬迁或删除。

## 每个来源库

| 表 | 一行代表什么 | 主要字段 / 约束 |
|---|---|---|
| source_meta | 这个库的来源类型 | platform、schema_version、created_at |
| materials | 一篇网页或一条平台帖子 | id、稳定 url、title、published、discovered_at、body_status、正文路径/哈希/方法/范围/版本 |
| observations | 某来源在一次返回里发现该材料 | material_id、source、source_item_id、observed_at、published、raw_path |
| body_versions | 某材料的一版正文 | material_id + version 唯一；sha256、path、method、scope、fetched_at |
| attempts | 一次正文读取或失败 | material_id、method、status、detail、raw_path、attempted_at |
| platform_items | 帖子的原生元数据 | material_id、platform_item_id 唯一、author、content_type、metrics_json、last_observed_at |
| runs | 一次代码采集执行 | command、起止时间、状态、摘要 |

正文按哈希存文件，数据库保存索引；旧正文和失败原件不覆盖。发布时间可能未知，不能用采集时间补造。重复采集保留各来源观察、更新最新互动指标，不覆盖已经验证的正文。

平台元数据不强塞进一套计数列：小红书 likes 可能是“2.3万”，TikTok 有 plays/shares，Twitter 有 views。`metrics_json` 保留平台原始值；缺失字段保持缺失，不把未知补成 0。`content_type` 区分文字帖子与 `video_description`；视频描述不是视频逐字稿。原始 JSON 始终另存，因此适配字段遗漏时仍可回查。

## 身份与去重

- 小红书：平台 + note ID。search_result / explore / discovery/item 三种路径归为同一篇；变化的 xsec_token 不参与身份。调用读帖时用代码手里的原始完整链接；数据库材料 URL 和模型快照只保留无临时参数的公开链接。
- Twitter：平台 +帖子 ID；TikTok：平台 + video ID。作者名、搜索词和短期访问参数变化不产生新材料。
- RSS / URL：规范化 URL，去 fragment/utm 等追踪项，保留其他语义参数；不自动跨协议或跨站合并。
- 同一网址同时出现在 RSS 与 URL 库时保留各自来源事实。分析快照按唯一材料 ID 合并相同 URL 的重复项，保留来源库指针；主题相近但 URL 不同的交给日报归并。

## 独立分析库

| 表 | 作用 |
|---|---|
| stage_runs | 每次筛选/日报执行：阶段、CLI、输入哈希、context 哈希、筛选输出哈希、输出哈希、完成时间 |
| scores | 每批逐条评分：材料 ID、平台、正文哈希、1–5 分或 null、keep/exclude/pending、理由、原文短引、限制 |
| processed | 成功日报之后的处理状态：材料 ID + context 哈希 + 正文哈希 → 报告运行与筛选结论 |

筛选成功只写 scores，不立刻把材料标为已处理。日报校验成功才更新 processed；日报失败可以用同一筛选结果续跑。pending 不标完成。context 或正文版本变化，会再次进入待处理范围；只修改排序或互动数字不会触发重新报道。评分规则变化也应重新筛选：快照处理键包含有效评分规则哈希。

`runs/<批次>/input.json` 汇总本次待处理材料，带 platform/source_db/原件引用；临时访问参数不发给模型。`filter/model.json` 与回执绑定精确输入和 context，日报入口拒绝错误快照、被改动的筛选清单或过期评分规则。跨库不设置外键，依赖快照中的材料 ID、来源库指针、正文哈希回查；分析库内部执行外键约束。

所有 SQLite、原件、快照、CLI 日志和真实日报都在 `.gitignore` 中；GitHub 只放建表 SQL、代码、共享配置、虚构 context、Skill 与经检查的少量演示文件。
