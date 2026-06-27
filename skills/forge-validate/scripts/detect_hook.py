"""
forge-validate/scripts/detect_hook.py
PostToolUse hook wrapper for the Forge validate detector.

Reads a Claude Code PostToolUse JSON event from stdin.
Extracts the edited file path, runs detect.py on it if it is a .py or .glb file,
and emits additionalContext JSON to stdout with any findings.

Contract (non-negotiable):
  - Always exits 0 — NEVER blocks or fails an edit.
  - Emits additionalContext JSON only when findings are non-empty.
  - Opt-out: set env var FORGE_DETECT_OFF=1 to suppress.

Hook registration in settings.json:
  {
    "PostToolUse": [{
      "matcher": "Edit|Write|MultiEdit",
      "hooks": [{
        "type": "command",
        "command": "python \"$env:CLAUDE_CONFIG_DIR\\skills\\forge-validate\\scripts\\detect_hook.py\""
      }]
    }]
  }
"""

import sys
import io
import json
import os
import subprocess
import pathlib

# Windows stdout encoding fix
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SCRIPT_DIR = pathlib.Path(__file__).parent
DETECT_SCRIPT = SCRIPT_DIR / "detect.py"
RELEVANT_EXTS = {".py", ".glb", ".gltf"}


def main():
    # Check opt-out env var
    if os.environ.get("FORGE_DETECT_OFF", "").strip() == "1":
        sys.exit(0)

    # Read PostToolUse event from stdin
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)
        event = json.loads(raw)
    except Exception:
        sys.exit(0)

    # Extract file path from event
    tool_input = event.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path", "")
    if not file_path:
        sys.exit(0)

    p = pathlib.Path(file_path)
    if p.suffix.lower() not in RELEVANT_EXTS:
        sys.exit(0)

    if not p.exists():
        sys.exit(0)

    # Run detect.py on the file
    try:
        result = subprocess.run(
            [sys.executable, str(DETECT_SCRIPT), "--target", str(p), "--json"],
            capture_output=True, text=True, timeout=10
        )
        report_text = result.stdout.strip()
        if not report_text:
            sys.exit(0)
        report = json.loads(report_text)
    except Exception:
        sys.exit(0)

    findings = report.get("findings", [])
    if not findings:
        sys.exit(0)

    # Only surface BLOCK and WARN (suppress NOTE in hooks to reduce noise)
    visible = [f for f in findings if f.get("level") in ("BLOCK", "WARN")]
    if not visible:
        sys.exit(0)

    counts = report.get("summary", {})
    lines = [f"[forge-validate detect] {p.name}: BLOCK:{counts.get('BLOCK',0)} WARN:{counts.get('WARN',0)}"]
    for f in visible:
        icon = "BLOCK" if f["level"] == "BLOCK" else "WARN "
        lines.append(f"  [{icon}] [{f['id']}] {f['msg']}")

    # Emit additionalContext (the only output channel for hooks)
    output = {"additionalContext": "\n".join(lines)}
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Hook must NEVER exit non-zero or raise — always silent failure
        sys.exit(0)
