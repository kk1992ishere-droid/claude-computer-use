#!/usr/bin/env python3
# Elicitation hook for the ccu MCP server (Computer Use from the ChatGPT desktop app).
# Answers its per-app prompt 'Allow Computer Use to use "<App>"?':
#   - app named in ccu-denylist.txt (next to this file) -> decline
#   - any other app -> accept
# Other prompts (e.g. recording computer audio), or a missing block list, fall through to the normal dialog.
# Each decision is appended to ccu-approvals.log next to this file (local only).
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DENYLIST = os.path.join(HERE, "ccu-denylist.txt")
LOG = os.path.join(HERE, "ccu-approvals.log")


def log(line):
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{ts} {line}\n")


def blocked_names():
    with open(DENYLIST, encoding="utf-8") as f:
        names = (line.split("#", 1)[0].strip().lower() for line in f)
        return [n for n in names if n]


msg = json.load(sys.stdin).get("message", "")
m = re.match(r'^Allow Computer Use to use "(.+)"\?$', msg)
if not m or not os.path.exists(DENYLIST):
    log(f"skip    {msg[:80]!r}")
    sys.exit(0)

app = m.group(1)
name = app.lower()
denied = any(re.search(rf"(^|[^a-z0-9]){re.escape(n)}($|[^a-z0-9])", name) for n in blocked_names())
action = "decline" if denied else "accept"
log(f"{action:<8}{app}")

out = {"hookEventName": "Elicitation", "action": action}
if action == "accept":
    out["content"] = {}
print(json.dumps({"hookSpecificOutput": out}))
