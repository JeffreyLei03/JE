import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

session_path = r"C:\Users\onepl\.je\sessions\projects-je-1bad51\a6d126574e51484ea137790e42b74e95.jsonl"
lines = open(session_path, encoding="utf-8").readlines()
print(f"Session total entries: {len(lines)}")

for i, l in enumerate(lines):
    d = json.loads(l)
    m = d.get("message", {})
    role = m.get("role")
    content = m.get("content")
    if role == "user":
        print(f"\n=== [STEP {i}] USER PROMPT ===")
        print(str(content)[:250] + "...")
    elif role == "assistant" and isinstance(content, list):
        print(f"\n=== [STEP {i}] JE AGENT ===")
        for item in content:
            t = item.get("type")
            if t == "thinking":
                th = item.get("thinking", "").strip()
                summary_line = th.split("\n")[0]
                print(f"  [Thinking ({len(th)} chars)]: {summary_line}")
            elif t == "toolCall":
                name = item.get("name")
                args = item.get("arguments", {})
                cmd = args.get("command") or args.get("path") or args.get("description") or ""
                print(f"  [ToolCall]: {name} -> {str(cmd)[:120]}")
            elif t == "text":
                txt = item.get("text", "").strip()
                print(f"  [Agent Message]: {txt[:120]}")
    elif role == "toolResult":
        res_text = ""
        if isinstance(content, list) and content:
            res_text = content[0].get("text", "")
        res_text = res_text.strip().replace("\r", "").replace("\n", " ")
        print(f"  [ToolResult]: {res_text[:120]}")
