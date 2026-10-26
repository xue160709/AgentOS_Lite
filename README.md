# AgentOS Lite

S4 / S5 共用的最小教学项目：**脚本采集 → SQLite 与原件 → Codex Skill 筛选 → Codex Skill 日报**。Python 3.11+、标准库即可完成离线演练与 RSS/Jina 采集。没有前端、定时任务或生产账号。

`context/` 是虚构的社区图书馆读者偏好。关键词只给确定性提示；采集不是 Skill；筛选与日报才是 `.agents/skills/` 下的两个 Skill。代码能运行与内容教学验收分开，真实验证范围见 [验证记录](docs/VALIDATION.md)。

## 从离线样例开始

在仓库根目录运行；`--home` 使不同演练相互隔离。fixture 是虚构材料，离线命令不需要登录或网络，也不生成伪造模型输出。

```bash
python3 -m unittest discover -s tests -v
python3 scripts/lite.py --home data/classroom fixture
python3 scripts/lite.py --home data/classroom bodies --offline
python3 scripts/lite.py --home data/classroom fixture
python3 scripts/lite.py --home data/classroom status
python3 scripts/lite.py --home data/classroom export --out outputs/classroom-input.json
```

预期：首次 new=3，正文检查 reused=2、pending=1；重复导入 duplicate=3。`--offline` 只检查缓存，不给缺正文项发网络请求。`fixtures/materials.json` 可编辑。离线阶段没有语义筛选，等待下面的真实模型运行。

## 编辑输入，再少量真实采集

先修改 `context/{interests,disinterests,report}.md`，再改 `config/rss.json` 和 `config/keywords.json`。RSS 每源 1–10 条，默认只启用 Python 官方博客 2 条。支持 RSS 2.0 和 Atom；description/summary 仅保存为元数据，content:encoded/Atom content 经质量检查才可复用，范围为 `feed_claimed_full`，不是本项目独立证明的全文。

```bash
python3 scripts/lite.py --home data/public rss
python3 scripts/lite.py --home data/public add https://www.sqlite.org/whentouse.html --title 'Appropriate Uses For SQLite (official reference)'
python3 scripts/lite.py --home data/public queue
opencli hackernews --help -f json
python3 scripts/lite.py --home data/public opencli --feed top --limit 2
python3 scripts/lite.py --home data/public bodies --limit 3
python3 scripts/lite.py --home data/public export --out outputs/public-input.json
```

OpenCLI 是可选外部 CLI，用已有安装与正常连接。本版仅允许 `hackernews top/newest` 的只读调用（1–5 条），以本机 help 核实；原始 stdout/stderr 归档。失败会记回执，不改登录、权限或账号。没有安装时同样保留 FileNotFoundError。

正文顺序：已有正文（哈希+质量复核）→ Jina Reader → Crawl4AI，成功即停止。每级一次请求（重定向最多 5 跳），网络每次 20 秒，Crawl4AI 总进程 45 秒；没有自动无限重试。重试只由用户明确运行：

```bash
python3 scripts/lite.py --home data/public bodies --retry --limit 3
python3 scripts/lite.py --home data/public bodies --id MATERIAL_ID --refresh
```

只有需要补正文才启动 Crawl4AI。可选安装到自己的隔离环境：`python3 -m venv .venv-crawl`，再用 `.venv-crawl/bin/pip install -r requirements-crawl.txt` 和 `.venv-crawl/bin/python -m playwright install chromium`；调用 bodies 时加 `--crawl-python .venv-crawl/bin/python`。不安装也能运行其他步骤，缺依赖明确记失败。本机验证可复用已有 Crawl4AI 运行时，具体见验证记录。

正文状态 `missing/ok/failed/refresh_failed`；失败项不删除，旧版本不覆盖。验证码、登录、付费墙、错误页或正文不足不能当全文。质量门是保守启发式，可能误判，正文范围统一注明提取未独立核验；可查看 attempts 原始响应。`--refresh` 显式取新版本；本版不会自动根据源更新探测网页变化。

仅使用审阅过的公开 URL。拒绝显式本地地址和带凭据 URL，URL 检查不是网络安全边界；本机代理可合成 DNS，因此不按 DNS 返回的代理地址误判目标。Crawl4AI 使用独立无登录浏览器，不绕验证。

## 用真实 Codex CLI 执行两个 Skill

先核 `codex --version`、`codex exec --help`。使用已经正常认证的 CLI，不读取或复制密钥，不新建凭据；若模型/连接不可用，保留 failed 回执。以下命令会真正调用模型，可能消耗已有额度。

```bash
python3 scripts/run_skills.py filter --input outputs/classroom-input.json --out runs/classroom-filter
python3 scripts/run_skills.py daily --input outputs/classroom-input.json --selection runs/classroom-filter/model.json --out runs/classroom-daily
```

实采同理，把 input 换成 `outputs/public-input.json`、out 换成新目录。out 必须不存在，以免覆盖上次结果。外层脚本使用 `codex exec --sandbox read-only --json --output-schema -o`，显式 `$filter-materials` / `$write-daily`；模型只读项目 Skill、context 和输入，外层脚本保存输出。`events.jsonl` 应能看到实际读 Skill/context 的工具调用，`receipt.json` 有文件哈希、命令和结束状态；新运行还校验 Skill/context 全文在已完成工具输出中出现；不能只看模型说“已读取”。

筛选输出 `model.json` 覆盖每个 ID 一次、含 keep/exclude/pending、理由、原文短引和限制，验证后写入 decisions 表。日报输出 `daily.md` 与 JSON，校验 keep ID、原链接和 context 哈希。context 改了必须重新筛选；日报与输入必须使用同一快照。日报还会检查筛选运行回执的输入哈希，筛选结果缺少输出哈希或被改动也会拒绝。机器校验不证明摘要语义正确，仍须对照原文审稿。

## 目录与追溯

| 路径 | 内容 |
|---|---|
| `scripts/lite.py` / `schema.sql` | 采集、确定性提示、队列、正文、状态、建表；SQL 不做语义筛选 |
| `scripts/run_skills.py` | Codex 真实执行、schema/短引/ID/上下文验证、决策入库 |
| `.agents/skills/` | 两个独立语义 Skill |
| `config/` / `context/` | 公开来源、关键词、虚构读者 |
| `fixtures/` / `tests/` | 固定演练与无网络行为测试 |
| `data/<批次>/library.sqlite` | materials、observations、body_versions、attempts、queue、runs、decisions |
| `data/<批次>/raw/` | 按 SHA256 命名的原始返回与正文，成功正文不可覆盖 |
| `data/<批次>/receipts/` | 每次命令成功/失败/partial；零新增与请求失败分开，failed/partial 命令非零退出 |
| `outputs/` / `runs/` | 输入快照与真实模型输出/日志，默认忽略 |
| `docs/REFERENCE.md` | 参考来源、许可、简化依据与官方资料 |
| `docs/VALIDATION.md` / `docs/MATERIALS.md` | 实际证据范围和教学取材点 |
| `examples/` | 经检查可提交的少量输入/输出样例，不含原始网页大段全文 |

观察时间、来源声明的发布时间与正文抓取时间分开保存；不把未知时间填成今天。重复 URL 只存一个材料，但保留各来源 observations。规范化去 fragment/utm，不擅自合并协议、查询参数或不同路径。原件与失败响应保留；本版无自动清理功能。`data/`、`outputs/`、`runs/`、`.env*` 都不提交，避免把未来真实读者资料或大段网页误上传。

数据库查看示例：

```bash
sqlite3 -header -column data/classroom/library.sqlite 'select id,title,body_status,body_method,body_version from materials;'
sqlite3 -header -column data/classroom/library.sqlite 'select method,status,detail from attempts;'
```

从全新目录可复现离线部分；真实来源内容会变化，读取失败也是合法结果。没有实现线上日报归档、定时调度或课程母稿批量修改。

## 本轮服务缺口与续跑

本机离线双 Skill 已经真实完成。公开日报的两次调用遇到 429；审查还修复了 SQLite 的 Reader 返回整页 HTML 的质量误判，最终正文已由 Crawl4AI 补齐。旧公开筛选只对应旧快照，最终公开筛选/日报仍 pending。服务恢复后使用不存在的新输出目录串行运行：

```bash
python3 scripts/run_skills.py filter --input outputs/public-current-input.json --out runs/public-final-filter
python3 scripts/run_skills.py daily --input outputs/public-current-input.json --selection runs/public-final-filter/model.json --out runs/public-final-daily
```

这些路径是本机最终快照；全新电脑应先按上文采集并 export 自己的输入。完整失败记录、另一份 context 对照续跑命令、语义审查和证据边界见 [验证记录](docs/VALIDATION.md)。
