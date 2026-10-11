# browser-task-router

一个统一的浏览器 / 接口自动化 Skill。装完之后，你的 Agent 就能直接用下面这些能力，不需要每次再挑工具：

| 能力 | 说明 |
| --- | --- |
| **WebCLI** | 在已登录的真实浏览器里调用站点自己的 HTTP 接口。**接口优先**的主力，能调接口就不点页面 |
| **腾讯 BrowserSkill** | 接管一个可观察的浏览器会话，适合人工接管、边看边做 |
| **Browser-Use** | 探索未知站点、多步导航、脚本化操作 |
| **Browser-Act** | Skill 驱动的浏览器动作，支持本地 / 远程模式 |
| **Playwright CLI / MCP** | 确定性 UI 测试、tracing、网络分析、给 MCP 客户端用 |

核心思路：**能用接口就用接口**。页面本身就是在渲染站点请求回来的数据，直接调同一个接口，拿到的是
结构化数据、稳定的字段和可批量处理的空间；点页面只留给登录、探索和确实没有接口的场景。

## 安装

```bash
git clone https://github.com/ctzlyj/browser-task-router.git
cd browser-task-router
python scripts/setup.py          # 探测已装工具，生成 runtime.json，注册本地别名
python scripts/toolbox.py status # 看每个能力是 installed 还是 missing
```

把仓库（或其中的 `SKILL.md`）放到你的 Agent 的 skill 目录即可。`agents/openai.yaml` 已经打开隐式调用，
Agent 遇到浏览器 / 接口自动化任务会自己加载。

`missing` 的不是错误，只是没装。按 `references/providers.md` 里的上游链接装好，再跑一次：

```bash
python scripts/setup.py --force
```

## 用法

`scripts/toolbox.py` 是所有工具的同一个入口，保证参数不被 shell 吞掉、输出不丢、退出码可信：

```bash
python scripts/toolbox.py status
python scripts/toolbox.py run webcli -- list
python scripts/toolbox.py run playwright-cli -- -s=demo open https://example.com
python scripts/toolbox.py browser-endpoint
```

接口优先的调用方式（在页面上下文里发请求，自动带上页面自己的会话）：

```bash
python scripts/toolbox.py eval-url --with webcli --url "https://example.com/api/list?page=1"
python scripts/toolbox.py eval-url --with webcli --code "return document.title"
```

## 目录

```text
SKILL.md                      # 给 Agent 的主入口
scripts/toolbox.py            # status / run / eval-url / sync-file
scripts/setup.py              # 探测工具、生成配置、注册别名
references/                   # 每个工具的用法，以及 providers.md、maintenance.md
docs/interface-first.md       # 接口优先自动化的做法
docs/routing-scenarios.md     # 路由验收提示词
tests/                        # 单元测试
```

## 配置在哪

`setup.py` 把配置写到 `<配置目录>/browser-task-router/runtime.json`（Windows 是 `%APPDATA%`，其他平台是
`$XDG_CONFIG_HOME` 或 `~/.config`），并把 `*-local` 别名合并进 `~/.browser-task-router/local_cli.json`，
不碰里面已有的其他条目。可以用 `BROWSER_TOOLBOX_CONFIG` 或 `--config` 覆盖。

## 设计取向

- **工具箱，不是白名单。** 现有能力不够时，Agent 可以自己写任务内的脚本或换工具。
- **不设审批门。** 工具选择、切换、诊断和恢复不需要额外确认；只在身份、权限或真的走不通时才问。
- **不吞参数、不丢输出。** 统一走原生 argv，退出码原样透传。
- **写入结果未知时先对账。** 超时或响应丢失后先读远端状态和回执，再决定是否重试；换工具不等于可以重放。
- **凭证不进代码。** Cookie、Token、账号凭证不要写进脚本、日志、文档、截图或提交里。

## 测试

```bash
python -m unittest discover -s tests -v
```

## 许可

MIT，见 [LICENSE](LICENSE)。上游工具各自遵循其自身许可。
