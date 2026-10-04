#!/usr/bin/env python3
"""Export Computer Use MCP settings, or install into an AI-discovered JSON config.

No arguments only prints a portable stdio server descriptor; it changes nothing.
Use --help for JSON preview/apply and the explicit Claude Code adapter.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import tempfile
import stat

NAME = "ccu"
HOME = os.path.expanduser("~")
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_GLOB = os.path.join(os.environ.get("CODEX_HOME", os.path.join(HOME, ".codex")), "plugins/cache/openai-bundled/unified-computer-use/*/.mcp.json")
CLAUDE_JSON = os.path.join(HOME, ".claude.json")
SETTINGS = os.path.join(HOME, ".claude/settings.json")
HOOK_DIR = os.path.join(HOME, ".claude/hooks")
HOOK_FILE = os.path.join(HOOK_DIR, "ccu-approve.py")
DENYLIST_FILE = os.path.join(HOOK_DIR, "ccu-denylist.txt")
HOOK_CMD = "python3 ~/.claude/hooks/ccu-approve.py"
ALLOW_RULE = "mcp__ccu"

ENV_OVERRIDES = {
    "NODE_REPL_DISABLE_ANALYTICS": "1",       # no usage events + account lookup sent to chatgpt.com
    "CUA_REPL_ENABLED_SURFACES": "computer",  # desktop apps only; no control of your Chrome
}


def load(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    path = os.path.abspath(os.path.expanduser(path))
    # Do not replace symlinks (or silently edit their targets).
    if os.path.islink(path):
        raise ValueError("Config is a symlink; use its verified real path explicitly.")
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    mode = stat.S_IMODE(os.stat(path).st_mode) if os.path.exists(path) else 0o600
    if os.path.exists(path):
        backup = f"{path}.bak-{time.time_ns()}"
        shutil.copy2(path, backup)
        os.chmod(backup, 0o600)
    fd, tmp = tempfile.mkstemp(prefix=".cu-config-", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def version_key(path):
    version = os.path.basename(os.path.dirname(path))
    return tuple(int(x) if x.isdigit() else 0 for x in version.split("."))


def server_config(source=None):
    found = [os.path.abspath(os.path.expanduser(source))] if source else sorted(glob.glob(PLUGIN_GLOB), key=version_key)
    if not found:
        sys.exit("Computer Use not found. Install the ChatGPT desktop app and turn on Computer Use in Codex first.")
    src = load(found[-1])["mcpServers"]["cua_repl"]
    env = {**src.get("env", {}), **ENV_OVERRIDES}
    if not isinstance(src.get("command"), str) or not src["command"]:
        raise ValueError("Source MCP server needs a command string.")
    args = src.get("args", [])
    if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
        raise ValueError("Source MCP args must be a list of strings.")
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
        raise ValueError("Source MCP env must contain string values.")
    return {"command": src["command"], "args": args, "env": env}


def register(server):
    if shutil.which("claude"):
        subprocess.run(["claude", "mcp", "remove", NAME, "-s", "user"], capture_output=True)
        subprocess.run(["claude", "mcp", "add-json", NAME, json.dumps(server), "-s", "user"], check=True)
        return
    # No `claude` on PATH (e.g. desktop app only): write the user-scope entry directly.
    data = load(CLAUDE_JSON)
    data.setdefault("mcpServers", {})[NAME] = server
    save(CLAUDE_JSON, data)


def unregister():
    if shutil.which("claude"):
        subprocess.run(["claude", "mcp", "remove", NAME, "-s", "user"], capture_output=True)
        return
    data = load(CLAUDE_JSON)
    if NAME in data.get("mcpServers", {}):
        del data["mcpServers"][NAME]
        save(CLAUDE_JSON, data)


def update_settings(hook, allow):
    settings = load(SETTINGS)
    before = json.dumps(settings, sort_keys=True)

    hooks = settings.setdefault("hooks", {})
    entries = [e for e in hooks.get("Elicitation", []) if e.get("matcher") != NAME]
    if hook:
        entries.append({"matcher": NAME, "hooks": [{"type": "command", "command": HOOK_CMD, "timeout": 10}]})
    hooks["Elicitation"] = entries
    if not entries:
        del hooks["Elicitation"]
    if not hooks:
        del settings["hooks"]

    perms = settings.setdefault("permissions", {})
    rules = [r for r in perms.get("allow", []) if r != ALLOW_RULE]
    if allow:
        rules.append(ALLOW_RULE)
    perms["allow"] = rules
    if not rules:
        del perms["allow"]
    if not perms:
        del settings["permissions"]

    if json.dumps(settings, sort_keys=True) != before:
        save(SETTINGS, settings)


def json_target(args, server):
    path = os.path.abspath(os.path.expanduser(args.config))
    data = load(path)
    if not isinstance(data, dict):
        raise ValueError("Target JSON must contain an object.")
    parent = data
    for key in args.section:
        if key not in parent:
            if args.uninstall:
                print("Already absent; no changes.")
                return
            parent[key] = {}
        parent = parent[key]
        if not isinstance(parent, dict):
            raise ValueError("Target section must contain an object.")
    if args.uninstall:
        if NAME not in parent:
            print("Already absent; no changes.")
            return
        del parent[NAME]
    else:
        if NAME in parent and parent[NAME] != server and not args.replace:
            raise ValueError("A different ccu entry exists; inspect it before using --replace.")
        if parent.get(NAME) == server:
            print("Already configured; no changes.")
            return
        parent[NAME] = server
    if args.apply:
        save(path, data)
        print(f"Updated {path}; reload the target client and verify tools and app approval.")
    else:
        # Never print unrelated config: it may contain other servers' secrets.
        print(json.dumps({"target": path, "section": args.section, "name": NAME,
                          "action": "remove" if args.uninstall else "set",
                          "server": server}, indent=2))
        print("Preview only. Add --apply to write.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--config", help="AI-verified strict JSON config path")
    target.add_argument("--client", choices=["claude"], help="Explicit legacy Claude Code adapter")
    parser.add_argument("--source", help="Verified Computer Use .mcp.json override")
    parser.add_argument("--section", nargs="+", default=["mcpServers"],
                        help="JSON object keys leading to the server map (default: mcpServers)")
    parser.add_argument("--stdio-type", action="store_true", help="Include type: stdio if required by client")
    parser.add_argument("--apply", action="store_true", help="Write settings (otherwise preview only)")
    parser.add_argument("--replace", action="store_true", help="Replace a reviewed conflicting JSON ccu entry")
    parser.add_argument("--uninstall", action="store_true")
    auto = parser.add_mutually_exclusive_group()
    auto.add_argument("--auto-approve", action="store_true", help="Claude only: install app block-list hook")
    auto.add_argument("--no-auto-approve", action="store_true", help="Claude only: keep normal app prompts (default)")
    parser.add_argument("--always-allow", action="store_true", help="Claude only: skip its outer tool prompt")
    args = parser.parse_args()
    if (args.auto_approve or args.no_auto_approve or args.always_allow) and args.client != "claude":
        parser.error("Approval flags require --client claude; they are not portable MCP settings.")
    if (args.apply or args.uninstall) and not (args.config or args.client):
        parser.error("Choose --config or --client explicitly before changing settings.")
    if args.replace and not args.config:
        parser.error("--replace requires --config")
    server = None if args.uninstall else server_config(args.source)
    if server is not None and (args.stdio_type or args.client == "claude"):
        server = {"type": "stdio", **server}
    if args.config:
        json_target(args, server)
        return
    if not args.client:
        print(json.dumps(server, indent=2))
        return
    if not args.apply:
        print(json.dumps({"client": "claude", "action": "remove" if args.uninstall else "set",
                          "server": server, "auto_approve": args.auto_approve,
                          "always_allow": args.always_allow}, indent=2))
        print("Preview only. Add --apply to write Claude Code settings.")
        return
    if args.uninstall:
        unregister()
        update_settings(hook=False, allow=False)
        for path in (HOOK_FILE, DENYLIST_FILE):
            if os.path.exists(path):
                os.remove(path)
        print("Removed. Restart Claude Code.")
        return
    register(server)
    if args.auto_approve:
        os.makedirs(HOOK_DIR, exist_ok=True)
        shutil.copy2(os.path.join(HERE, "ccu-approve.py"), HOOK_FILE)
        if not os.path.exists(DENYLIST_FILE):
            shutil.copy2(os.path.join(HERE, "ccu-denylist.txt"), DENYLIST_FILE)
    update_settings(hook=args.auto_approve, allow=args.always_allow)
    print("Updated Claude Code. Restart it and verify tools and app approval.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        sys.exit(f"Cannot configure Computer Use: {exc}")
