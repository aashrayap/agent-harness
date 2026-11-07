#!/usr/bin/env python3
import json
import os
import re
import shlex
import subprocess
import sys

MESSAGE = ("Pushing to main or master is never allowed: push a topic branch and open a PR. "
           "A high-risk PR merges only with the owner's recorded yes (AGENTS.md, Always pause).")
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", "|&"}
SHELLS = {"sh", "bash", "zsh", "dash", "eval", "watch", "ssh"}
GIT_VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
COMMAND_TOOLS = ("Bash", "mcp__terminal__run_in_terminal")
WHOLESALE_FLAGS = ("--all", "--branches", "--mirror")
NO_BRANCH_FLAGS = ("--dry-run", "-n", "--delete", "-d")
WRAPPERS = ("sudo", "env", "command", "time", "nohup")
MAIN_REF = re.compile(r"(^\+?|:)(refs/heads/)?(main|master)$")
FORCE_MESSAGE = ("Force-pushing is allowed only to the branch checked out where the push runs, so another "
                 "chat's branch is never rewritten; force-pushing a shared branch waits for the owner (AGENTS.md, "
                 "Always pause).")
FORCE_FLAGS = re.compile(r"^(--force|--force-with-lease(=.*)?|--force-if-includes|-[a-zA-Z]*f[a-zA-Z]*)$")
LOOSE_PUSH = re.compile(r"\bgit\b.*\bpush\b.*\b(main|master)\b", re.S)
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def line_ends(command):
    out, quote, index = [], None, 0
    while index < len(command):
        char = command[index]
        if char == "\\" and quote != "'" and command[index + 1:index + 2] == "\n":
            out.append(" ")
            index += 2
            continue
        if char == "\\" and quote != "'":
            out.append(command[index:index + 2])
            index += 2
            continue
        if quote:
            quote = None if char == quote else quote
        elif char in "'\"":
            quote = char
        out.append(" ; " if char == "\n" and not quote else char)
        index += 1
    return "".join(out)


def tokens(command):
    lexer = shlex.shlex(line_ends(command), posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def segments(words):
    current = []
    for word in words:
        if word in SEPARATORS or set(word) <= set(";&|()"):
            if current:
                yield current
            current = []
        else:
            current.append(word)
    if current:
        yield current


def split_heredocs(command):
    kept, bodies, lines = [], [], iter(command.split("\n"))
    for line in lines:
        kept.append(line)
        for _, delimiter in HEREDOC.findall(line):
            body = []
            for inner in lines:
                if inner.strip() == delimiter:
                    break
                body.append(inner)
            names = [os.path.basename(word) for word in line.replace("|", " ").split()]
            if any(name in SHELLS for name in names):
                bodies.append("\n".join(body))
    return "\n".join(kept), bodies


DUPLICATE = re.compile(r"[012]?>&[012]")
FILE_REDIRECT = r"(?:[012]?(?:>>|>\||>|<)|&>>?)"
TARGET = r"[A-Za-z0-9_./~][A-Za-z0-9_./~-]*"
REDIRECT_OPERATOR = re.compile(FILE_REDIRECT)
REDIRECT_WITH_TARGET = re.compile(FILE_REDIRECT + TARGET)
TARGET_WORD = re.compile(TARGET)


def strip_redirects(command):
    parts = re.split(r"([ \t]+)", command)
    index = 0
    while index < len(parts):
        word = parts[index]
        if DUPLICATE.fullmatch(word) or REDIRECT_WITH_TARGET.fullmatch(word):
            parts[index] = ""
        elif REDIRECT_OPERATOR.fullmatch(word) and index + 2 < len(parts) \
                and TARGET_WORD.fullmatch(parts[index + 2]):
            parts[index] = parts[index + 2] = ""
        index += 2
    return "".join(parts)


def positional(words):
    found, skip = [], False
    for word in words:
        if skip:
            skip = False
        elif word.startswith("-"):
            skip = word in GIT_VALUE_FLAGS
        else:
            found.append(word)
    return found


def current_branch(cwd, git_args):
    try:
        result = subprocess.run(["git", *git_args, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True,
                                text=True, cwd=cwd or None, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def git_dir_args(rest):
    found, index = [], 0
    while index < len(rest) - 1 and rest[index] in GIT_VALUE_FLAGS:
        if rest[index] in ("-C", "--git-dir", "--work-tree"):
            found += [rest[index], rest[index + 1]]
        index += 2
    return found


def force_elsewhere(rest, words, cwd):
    flags = [word for word in rest[rest.index("push") + 1:] if word.startswith("-")] if "push" in rest else []
    refspecs = words[2:]
    if not any(FORCE_FLAGS.match(flag) for flag in flags) and not any(ref.startswith("+") for ref in refspecs):
        return False
    branch = current_branch(cwd, git_dir_args(rest))
    if not branch or branch == "HEAD":
        return True
    targets = [ref.lstrip("+").rpartition(":")[2] or ref for ref in refspecs]
    return any(re.sub(r"^refs/heads/", "", target) not in (branch, "HEAD") for target in targets)


def without_redirects(words):
    kept, skip = [], False
    for word in words:
        if skip:
            skip = False
        elif set(word) <= set("<>&"):
            skip = True
            if kept and kept[-1].isdigit():
                kept.pop()
        else:
            kept.append(word)
    return kept


def lands_on_main(rest, cwd):
    args = without_redirects(rest[rest.index("push") + 1:])
    flags = [word for word in args if word.startswith("-")]
    if any(flag in NO_BRANCH_FLAGS for flag in flags):
        return False
    if any(flag in WHOLESALE_FLAGS for flag in flags):
        return True
    targets = [ref.lstrip("+").rpartition(":")[2] or ref for ref in positional(args)[1:]]
    if "--tags" in flags and not targets:
        return False
    if targets and not any(target in ("HEAD", "@") for target in targets):
        return False
    return current_branch(cwd, git_dir_args(rest)) in ("main", "master")


def runs_push(argv, depth, cwd=None):
    for index, word in enumerate(argv):
        name = os.path.basename(word)
        rest = argv[index + 1:]
        if name == "git":
            words = positional(rest)
            if words[:1] == ["push"] and any(MAIN_REF.search(item) for item in words[2:]):
                return MESSAGE
            leads = all(os.path.basename(item) in WRAPPERS or "=" in item or item.startswith("-")
                        for item in argv[:index])
            if words[:1] == ["push"] and "push" in rest and leads and lands_on_main(rest, cwd):
                return MESSAGE
            if words[:1] == ["push"] and force_elsewhere(rest, words, cwd):
                return FORCE_MESSAGE
        if name in SHELLS and rest:
            found = refused_push(" ".join(rest), depth + 1, cwd)
            if found:
                return found
    return None


PLAIN_COMMAND = re.compile(r"[A-Za-z0-9 \t\n_./:+=,@%~<>&|;-]*")


CHANGES_DIRECTORY = re.compile(r"(^|[;&|\n])\s*(cd|pushd|popd)\b")
READS_ARGUMENTS = re.compile(r"\b(xargs|parallel)\b")


def stripping_is_safe(command):
    if not PLAIN_COMMAND.fullmatch(command) or "<<" in command or CHANGES_DIRECTORY.search(command) \
            or READS_ARGUMENTS.search(command):
        return False
    stripped = strip_redirects(command)
    return stripped.count("push") == command.count("push")


def refused_push(command, depth=0, cwd=None):
    if depth > 4:
        return None
    original = scan_push(command, depth, cwd, strip=False)
    if original == MESSAGE or not stripping_is_safe(command):
        return original
    return scan_push(command, depth, cwd, strip=True)


def scan_push(command, depth, cwd, strip):
    command, bodies = split_heredocs(command)
    if strip:
        command = strip_redirects(command)
    for body in bodies:
        found = refused_push(body, depth + 1, cwd)
        if found:
            return found
    try:
        words = tokens(command)
    except ValueError:
        return MESSAGE if LOOSE_PUSH.search(command) else None
    for inner in re.findall(r"\$\((.*)\)|`([^`]*)`", command, re.S):
        found = refused_push("".join(inner), depth + 1, cwd)
        if found:
            return found
    for argv in segments(words):
        if argv[:1] in (["cd"], ["pushd"]) and len(argv) > 1:
            cwd = os.path.join(cwd or os.getcwd(), os.path.expanduser(argv[1]))
            continue
        found = runs_push(argv, depth, cwd)
        if found:
            return found
    return None


def command_cwd(event, tool_input):
    base = event.get("cwd") if isinstance(event.get("cwd"), str) else None
    typed = tool_input.get("cwd")
    if not isinstance(typed, str) or not typed:
        return base
    return os.path.join(base or "", os.path.expanduser(typed))


def decide(event):
    tool_input = event.get("tool_input")
    if event.get("tool_name") not in COMMAND_TOOLS or not isinstance(tool_input, dict):
        return None
    cwd = command_cwd(event, tool_input)
    reason = refused_push(str(tool_input.get("command") or ""), cwd=cwd)
    if not reason:
        return None
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "deny",
                                   "permissionDecisionReason": reason}}


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    decision = decide(event if isinstance(event, dict) else {})
    if decision:
        print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
