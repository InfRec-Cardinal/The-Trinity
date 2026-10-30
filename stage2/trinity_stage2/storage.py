from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
from uuid import uuid4


def write_text(path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    try:
        with open(temporary, "x", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json(path, value, indent=1) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=indent))


def write_csv(path, rows) -> None:
    buffer = io.StringIO()
    csv.writer(buffer).writerows(rows)
    write_text(path, buffer.getvalue())


def append_line(path, line: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = memoryview(line.encode("utf-8"))
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        size = os.fstat(descriptor).st_size
        try:
            while data:
                data = data[os.write(descriptor, data):]
            os.fsync(descriptor)
        except BaseException:
            os.ftruncate(descriptor, size)
            raise
    finally:
        os.close(descriptor)


def complete_lines(path) -> list[str]:
    path = Path(path)
    if not path.exists():
        return []
    return [line for line in path.read_text(encoding="utf-8").split("\n")[:-1] if line.strip()]
