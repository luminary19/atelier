# -*- coding: utf-8 -*-
"""
atelier detect - PostToolUse hook wrapper (opt-in, non-blocking).

Wires the native detector (detect.py) to fire after a UI file is edited and surface BLOCK/WARN findings
back to the model as a quiet nudge. Strictly Atelier; pure stdlib.

CONTRACT (deliberately safe):
  - Reads the PostToolUse JSON event on stdin; pulls the edited file path.
  - Does nothing unless the file is a web file (css/html/jsx/tsx/vue/svelte/astro/...).
  - Runs detect.py --quiet --severity warn on JUST that file (drops 'suggest' noise).
  - If there are findings, emits them as PostToolUse additionalContext for the model.
  - ALWAYS exits 0. Never blocks or fails an edit. Any error -> silent exit 0.
  - Honors env ATELIER_DETECT_OFF=1 to disable without touching settings.

This hook is OPT-IN. It is NOT wired into settings.json automatically (it would run on every edit in
every repo). To enable it, see atelier-perf-a11y/references/detector.md.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# UI-certain extensions only. The hook is scoped TIGHTER than detect.py (which also scans .js/.ts/.md):
# bare .js/.ts are often backend / scripts / config, so the passive hook skips them to stay non-disruptive
# on non-frontend work. React UI (.jsx/.tsx) and component/style files are always design surfaces.
# Full .js/.ts/.md coverage still happens via a manual `detect.py` run or atelier-review.
WEB_EXT = {".html", ".htm", ".css", ".scss", ".sass", ".less",
           ".jsx", ".tsx", ".vue", ".svelte", ".astro"}


def emit_context(text: str) -> None:
    """Surface findings to the model via the PostToolUse additionalContext channel."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": text,
        }
    }))


def main() -> None:
    if os.environ.get("ATELIER_DETECT_OFF") == "1":
        sys.exit(0)
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)

    tool_input = event.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not file_path or Path(file_path).suffix.lower() not in WEB_EXT:
        sys.exit(0)
    if not Path(file_path).is_file():
        sys.exit(0)

    detect = Path(__file__).with_name("detect.py")
    try:
        result = subprocess.run(
            [sys.executable, str(detect), file_path, "--quiet", "--severity", "warn"],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        sys.exit(0)

    out = (result.stdout or "").strip()
    if out:
        emit_context(
            "atelier detect (regex-tier, advisory) flagged the file you just edited:\n\n"
            + out
            + "\n\nFix the BLOCK items; weigh WARN items against the Direction Doc / ATELIER.md "
              "(a committed concept device is not a tell). Verify visual tells in-browser via atelier-review."
        )
    sys.exit(0)


if __name__ == "__main__":
    main()
