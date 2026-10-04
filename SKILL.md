---
name: turn-anything-cu
description: Connect the local ChatGPT Computer Use component to the user's chosen AI client on macOS. Discover that client's MCP installation method, register and verify the server, or repair/uninstall this integration. Requires a client capable of running local stdio MCP servers; does not provide a model or free inference.
---

# Turn anything into Computer Use

You are the installation agent. Discover where the **target AI client** registers MCP servers instead of assuming Claude paths. `REPO` is the directory containing this file. This project reuses the locally installed OpenAI component; it does not distribute that component. Keep all configuration inspection local and avoid exposing credentials.

## Discover the target and installation method

Use the user's named client; otherwise use the current host when its identity is reliably available. Do not equate the model name with the client application. If the target is still ambiguous, ask one question about which app they want to use.

Inspect the target client's local help, documented configuration and existing MCP settings. If necessary consult its current official docs. Establish:

- Whether it can launch a **local stdio MCP server**, and which user/project scope the user intends. Prefer user scope for this machine-local integration unless instructed otherwise.
- Its supported registration command or exact config path and schema. Prefer its native MCP registration CLI/API. Do not scan arbitrary credential files or configure every installed AI app.
- How it handles MCP elicitation (the component's per-app permission questions). Generic tool confirmation is not a substitute for these questions.

Do not invent a path, registry section, or format. A client limited to remote HTTP MCP cannot directly run this server. If discovery fails, report the missing capability or ask for the client/config location; do not write a guessed config.

## Locate the local component

Check macOS, Python 3, and the installed Computer Use component. Run:

```bash
python3 REPO/install.py
```

This only prints a portable server descriptor (`command`, `args`, `env`). It finds the newest component in `$CODEX_HOME/plugins/cache/openai-bundled/unified-computer-use/`, defaulting to `~/.codex`. It does not run the component or change client settings. Treat the descriptor as local configuration, not material to upload.

If missing, ask the user to install/enable Computer Use in ChatGPT/Codex and use it once. macOS Screen Recording and Accessibility permissions must be granted by the user. If the component moved, discover its actual `.mcp.json` and use `--source /verified/path/.mcp.json`; do not download replacement binaries from unrelated sources.

The generated descriptor requests analytics off and desktop-app surfaces only. Preserve its environment entries, executable path and argument boundaries. Do not claim that these switches prove zero network traffic or guarantee free-account access.

## Install for the discovered client

Briefly explain the destination and scope, and that screenshots/window text reach the chosen model. An explicit installation request authorizes normal registration; do not add automatic approval without the user's choice.

Use one of these methods:

1. **Native registration**: pass the descriptor fields through the client's documented command/API. Adapt only schema differences verified for this client (for example whether `type: stdio` is required). Back up an existing entry before replacement; preserve unrelated settings.
2. **Strict JSON config**: the script can merge a `ccu` entry into a verified server map. Preview first, then apply within the user's installation authorization:

   ```bash
   python3 REPO/install.py --config /verified/config.json --section mcpServers
   python3 REPO/install.py --config /verified/config.json --section mcpServers --apply
   ```

   `--section` takes successive object keys, e.g. `--section integrations mcpServers`. This example is not a claim about any particular client's schema. Add `--stdio-type` only if required. Conflicting entries require inspection and `--replace`. The writer backs up existing files and preserves unrelated data, though JSON whitespace is normalized.
3. **Other formats (TOML, JSONC, YAML, etc.)**: use the native registration method or a format-aware targeted edit with backup. Do not pass these files to the strict JSON writer, strip comments, or overwrite the entire config. Keep the same descriptor fields and verify the result using the client's own parser/list command.
4. **Claude Code compatibility adapter**: `python3 REPO/install.py --client claude` previews; add `--apply` to install. The adapter keeps the legacy tool name `ccu`. This is the only route allowed to change Claude's files. If an existing `ccu` entry differs, inspect/back it up before proceeding.

### App approval is client-specific

Preserve the target client's permission mechanism and test it. If it cannot handle the component's elicitation, report that registration alone is insufficient. Do not silently auto-approve, disable safety prompts, or claim compatibility.

For **Claude Code only**, explain and offer the existing optional `--auto-approve` hook. It approves per-app requests except apps in `ccu-denylist.txt`; it does not approve audio recording. Review the app block list with the user before enabling it. `--always-allow` additionally skips Claude's outer tool confirmation and also requires explicit user choice. Keep asking by default; avoid bypass-permissions mode. Neither flag applies to other clients, and their app accesses are not protected by this repository's block list.

## Verify, repair, remove

Reload/restart only the target client as needed. Verify separately:

1. The client lists `ccu` and loads its tool schema.
2. An app authorization question can be answered through the client's supported mechanism (or the user-selected Claude hook).
3. At the user's request, open TextEdit, create a **new** document and type a harmless test line. Do not type into an existing document or send/publish anything. Read the tool's returned API documentation before calling its computer-use APIs.

Report the target, config destination, scope and actual verification result. Say when restart or a user-granted macOS permission still prevents end-to-end verification. Do not call an untested client supported.

For updates, regenerate the descriptor after ChatGPT changes component paths and update only the target entry. To remove, prefer the same native registration method; the JSON route supports `--uninstall --apply` with the same path/section, and Claude supports `--client claude --uninstall --apply`. Do not remove shared OpenAI components or other MCP servers. Rollback uses the backup created before editing.
