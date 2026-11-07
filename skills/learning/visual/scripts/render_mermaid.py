#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>__TITLE__</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
         margin: 0; padding: 28px; background: #fafafa; color: #1a1a1a; }
  h1 { font-size: 19px; margin: 0 0 16px; }
  #out { background:#fff; border:1px solid #e2e2e2; border-radius:10px; padding:20px; overflow:auto; }
  #out svg { max-width:100%; height:auto; }
  details { margin-top:18px; }
  summary { cursor:pointer; color:#555; font-size:13px; }
  pre { background:#f4f4f4; padding:14px; border-radius:8px; overflow:auto; font-size:12px; line-height:1.45; }
  .err { color:#b00020; }
</style>
</head>
<body>
  <h1>__TITLE__</h1>
  <div id="out">rendering&hellip;</div>
  <details>
    <summary>Mermaid source</summary>
    <pre id="src"></pre>
  </details>
  <script type="module">
    const code = __CODE_JSON__;
    document.getElementById('src').textContent = code;
    try {
      const mermaid = (await import('https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs')).default;
      mermaid.initialize({ startOnLoad:false, theme:'default', securityLevel:'loose', flowchart:{ htmlLabels:true } });
      const { svg } = await mermaid.render('graph', code);
      document.getElementById('out').innerHTML = svg;
    } catch (e) {
      document.getElementById('out').innerHTML =
        '<p class="err">Mermaid failed to render (' + (e && e.message ? e.message : e) +
        '). Usually this means no network for the CDN — the source is shown below.</p>';
      document.querySelector('details').open = true;
    }
  </script>
</body>
</html>
"""


def slugify(text: str, default: str = "diagram") -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return s[:60] or default


def strip_fences(text: str) -> str:
    m = re.search(r"```(?:mermaid)?\s*\n(.*?)\n```", text, re.S)
    return (m.group(1) if m else text).strip()


def open_in_browser(path: Path):
    if sys.platform == "darwin":
        for cmd in (["open", "-a", "Google Chrome", str(path)], ["open", str(path)]):
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                return "Google Chrome" if "-a" in cmd else "default browser"
            except Exception:
                continue
    elif sys.platform.startswith("linux"):
        try:
            subprocess.run(["xdg-open", str(path)], check=True, capture_output=True)
            return "xdg-open"
        except Exception:
            pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a Mermaid diagram to HTML and open it.")
    ap.add_argument("source", nargs="?", help="file with mermaid source; omit to read stdin")
    ap.add_argument("--code", help="mermaid source as a literal string")
    ap.add_argument("--title", default="Mermaid Diagram")
    ap.add_argument("--out", help="output .html path (default: ~/.dot-agent/state/mermaid/<slug>.html)")
    ap.add_argument("--no-open", action="store_true", help="write the file but do not open a browser")
    a = ap.parse_args()

    if a.code is not None:
        src = a.code
    elif a.source:
        src = Path(a.source).expanduser().read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        src = sys.stdin.read()
    else:
        ap.error("no mermaid source: pass a file, --code, or pipe via stdin")
    src = strip_fences(src)
    if not src:
        print("error: empty mermaid source", file=sys.stderr)
        return 1

    if a.out:
        out = Path(a.out).expanduser().resolve()
    else:
        out = Path.home() / ".dot-agent" / "state" / "mermaid" / f"{slugify(a.title)}.html"
    out.parent.mkdir(parents=True, exist_ok=True)

    title = a.title.replace("<", "&lt;").replace(">", "&gt;")
    html = (HTML_TEMPLATE
            .replace("__TITLE__", title)
            .replace("__CODE_JSON__", json.dumps(src, ensure_ascii=False)))
    out.write_text(html, encoding="utf-8")

    opened = None if a.no_open else open_in_browser(out)
    print(f"file: {out}")
    print(f"link: {out.as_uri()}")
    print(f"opened: {opened or 'no (open the link above manually)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
