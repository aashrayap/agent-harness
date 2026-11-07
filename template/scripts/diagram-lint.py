#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).absolute().parents[1]
MAX_NODES = 8
MAX_WORDS = 8
STATES = ("done", "todo", "problem")
FENCE = re.compile(r"^[ \t]*```mermaid[ \t]*\n(.*?)^[ \t]*```", re.M | re.S)
COLOR = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b|\b(?:rgb|hsl)a?\(")
FORBIDDEN = re.compile(r"^(classDef|style|linkStyle)\b")
C4 = re.compile(r"^C4\w*")
CLOSERS = {"[": "]", "(": ")", "{": "}", ">": "]"}
ARROW = re.compile(r"<?(?:-{2,}|={2,}|-\.+-|~{3,})(?:>|[xo](?![\w]))?")
INLINE_LABEL = re.compile(r"(?:--|==|-\.)\s+([^-=.|>\s][^|]*?)\s+(?:-{2,}>|-{3,}|={2,}>|={3,}|\.-+>|-{2,}[xo]\b)")
SKIP_FLOW = re.compile(r"^(?:(?:end|click|classDef|style|linkStyle)\b|direction\s|%%)")
SEQ_SKIP = re.compile(r"^(end|else|and|autonumber|activate|deactivate|rect|box|%%)\b")
SEQ_BLOCK = re.compile(r"^(loop|alt|opt|par|critical|break)\b\s*(.*)$")
SEQ_ACTOR = re.compile(r"^(?:participant|actor)\s+(\S+)(?:\s+as\s+(.+))?$")
SEQ_MESSAGE = re.compile(r"^(.+?)\s*(?:<<)?-{1,2}(?:>>|>|x|\))\s*[+-]?\s*(.+?)\s*:\s*(.*)$")
NOTE = re.compile(r"^note\b[^:]*:\s*(.*)$", re.I)
STATE_DECL = re.compile(r'^state\s+"([^"]*)"\s+as\s+(\w+)')
STATE_BLOCK = re.compile(r"^state\s+(\w+)")
STATE_EDGE = re.compile(r"^(\S+)\s*-->\s*([^:\s]+)\s*(?::\s*(.*))?$")
STATE_DESC = re.compile(r"^(\w+)\s*:\s*(.*)$")
ER_REL = re.compile(r'^([\w-]+)\s+\S+--\S+\s+([\w-]+)\s*:\s*"?([^"]*)"?')
ER_ENTITY = re.compile(r"^([\w-]+)\s*\{")


def words(label):
    text = re.sub(r"<[^>]+>", " ", label)
    text = re.sub(r"#\w+;", " ", text)
    text = re.sub(r"[*_`\"]", " ", text)
    return len(text.split())


def strip_class(name):
    base, _, shorthand = name.partition(":::")
    return base, shorthand


def read_label(line, i):
    opener = line[i]
    while i < len(line) and line[i] in "[({/\\>":
        i += 1
    if i < len(line) and line[i] == '"':
        end = line.find('"', i + 1)
        end = len(line) if end < 0 else end
        label, i = line[i + 1:end], end + 1
    else:
        end = line.find(CLOSERS[opener], i)
        end = len(line) if end < 0 else end
        label, i = line[i:end].rstrip("/\\"), end
    while i < len(line) and line[i] in "])}/\\":
        i += 1
    return label, i


def flowchart(lines):
    nodes, labels, classes = {}, [], []
    for number, line in lines:
        if SKIP_FLOW.match(line):
            continue
        if line.startswith("class "):
            parts = line.split()
            classes.append((number, parts[-1]))
            continue
        if line.startswith("subgraph"):
            rest = line[len("subgraph"):].strip()
            match = re.match(r"\w+\s*(\[.*)$", rest)
            label = read_label(match.group(1), 0)[0] if match else rest
            labels.append((number, label))
            continue
        i = 0
        while i < len(line):
            char = line[i]
            if char.isspace() or char in "&;":
                i += 1
                continue
            if char == "|":
                end = line.find("|", i + 1)
                end = len(line) if end < 0 else end
                labels.append((number, line[i + 1:end]))
                i = end + 1
                continue
            inline = INLINE_LABEL.match(line, i)
            if inline:
                labels.append((number, inline.group(1)))
                i = inline.end()
                continue
            arrow = ARROW.match(line, i)
            if arrow and arrow.end() > i:
                i = arrow.end()
                continue
            ident = re.match(r"\w+(?::::\w+)?", line[i:])
            if not ident:
                i += 1
                continue
            name, shorthand = strip_class(ident.group(0))
            if shorthand:
                classes.append((number, shorthand))
            nodes.setdefault(name, number)
            i += ident.end()
            if line.startswith("@{", i):
                end = line.find("}", i)
                shape = re.search(r'label:\s*"([^"]*)"', line[i:end])
                if shape:
                    labels.append((number, shape.group(1)))
                i = len(line) if end < 0 else end + 1
                continue
            if i < len(line) and line[i] in CLOSERS:
                label, i = read_label(line, i)
                labels.append((number, label))
                tail = re.match(r":::(\w+)", line[i:])
                if tail:
                    classes.append((number, tail.group(1)))
                    i += tail.end()
    return nodes, labels, classes


def sequence(lines):
    nodes, labels = {}, []
    for number, line in lines:
        if SEQ_SKIP.match(line):
            continue
        block = SEQ_BLOCK.match(line)
        if block:
            labels.append((number, block.group(2)))
            continue
        note = NOTE.match(line)
        if note:
            labels.append((number, note.group(1)))
            continue
        actor = SEQ_ACTOR.match(line)
        if actor:
            nodes.setdefault(actor.group(1), number)
            labels.append((number, actor.group(2) or actor.group(1)))
            continue
        message = SEQ_MESSAGE.match(line)
        if message:
            nodes.setdefault(message.group(1), number)
            nodes.setdefault(message.group(2), number)
            labels.append((number, message.group(3)))
    return nodes, labels, []


def state(lines):
    nodes, labels, classes = {}, [], []
    for number, line in lines:
        if line in ("}", "--") or line.startswith("%%") or line.startswith("direction"):
            continue
        if line.startswith("class "):
            classes.append((number, line.split()[-1]))
            continue
        note = NOTE.match(line)
        if note:
            labels.append((number, note.group(1)))
            continue
        declared = STATE_DECL.match(line)
        if declared:
            nodes.setdefault(declared.group(2), number)
            labels.append((number, declared.group(1)))
            continue
        edge = STATE_EDGE.match(line)
        if edge:
            for end in edge.group(1, 2):
                name, shorthand = strip_class(end)
                if shorthand:
                    classes.append((number, shorthand))
                if name != "[*]":
                    nodes.setdefault(name, number)
            if edge.group(3):
                labels.append((number, edge.group(3)))
            continue
        block = STATE_BLOCK.match(line)
        if block:
            nodes.setdefault(block.group(1), number)
            continue
        described = STATE_DESC.match(line)
        if described:
            nodes.setdefault(described.group(1), number)
            labels.append((number, described.group(2)))
    return nodes, labels, classes


def er(lines):
    nodes, labels, inside = {}, [], False
    for number, line in lines:
        if inside:
            inside = line != "}"
            continue
        entity = ER_ENTITY.match(line)
        if entity:
            nodes.setdefault(entity.group(1), number)
            inside = not line.endswith("}")
            continue
        relation = ER_REL.match(line)
        if relation:
            nodes.setdefault(relation.group(1), number)
            nodes.setdefault(relation.group(2), number)
            labels.append((number, relation.group(3)))
    return nodes, labels, []


PARSERS = {"flowchart": flowchart, "graph": flowchart, "sequenceDiagram": sequence,
           "stateDiagram": state, "stateDiagram-v2": state, "erDiagram": er}


def problems(source):
    found = []
    raw = source.splitlines()
    lines = [(number, line.strip()) for number, line in enumerate(raw, 1) if line.strip()]
    if lines and lines[0][1] == "---":
        close = next((index for index, (_, line) in enumerate(lines[1:], 1) if line == "---"), len(lines) - 1)
        if any(line.startswith("config:") for _, line in lines[1:close]):
            found.append(f"line {lines[0][0]}: front-matter config sets the theme; the page sets it")
        lines = lines[close + 1:]
    for number, line in lines:
        if "%%{" in line:
            found.append(f"line {number}: init directive; the page sets the theme")
        directive = FORBIDDEN.match(line)
        if directive:
            found.append(f"line {number}: {directive.group(1)}; color means state only: use class X done, todo or problem")
        for color in COLOR.findall(line):
            found.append(f"line {number}: {color} is a hand color or a #number; use state classes and plain words")
    body = [(number, line) for number, line in lines if not line.startswith("%%")]
    if not body:
        return ["no diagram"], 0
    first = body[0][1].split()[0]
    if C4.match(first):
        found.append(f"line {body[0][0]}: {first}: C4 ignores the theme and overlaps labels; use a flowchart")
        return found, 0
    parse = PARSERS.get(first)
    if not parse:
        return found, 0
    nodes, labels, classes = parse(body[1:])
    if len(nodes) > MAX_NODES:
        found.append(f"{len(nodes)} boxes (max {MAX_NODES}); split it into a series of small diagrams")
    for number, label in labels:
        count = words(label)
        if count > MAX_WORDS:
            found.append(f"line {number}: label has {count} words (max {MAX_WORDS}): {label.strip()}")
    for number, name in classes:
        if name not in STATES:
            found.append(f"line {number}: class {name}; color means state only: done, todo or problem")
    return found, len(nodes)


def diagrams(text, where, markdown):
    if not markdown:
        return [(where, text)]
    return [(f"{where}:{text.count(chr(10), 0, match.start(1)) + 1}", match.group(1))
            for match in FENCE.finditer(text)]


def committed():
    listed = subprocess.run(["git", "-C", str(ROOT), "ls-files", "*.mmd", "*.md"],
                            capture_output=True, text=True, check=True).stdout.split()
    return [ROOT / path for path in listed if not path.startswith(".claude/") and (ROOT / path).is_file()]


def gather(args):
    found = []
    for path in committed() if args.repo else []:
        found += diagrams(path.read_text(encoding="utf-8"), str(path.relative_to(ROOT)), path.suffix == ".md")
    for item in args.inputs:
        if item == "-":
            found += diagrams(sys.stdin.read(), "stdin", False)
        elif "\n" not in item and Path(item).is_file():
            found += diagrams(Path(item).read_text(encoding="utf-8"), item, item.endswith(".md"))
        else:
            found += diagrams(item, "source", False)
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fail a Mermaid diagram that is too big, too wordy or colored by hand.")
    parser.add_argument("inputs", nargs="*", help="Mermaid source, a .mmd or .md file, or - for stdin")
    parser.add_argument("--repo", action="store_true", help="also lint every committed .mmd file and Markdown mermaid fence")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.inputs and not args.repo:
        parser.error("give Mermaid source, a file, - or --repo")
    results = []
    for where, source in gather(args):
        found, count = problems(source)
        results.append({"where": where, "nodes": count, "problems": found})
    ok = all(not result["problems"] for result in results)
    if args.json:
        print(json.dumps({"ok": ok, "diagrams": results}, indent=2))
    else:
        for result in results:
            for problem in result["problems"]:
                print(f"ERROR: {result['where']}: {problem}")
        print("diagram-lint: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
