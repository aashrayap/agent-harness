from __future__ import annotations

import json
from typing import Any, BinaryIO


class TOMLDecodeError(ValueError):
    pass


def _strip_comment(line: str) -> str:
    in_string = False
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if char == "#" and not in_string:
            return line[:index]
    return line


def _parse_value(raw: str) -> Any:
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            raise TOMLDecodeError(str(error)) from error
    if raw in {"true", "false"}:
        return raw == "true"
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        values: list[Any] = []
        current = []
        in_string = False
        escaped = False
        for char in inner:
            if escaped:
                current.append(char)
                escaped = False
                continue
            if char == "\\" and in_string:
                escaped = True
                current.append(char)
                continue
            if char == '"':
                in_string = not in_string
                current.append(char)
                continue
            if char == "," and not in_string:
                values.append(_parse_value("".join(current)))
                current = []
                continue
            current.append(char)
        if current:
            values.append(_parse_value("".join(current)))
        return values
    try:
        return int(raw)
    except ValueError:
        return raw


def load(handle: BinaryIO) -> dict[str, Any]:
    try:
        text = handle.read().decode("utf-8")
    except Exception as exc:
        raise TOMLDecodeError(str(exc)) from exc

    data: dict[str, Any] = {}
    current = data

    for line_number, line in enumerate(text.splitlines(), start=1):
        line = _strip_comment(line).strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            table_name = line[1:-1].strip()
            if not table_name:
                raise TOMLDecodeError(f"empty table name at line {line_number}")
            current = data
            for part in table_name.split("."):
                current = current.setdefault(part, {})
                if not isinstance(current, dict):
                    raise TOMLDecodeError(f"table conflict at line {line_number}")
            continue
        if "=" not in line:
            raise TOMLDecodeError(f"expected key/value at line {line_number}")
        key, raw_value = line.split("=", 1)
        key = key.strip().strip('"')
        if not key:
            raise TOMLDecodeError(f"empty key at line {line_number}")
        current[key] = _parse_value(raw_value)

    return data
