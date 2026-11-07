#!/usr/bin/env python3
import ast
import io
import re
import subprocess
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW = ROOT / "scripts" / "no-comments.allow"

HASH_FILES = {".yaml", ".yml", ".toml", ".tsv"}
WHOLE_LINE_HASH = {".gitignore", ".gitattributes", "markers", "provided-skills"}
FENCE_LANGS = {
    "bash": "sh", "sh": "sh", "shell": "sh", "zsh": "sh", "console": "sh",
    "python": "py", "py": "py",
    "js": "js", "javascript": "js", "ts": "js", "typescript": "js", "json5": "js",
    "css": "css",
    "html": "html", "svg": "html", "xml": "html",
    "yaml": "hash", "yml": "hash", "toml": "hash",
}
FENCE = re.compile(r"^\s*(```+|~~~+)\s*([\w+-]*)")


def python_comments(text, offset=0):
    found = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return [(offset + 1, "unparseable python")]
    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            if tok.start[0] == 1 and tok.string.startswith("#!") and offset == 0:
                continue
            found.append((offset + tok.start[0], tok.string))
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return found
    nodes = [tree] + [
        n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    for node in nodes:
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            found.append((offset + body[0].lineno, "docstring"))
    return found


def shell_comments(text, offset=0):
    found = []
    quote = None
    heredoc = None
    for number, line in enumerate(text.split("\n"), 1):
        if heredoc:
            if line.strip() == heredoc:
                heredoc = None
            continue
        if number == 1 and offset == 0 and line.startswith("#!"):
            continue
        i = 0
        while i < len(line):
            ch = line[i]
            if quote == "'":
                if ch == "'":
                    quote = None
            elif quote == '"':
                if ch == "\\":
                    i += 1
                elif ch == '"':
                    quote = None
            elif ch == "\\":
                i += 1
            elif ch in "'\"":
                quote = ch
            elif ch == "#" and (i == 0 or line[i - 1] in " \t;&|()"):
                found.append((offset + number, line[i:].strip()))
                break
            elif line.startswith("<<", i) and not line.startswith("<<<", i):
                match = re.match(r"<<-?\s*(['\"]?)(\w+)\1", line[i:])
                if match:
                    heredoc = match.group(2)
                    i += match.end() - 1
            i += 1
    return found


def hash_comments(text, offset=0, whole_line=False):
    found = []
    for number, line in enumerate(text.split("\n"), 1):
        if whole_line:
            if line.lstrip().startswith("#"):
                found.append((offset + number, line.strip()))
            continue
        quote = None
        for i, ch in enumerate(line):
            if quote:
                if ch == quote:
                    quote = None
            elif ch in "'\"":
                quote = ch
            elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
                found.append((offset + number, line[i:].strip()))
                break
    return found


def line_of(text, index):
    return text.count("\n", 0, index) + 1


REGEX_BEFORE = set("(,=:[!&|?{};+-*%<>~^")


def js_comments(text, offset=0, css=False):
    found = []
    i = 0
    stack = []
    last = ""
    while i < len(text):
        ch = text[i]
        mode = stack[-1] if stack else None
        if mode in ("'", '"'):
            if ch == "\\":
                i += 2
                continue
            if ch == mode or ch == "\n":
                stack.pop()
            i += 1
            continue
        if mode == "`":
            if ch == "\\":
                i += 2
                continue
            if ch == "`":
                stack.pop()
            elif text.startswith("${", i):
                stack.append("{")
                i += 2
                continue
            i += 1
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = len(text) if end < 0 else end + 2
            found.append((offset + line_of(text, i), text[i:end].split("\n")[0].strip()))
            i = end
            continue
        if not css and text.startswith("//", i):
            end = text.find("\n", i)
            end = len(text) if end < 0 else end
            found.append((offset + line_of(text, i), text[i:end].strip()))
            i = end
            continue
        if ch in "'\"" or (ch == "`" and not css):
            stack.append(ch)
        elif ch == "{":
            stack.append("{")
        elif ch == "}":
            if stack and stack[-1] == "{":
                stack.pop()
        elif ch == "/" and not css and (last in REGEX_BEFORE or last == ""):
            j = i + 1
            in_class = False
            while j < len(text) and text[j] != "\n":
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == "[":
                    in_class = True
                elif text[j] == "]":
                    in_class = False
                elif text[j] == "/" and not in_class:
                    break
                j += 1
            i = j + 1
            last = "/"
            continue
        if not ch.isspace():
            last = ch
        i += 1
    return found


def html_comments(text, offset=0):
    found = []
    for match in re.finditer(r"<!--", text):
        found.append((offset + line_of(text, match.start()), "<!--"))
    for match in re.finditer(r"(<script\b[^>]*>)(.*?)</script>", text, re.S | re.I):
        start = match.start(2)
        found += js_comments(match.group(2), offset + line_of(text, start) - 1)
    for match in re.finditer(r"(<style\b[^>]*>)(.*?)</style>", text, re.S | re.I):
        start = match.start(2)
        found += js_comments(match.group(2), offset + line_of(text, start) - 1, css=True)
    return found


def fixup_js_lines(found, text):
    lines = text.split("\n")
    return [(n, lines[n - 1].strip() if 0 < n <= len(lines) else s) for n, s in found]


SCANNERS = {
    "py": python_comments,
    "sh": shell_comments,
    "js": js_comments,
    "css": lambda t, o=0: js_comments(t, o, css=True),
    "html": html_comments,
    "hash": hash_comments,
}


def markdown_comments(text):
    found = []
    lines = text.split("\n")
    fence = None
    block = []
    prose = []
    for number, line in enumerate(lines, 1):
        match = FENCE.match(line)
        if fence is None and match:
            fence = (match.group(1)[0] * len(match.group(1)), FENCE_LANGS.get(match.group(2).lower()), number)
            block = []
            continue
        if fence is not None:
            if line.strip().startswith(fence[0]) and not line.strip().strip(fence[0][0]):
                if fence[1]:
                    found += SCANNERS[fence[1]]("\n".join(block), fence[2])
                fence = None
                continue
            block.append(line)
            continue
        prose.append((number, line))
    for number, line in prose:
        if "<!--" in re.sub(r"`[^`]*`", "", line):
            found.append((number, line.strip()))
    return found


def kind(path, text):
    name = path.name
    if path.suffix == ".md":
        return "md"
    if path.suffix == ".py":
        return "py"
    if path.suffix == ".sh":
        return "sh"
    if path.suffix in (".html", ".svg"):
        return "html"
    if path.suffix in (".js", ".mjs", ".css"):
        return path.suffix.lstrip(".").replace("mjs", "js")
    if path.suffix in HASH_FILES:
        return "hash"
    if name in WHOLE_LINE_HASH:
        return "whole"
    first = text.split("\n", 1)[0]
    if first.startswith("#!"):
        return "py" if "python" in first else "sh"
    return None


def scan(path, text):
    which = kind(path, text)
    if which is None:
        return []
    if which == "md":
        found = markdown_comments(text)
    elif which == "whole":
        found = hash_comments(text, whole_line=True)
    else:
        found = SCANNERS[which](text)
    return fixup_js_lines(found, text)


def load_allow():
    files, lines = set(), set()
    for raw in ALLOW.read_text().splitlines():
        if not raw.strip():
            continue
        if "\t" in raw:
            path, line = raw.split("\t", 1)
            lines.add((path, line.strip()))
        else:
            files.add(raw.strip())
    return files, lines


def tracked(paths):
    if paths:
        return paths
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [rel for rel in out.stdout.split() if not rel.startswith(".claude/skills/")]


def main(argv):
    allow_files, allow_lines = load_allow()
    used = set()
    failures = []
    for rel in tracked(argv):
        path = ROOT / rel
        if rel in allow_files:
            used.add(rel)
            continue
        if not path.is_file():
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        for number, line in scan(path, text):
            if (rel, line) in allow_lines:
                used.add((rel, line))
                continue
            failures.append(f"{rel}:{number}: {line}")
    stale = [] if argv else sorted(str(x) for x in (allow_files | allow_lines) - used)
    for failure in failures:
        print(failure)
    for entry in stale:
        print(f"stale allowlist entry: {entry}")
    if failures or stale:
        print(f"no-comments: FAIL ({len(failures)} comments, {len(stale)} stale allowlist entries)")
        return 1
    print("no-comments: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
