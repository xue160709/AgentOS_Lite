# AgentOS Lite

一个可复制的信息采集与日报 MVP，也是 S4/S5 教学示例。**Python 采集 → 分平台数据库 → CLI 筛选评分 Skill → CLI 日报 Skill → Markdown 日报**。没有前端，不自动发布。

采集和日报可分别运行；默认使用 Claude Code，保留 Codex。Python 3.11+ 标准库即可运行主流程，Crawl4AI 为可选正文后备。真实渠道与模型验证范围见 [验证记录](docs/VALIDATION.md)。

## 从新电脑开始

```bash
git clone https://github.com/xue160709/AgentOS_Lite.git
cd AgentOS_Lite
python3 --version
```

以下命令都在仓库根目录执行。Windows 如果没有 `python3` 命令，可将它替换为 `python` 或 `py -3`。

先准备三项环境：

1. **Python 3.11+**：主程序和无网络测试不用安装 pip 包。
2. **选择一个模型 CLI**：按 [Claude Code 安装与登录指南](https://code.claude.com/docs/en/quickstart) 或 [Codex CLI 指南](https://learn.chatgpt.com/docs/codex/cli) 安装并完成自己的正常认证；确保终端能找到 `claude` 或 `codex`。只需安装你要使用的一个。
3. **OpenCLI 与浏览器连接**：按 [OpenCLI 官方安装说明](https://github.com/jackwener/opencli#quick-start) 安装 CLI 和 Browser Bridge 扩展，保持浏览器与扩展可用，并由自己在小红书、X 网站正常登录。npm 安装方式如下（先满足官方 Node.js 版本要求）：

```bash
npm install -g @jackwener/opencli
opencli doctor
```

默认配置启用 RSS、SQLite 参考页、小红书、X。要完整复现四路采集，请按文末步骤安装自己的 Crawl4AI 正文后备；本机验证中 SQLite 页面需要这一级，不能假定 Reader 总会成功。暂时没有社交平台环境时，可在对应来源的本机覆盖文件中设 `enabled: false`，先运行 RSS/URL 子集；这不算社交平台已验证。

然后依次执行：

```bash
python3 -m unittest discover -s tests -v
python3 scripts/collect.py --preview --out runs/first/input.json
python3 scripts/daily.py --preview
python3 scripts/daily.py
# 若选择 Codex，最后一条改为：
# python3 scripts/daily.py --engine codex
```

成功时终端打印日报绝对路径，文件在 `reports/<批次>/daily/daily.md`。`daily.py` 手动执行不安装或启用定时任务。退出 2 表示已生成带采集缺口的日报，应查看本批次 input.json/job.log；退出 1 或其他非零码表示流程失败，不算完整跑通。

本机已实际跑过 **Claude Code 的两个独立 Skill**，以及 **Codex 的完整 daily.py 三阶段入口**：各处理 RSS 2 + URL 1 + Twitter 2 + 小红书 2，共 7 条有正文的材料并产出日报。同库复跑无新待处理内容时，两阶段都跳过模型。TikTok 默认关闭，Windows 调度尚未实机验证；详见 [验证记录](docs/VALIDATION.md)。

## 最小目录

```text
CLAUDE.md / AGENTS.md             两个工具的项目说明
.claude/skills/                   Claude Code：filter-materials / write-daily
.agents/skills/                   Codex：filter-materials / write-daily
config/
  sources/
    rss.json                     RSS 来源样例
    urls.json                    固定公开 URL 样例
    opencli/
      xiaohongshu.json            小红书公开搜索样例
      twitter.json               Twitter/X 公开搜索样例
      hackernews.json            可选 HN 样例，默认关闭
      tiktok.json                视频描述采集样例，默认关闭
  runtime.json                   CLI、模型、超时和正文参数
  scoring.json                   1–5 分刻度与保留门槛
  keywords.json                  历史教学关键词提示，不做语义筛选
context/
  profile.md                     用户背景
  interests.md                   关注的信息
  disinterests.md                 不关注的信息
  report.md                      日报用途和格式
scripts/
  collect.py                     采集与快照入口
  filter.py                      CLI 筛选评分入口
  generate.py                    CLI 日报入口（要求筛选清单）
  skill_runner.py                两阶段共用 CLI 调用与校验
  contracts.py                   输出契约、版本绑定与引用校验
  storage.py                     分库存储与分析记录
  daily.py                       组合入口，供定时任务调用
  sources.py                     配置读取与只读 OpenCLI 适配
  lite.py / schema.sql           原件、SQLite、正文与旧手动命令
  source_schema.sql              每个平台的采集库结构
  analysis_schema.sql            独立分析库结构
  crawl_body.py                  可选 Crawl4AI 后备
  schedule_macos.py
  schedule_windows.ps1
runs/                            独立采集/生成的本机产物，不提交
reports/                         完整流程的快照、日志和日报，不提交
data/                            SQLite 与按哈希保存的原件，不提交
```

`docs/filter-workflow.md` 与 `docs/daily-workflow.md` 分别是两种 CLI 共用的筛选评分、日报写作规则。`tests/` 与 `fixtures/` 只用于开发检查和离线演练，不是日常业务步骤。日常使用 collect.py、filter.py、generate.py，或直接运行组合入口 daily.py；不再提供旧版 run_skills.py 执行入口。

## 1. 修改公开配置与偏好

共享 `config/` 和 `context/` 是项目的一部分，**应该上传 GitHub**。当前 context 是虚构图书馆读者，可替换。只填写愿意公开的信息；不要把 cookie、token、浏览器配置或密码放进去。

来源按类型分文件。每项含唯一 `id` 与布尔 `enabled`：

- `rss.json`：公开 Feed URL、每源数量；样例启用 Python 官方博客 2 条。
- `urls.json`：固定页面 URL 和标题；样例启用 SQLite 官方参考页。
- `opencli/xiaohongshu.json`：`search` 关键词、排序、时间范围、数量，样例为“Python 自动化”2 条。
- `opencli/twitter.json`：`search` 查询表达式、搜索页类型、数量，样例为“Python RSS”2 条。

小红书先搜索再读取少量笔记文字；Twitter 使用返回的帖子文本。不转写图片/视频，不抓私信、私有账号、创作者后台或个性化信息流。平台只返回标题或没有足够文字时保留 pending；零搜索结果合法。搜索时间过滤是平台行为，不证明返回材料都是当天发布。

OpenCLI 需要已有正常连接的 Browser Bridge 与平台登录状态。本项目不复制登录态、不自动登录或改权限。先在自己的环境中核对版本和只读命令：

```bash
opencli --version
opencli xiaohongshu search --help -f json
opencli twitter search --help -f json
claude --version
# 使用 Codex 时：
codex --version
```

`runtime.json` 默认 `engine: "claude"`，`model: null` 沿用对应 CLI 的现有模型；切换 Codex 可用命令参数。不要把只适用于自己网关的模型 ID 写进共享配置。超时默认 600 秒；正文最多补 10 条。没有正文时按缓存 → Jina Reader → 可选 Crawl4AI 尝试，失败原样记录，不无限重试。社交平台文字使用其自己的适配器，不把带访问参数的社交 URL 发给 Reader。

仅使用少量公开且审阅过的 URL；显式本地地址和带账号密码的 URL 会拒绝，URL 检查不是完整网络安全边界。外部材料里的命令和提示都不是项目指令。

## 2. 分别运行采集与日报

只预览来源，不请求网络或模型：

```bash
python3 scripts/collect.py --preview --out runs/demo/input.json
```

实际采集：

```bash
python3 scripts/collect.py --out runs/demo/input.json
```

先通过 Claude Code CLI 调用筛选评分 Skill，再调用日报 Skill：

```bash
python3 scripts/filter.py --input runs/demo/input.json --out runs/demo/filter
python3 scripts/generate.py --input runs/demo/input.json --selection runs/demo/filter/model.json --out runs/demo/claude-daily
```

筛选逐条输出 1–5 分、理由、原文短引与 keep/exclude/pending；默认 3 分及以上保留。缺正文为 pending，score=null。评分衡量读者相关性，不等于事实可信度。日报只读 keep 材料，不重新评分。

同一快照也可交给 Codex：

```bash
python3 scripts/filter.py --engine codex --input runs/demo/input.json --out runs/demo/codex-filter
python3 scripts/generate.py --engine codex --input runs/demo/input.json --selection runs/demo/codex-filter/model.json --out runs/demo/codex-daily
```

输出目录必须是新的目录，不覆盖旧日报；重新采集也请使用新批次路径。CLI 使用已有认证，真正调用模型并消耗对应额度。Claude 模型只提供 Read 工具；Codex 使用只读 sandbox。每个 Skill 各调用一次 CLI；外层脚本分别保存 filter/model.json、daily/model.json、daily.md 和运行回执，检查材料 ID、评分门槛、原文短引、原链接与输入/context/评分规则版本绑定。机器通过不等于摘要语义完全正确。

日报成功后才记录 keep/exclude 为已处理，筛选成功但日报失败时可直接续写。下次快照只包含当前 context/评分规则下尚未处理的正文版本，pending 继续待补。平台按帖子 ID 去重，网页按 URL 去重；不会自动刷新同一 URL 的正文。快照可能含旧材料，日报必须注明来源时间，不声称是当日全网新闻。无新材料时写明情况，不为凑日报调用模型。

单个渠道失败不丢弃其他渠道结果；部分采集的退出码为 2，日报会注明缺口。所有已启用渠道失败则退出 1，组合流程不调用模型。正常无新内容退出 0。失败与无更新不是一回事。

## 3. 完整运行与定时任务

```bash
python3 scripts/daily.py --preview
python3 scripts/daily.py
# 或：
python3 scripts/daily.py --engine codex
```

结果位于 `reports/<批次>/daily/daily.md`；同批次保留 `input.json`、`filter/model.json` 和两阶段日志。一次定时任务调用 daily.py 即可，采集和生成不需要分别注册任务。

每天本地时间 08:00 的配置准备命令：

```bash
python3 scripts/schedule_macos.py --at 08:00
```

```powershell
.\scripts\schedule_windows.ps1 -At '08:00'
```

默认只生成配置。你明确决定启用后，才自行加 `--install`（macOS）或 `-Install`（Windows）。先在同一用户环境完整手动跑通，确保 Python、CLI、平台 Browser Bridge、现有模型连接在定时时仍可用。Windows 尚需实机验证；配置生成不等于定时触发已验证。

## 分平台存储

数据库格式见 [存储设计](docs/STORAGE.md)。采集只写本来源库，模型结果另存分析库：

```text
data/daily/
  sources/rss/rss.sqlite
  sources/urls/urls.sqlite
  sources/xiaohongshu/xiaohongshu.sqlite
  sources/twitter/twitter.sqlite
  sources/tiktok/tiktok.sqlite       启用采集后才创建
  analysis.sqlite                   评分、日报运行与处理状态
```

各平台目录有自己的 raw/ 与采集回执。小红书读帖所需临时参数只在本机代码与原始响应中使用，不进入模型输入；按 note ID 去重，避免每次搜索签名变化造成重复。TikTok 当前只支持搜索返回的视频描述，不代表已读视频或完成转写；共享样例默认关闭，本轮不把它计入真实平台验收。

旧 library.sqlite、原件和历史运行不自动迁移或删除；新入口在 sources/ 下建立独立平台库。改读者偏好或评分门槛后，新快照会重新筛选对应材料。

## GitHub 提交边界与个人覆盖

**提交：**源码、依赖声明、共享配置、虚构 context、CLAUDE.md、AGENTS.md、两个工具的项目 Skill、测试/fixture，以及经检查的少量样例与文档。

**忽略：**data/、runs/、reports/、outputs/；虚拟环境、缓存、数据库、日志；`.env*`、密钥、cookie、浏览器会话；本机 CLI 设置与个人覆盖。不会把 `.claude/` 整体忽略，否则别人拿不到 Skill。

个人使用无需修改共享模板：

- 在同级建立 `rss.local.json`、`urls.local.json`、`twitter.local.json` 或 `runtime.local.json`，会**完整替换**对应共享文件，不是字段合并；均被忽略。
- 个人偏好放 `context/local/`，需要提供完整四份 Markdown。日报入口优先读取它；没有时使用共享 context。也可用 generate.py 的 `--context` 显式指定。
- 不要把浏览器返回的带临时访问参数的链接复制进共享 config；真实返回只留在被忽略的原件与日报里。

`.gitignore` 不会撤销已被 Git 跟踪的文件。提交前仍需逐项查看差异，确认没有把私人偏好填进共享 context；不要用 `git add .` 混入其他会话修改。

## 开发与历史证据

```bash
python3 -m unittest discover -s tests -v
python3 scripts/lite.py --home data/classroom fixture
python3 scripts/lite.py --home data/classroom export --out outputs/classroom-input.json
```

离线 fixture 是虚构材料，不冒充真实采集，也不生成伪造模型结果。当前验证范围见 [验证记录](docs/VALIDATION.md)，教学动作见 [教学素材](docs/MATERIALS.md)，参考来源见 [来源与参考](docs/REFERENCE.md)。早期冻结的模型输出与历史运行证据不再随源码分发，已有本机文件保留，Git 历史也可回查。

## 配置自己的 Crawl4AI 后备

macOS / Linux：

```bash
python3 -m venv .venv-crawl
.venv-crawl/bin/python -m pip install -r requirements-crawl.txt
.venv-crawl/bin/python -m playwright install chromium
cp config/runtime.json config/runtime.local.json
```

Windows PowerShell：

```powershell
python -m venv .venv-crawl
.\.venv-crawl\Scripts\python.exe -m pip install -r requirements-crawl.txt
.\.venv-crawl\Scripts\python.exe -m playwright install chromium
Copy-Item config/runtime.json config/runtime.local.json
```

以上复制命令只用于尚无本机覆盖配置的首次安装，已有文件时直接编辑它。打开 `config/runtime.local.json`，保留其他字段，将 `crawl_python` 设为自己的虚拟环境 Python **绝对路径**（macOS/Linux 的 `.venv-crawl/bin/python`，Windows 的 `.venv-crawl\Scripts\python.exe`；JSON 中 Windows 反斜杠需写作 `\\`）。不要复制维护者的机器路径，也不需要其他 AgentOS 仓库。

未安装后备不影响 RSS/平台已有正文的使用；需要后备而缺依赖时会明确失败。若依赖安装不支持当前 Python 版本，请使用该依赖支持的 Python 创建隔离环境，主程序不必更换解释器。
