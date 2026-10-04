<h1 align="center">turn-anything-cu</h1>

<p align="center">Let your AI client use your Mac through the locally installed Computer Use component.<br>让安装的 AI 自己找到 MCP 应该装在哪里，再接上 Mac 的 Computer Use。</p>

<p align="center">macOS · local stdio MCP · AI-guided setup · MIT</p>

## 中文

这个仓库提供安装 skill 和配置脚本，把 ChatGPT/Codex 已安装的 Computer Use 组件接给你选择的 AI 客户端。AI 负责理解任务，Computer Use 负责读屏幕、点击和输入；仓库不包含 OpenAI 的组件，也不提供模型。

### 一句话安装

先在 Mac 上安装并启用 ChatGPT/Codex 的 Computer Use，使用一次并完成系统权限授权。然后把这句话交给要使用的 AI 客户端：

```text
把 https://github.com/kk1992ishere-droid/turn-anything-cu 克隆到合适的本地工具目录，阅读 SKILL.md。识别我当前使用的 AI 客户端，依据它的本地帮助或官方文档找到正确的 MCP 注册方式、配置位置和格式，然后安装并验证 Computer Use。不要默认安装到 Claude 目录；保留其他配置，保持正常授权提示。
```

不需要先知道 skill 应该放在哪个目录；AI 可以直接阅读克隆后的 SKILL.md。只有确实需要可重复调用的 skill，才按目标客户端的规范安装该 skill。

### 支持范围

- 安装 AI 自行发现目标客户端的配置路径、作用域和格式；脚本不硬编码一张客户端目录表。
- 通用路径要求客户端能运行 **本地 stdio MCP**，并能处理组件发出的应用授权请求。仅支持远程 HTTP MCP 的客户端不能直接接入。
- 提供通用配置导出、严格 JSON 合并，以及现有 Claude Code 专用适配器。TOML、JSONC 等格式交给客户端原生注册命令或 AI 的格式感知编辑。
- “通用安装”不代表所有 AI 已通过实测。其他客户端需要逐一验证工具加载、应用授权和实际操作；模型名称也不等于客户端名称。
- 当前仓库仅针对 macOS。只使用 Codex 原生 Computer Use 的用户通常不需要这个仓库。

### 脚本用法

```bash
# 仅导出 command / args / env，不修改任何客户端
python3 install.py

# AI 已核实配置文件和 server map 后：先预览，再写入
python3 install.py --config /verified/config.json --section mcpServers
python3 install.py --config /verified/config.json --section mcpServers --apply

# 如果客户端要求 type: stdio，再添加 --stdio-type
# 嵌套 server map 用多个 key：--section integrations mcpServers
# 已核实的组件位置可用 --source /verified/component/.mcp.json 覆盖

# Claude Code 专用；默认保留正常授权，不自动批准
python3 install.py --client claude --apply

# 卸载相同 JSON 位置中的 ccu
python3 install.py --config /verified/config.json --section mcpServers --uninstall --apply
# 卸载 Claude 适配
python3 install.py --client claude --uninstall --apply
```

通用 JSON 写入会备份旧文件、保留其他配置，并拒绝覆盖不同的 `ccu` 条目，除非显式使用 `--replace`。仅支持严格 JSON，不接受带注释的 JSONC 或 TOML；JSON 排版会被规范化。`ccu` 是保留的工具注册名。

**旧版迁移：** 不带参数现在只导出配置，不再安装到 Claude；旧的 Claude 安装方式请加 `--client claude --apply`。Claude 应用自动批准现在需要主动选择 `--auto-approve`，不再默认开启。

### 授权、隐私与费用

窗口文字和截图会交给你选择的 AI 模型。生成的配置设置 `NODE_REPL_DISABLE_ANALYTICS=1`，并通过 `CUA_REPL_ENABLED_SURFACES=computer` 请求仅开放桌面应用表面；这不是网络隔离或浏览器内容防泄漏保证。它依赖非官方复用的本地组件，更新后可能需要重新配置。

客户端必须能回答组件的应用授权请求，仅能确认“运行 MCP 工具”还不够。Claude 专用的可选 `--auto-approve` hook 会放行黑名单之外的应用；黑名单在 `~/.claude/hooks/ccu-denylist.txt`，决定日志在同目录的 `ccu-approvals.log`。`--always-allow` 还会跳过 Claude 的工具确认。这两项都应由用户明确选择；其他客户端不受这个 hook 或黑名单保护。

仓库脚本不调用 OpenAI 推理 API；执行任务的模型按其服务计费。不能据此保证任意免费账号可启用本地组件、完全零网络流量，或所有 AI 免费无限使用。

## English

An installation skill and configuration helper that connects the Computer Use component already installed by ChatGPT/Codex to your chosen AI client. The model plans; the local component reads and operates desktop apps. No OpenAI component or model is distributed here.

### Install with your AI

Enable Computer Use in ChatGPT/Codex on your Mac, use it once, and grant the requested macOS permissions. Then ask your chosen AI client:

```text
Clone https://github.com/kk1992ishere-droid/turn-anything-cu into a suitable local tools directory and read SKILL.md. Identify my current AI client, discover its documented MCP registration method, config location and schema, then install and verify Computer Use. Do not assume Claude paths. Preserve other settings and normal approval prompts.
```

The agent discovers the destination rather than relying on a hardcoded client list. The client must launch local stdio MCP servers and handle the component's app-access elicitation. Remote-only MCP clients cannot directly use it. Cross-client installation is a workflow, not a claim that every client has been tested.

`python3 install.py` exports `command`, `args`, and `env` without modifying settings. Prefer the target client's native registration command. For a verified strict JSON server map, use `--config PATH --section mcpServers`, review the preview, then add `--apply`. Nested maps use successive keys. Add `--stdio-type` only when required by the schema. TOML, JSONC and other formats need a native command or format-aware edit; the JSON writer does not support them.

The legacy Claude adapter is explicit: `--client claude --apply`. Unlike the old installer, no arguments no longer install into Claude, and app auto-approval is opt-in with `--auto-approve`. The optional `--always-allow` also skips Claude's outer tool confirmation. These flags and the app block list are Claude-only. Other clients need their own working approval mechanism.

JSON updates back up existing files, preserve unrelated data, normalize whitespace and require `--replace` for conflicting `ccu` entries. Use the same target flags with `--uninstall --apply` to remove the entry. After an OpenAI component update, regenerate the descriptor if its paths changed.

Screenshots and window text reach the chosen model. The descriptor requests analytics off and desktop-app surfaces only; these settings are not a network sandbox. The integration is unofficial and can break on updates. The installer makes no OpenAI inference calls, but model usage is billed by the selected provider. Free-account component access, zero network traffic and universally free use are not guaranteed.

---

MIT · Unofficial; not affiliated with Anthropic or OpenAI.
