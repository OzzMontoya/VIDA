"""Registro JSONL de eventos por corrida: una línea por ``EventRecord``, claves ordenadas."""

from __future__ import annotations

from pathlib import Path
from typing import IO

from vida.simulation.events import EventRecord


class JsonlEventLogger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh: IO[str] | None = self.path.open("w", encoding="utf-8", newline="\n")
        self.count = 0

    def write(self, event: EventRecord) -> None:
        if self._fh is None:
            raise RuntimeError("logger cerrado")
        self._fh.write(event.to_json_line())
        self._fh.write("\n")
        self.count += 1

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def __enter__(self) -> "JsonlEventLogger":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def read_events(path: str | Path) -> list[EventRecord]:
    with Path(path).open("r", encoding="utf-8") as fh:
        return [EventRecord.model_validate_json(line) for line in fh if line.strip()]
