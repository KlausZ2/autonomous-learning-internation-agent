import json
from pathlib import Path
from typing import Any


def read_jsonl(path: str) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []

    records = []
    buffer = []
    buffer_start_line = 0

    for line_number, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line and not buffer:
            continue
        if not line and buffer:
            records.append(_parse_json_record(path, buffer, buffer_start_line))
            buffer = []
            buffer_start_line = 0
            continue

        if not buffer:
            try:
                records.append(json.loads(line))
                continue
            except json.JSONDecodeError:
                buffer_start_line = line_number

        buffer.append(line)

    if buffer:
        records.append(_parse_json_record(path, buffer, buffer_start_line))
    return records


def _parse_json_record(path: str, lines: list[str], start_line: int) -> dict[str, Any]:
    try:
        return json.loads("\n".join(lines))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON record in {path} starting at line {start_line}: {exc}") from exc


def append_jsonl(path: str, record: dict[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_jsonl(path: str, records: list[dict[str, Any]]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
