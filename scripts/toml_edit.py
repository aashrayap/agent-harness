from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True

try:
    import tomllib as _parser
except ModuleNotFoundError:
    try:
        import tomli as _parser
    except ModuleNotFoundError:
        _parser = None

_EXTERNAL_PARSER = None
_PARSE = (
    "import json,sys,tomllib; "
    "print(json.dumps(tomllib.loads(sys.stdin.read()),default=str))"
)


def strict_loads(text: str) -> dict:
    global _EXTERNAL_PARSER
    if _parser is not None:
        return _parser.loads(text)
    if _EXTERNAL_PARSER is None:
        for name in ("python3.14", "python3.13", "python3.12", "python3.11"):
            executable = shutil.which(name)
            if executable and subprocess.run(
                [executable, "-B", "-c", "import tomllib"], capture_output=True
            ).returncode == 0:
                _EXTERNAL_PARSER = executable
                break
    if _EXTERNAL_PARSER is None:
        raise ValueError("Config mutation needs Python 3.11+ or tomli; the partial TOML reader cannot authorize writes")
    result = subprocess.run([_EXTERNAL_PARSER, "-B", "-c", _PARSE], input=text,
                            text=True, capture_output=True)
    if result.returncode:
        raise ValueError("Invalid TOML; config was not changed: " + result.stderr.strip())
    return json.loads(result.stdout)


def line_editable(text: str) -> dict:
    document = strict_loads(text)
    in_managed_table = True
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("["):
            if not re.fullmatch(r"\[[^\]]+\]", stripped):
                raise ValueError(f"Unsupported TOML table form at line {number}; config was not changed")
            table = strict_loads(stripped + "\n__dot_agent_probe__ = true\n")
            in_managed_table = "features" in table
            if in_managed_table and stripped != "[features]":
                raise ValueError(f"Unsupported managed table spelling at line {number}; config was not changed")
            continue
        assignment = re.fullmatch(r"\s*([A-Za-z0-9_-]+)\s*=\s*(.*)", line)
        if in_managed_table and assignment is None:
            raise ValueError(f"Unsupported TOML assignment at line {number}; config was not changed")
        try:
            strict_loads(line)
        except ValueError as error:
            raise ValueError(f"Unsupported multiline TOML value at line {number}; config was not changed") from error
    return document


if __name__ == "__main__":
    for argument in sys.argv[1:]:
        path = Path(argument)
        if path.is_file():
            line_editable(path.read_text())
