# 可提交的小样例

- 输入原件为 `../fixtures/materials.json`。`fixture-selection.json`、`fixture-daily.md` 是现有认证 Codex CLI 真实输出的逐字副本；输入内容是虚构演练，不能当真实服务或真实工具使用经历。
- `fixture-selection-entertainment.json` 使用同一份离线快照与另一份虚构 context；技术/娱乐的 keep/exclude 反转，缺正文仍 pending。
- `public-source-index.json` 是最终 5 条公开材料的身份、正文哈希、method 与范围，不含整页转载。最终 SQLite 正文走 Crawl4AI，其余 4 篇走 Jina。
- `public-selection-provisional.json` 是早期快照上的真实模型筛选，供理解轨迹；其中 SQLite 当时还是误收的 HTML 源码。质量门已修复、原件已保留，但该清单不能作为最终清洗快照的已验证筛选。需要按 README 的最终命令重新筛选。
- `evidence.json` 只保存脱敏的实际运行状态、哈希、文件名和读取验证结论。完整 events/stderr、原始网页和数据库留在本机 ignored 目录；这些运行日志不应直接提交或对外分享。

样例是一次实际执行的冻结副本，不会随读者修改 context 自动变化。完整 CLI 调用、未满足项和语义检查见 `../docs/VALIDATION.md`。
