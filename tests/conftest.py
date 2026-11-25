import asyncio
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from mcp import Client

from mezzala.core.players import Snapshot
from mezzala.core.view import View
from mezzala.save.career import Career
from mezzala.save.store import FileStamp, SnapshotStore
from mezzala.save.watchlist import WatchlistStore
from mezzala.server import create_server


class SaveUnreadable(Exception):
    pass


@dataclass
class FakeSave:
    snapshot: Snapshot | None = None
    version: int = 0
    reads: int = 0
    failing: Exception | None = None
    read_seconds: float = 0.0
    missing: set[Path] = field(default_factory=set[Path])
    no_saves: bool = False
    path: Path = field(default_factory=lambda: Path("career.fm"))

    def write(self, snapshot: Snapshot) -> None:
        self.snapshot = snapshot
        self.version += 1

    def read(self, _: Path) -> Snapshot:
        self.reads += 1
        time.sleep(self.read_seconds)
        if self.failing is not None:
            raise self.failing
        assert self.snapshot is not None
        return self.snapshot

    def locate(self) -> Path:
        if self.no_saves:
            raise FileNotFoundError("No .fm saves found")
        return self.path

    def stamp(self, path: Path) -> FileStamp:
        if path in self.missing:
            raise FileNotFoundError(f"{path.name} is being rewritten")
        return FileStamp(self.version, 1)


@dataclass(frozen=True)
class ToolResult:
    is_error: bool
    data: dict[str, Any]
    text: str


@dataclass
class Mezzala:
    save: FakeSave
    career: Career
    database: Path
    watched: WatchlistStore
    view: View = View.FULL

    def another_server(self) -> "Mezzala":
        store = SnapshotStore(self.database)
        career = Career(self.save.locate, store, self.save.read, self.save.stamp)
        return Mezzala(self.save, career, self.database, WatchlistStore(self.database), self.view)

    def call(self, tool: str, **arguments: Any) -> ToolResult:
        async def run() -> ToolResult:
            async with Client(create_server(self.career, self.watched, self.view)) as client:
                result = await client.call_tool(tool, arguments)
                text = "".join(getattr(block, "text", "") for block in result.content)
                data = result.structured_content or (json.loads(text) if not result.is_error else {})
                return ToolResult(result.is_error, data, text)

        return asyncio.run(run())

    def call_together(self, *tools: str) -> list[ToolResult]:
        async def run() -> list[ToolResult]:
            async with Client(create_server(self.career, self.watched, self.view)) as client:
                results = await asyncio.gather(*(client.call_tool(tool, {}) for tool in tools))
                return [ToolResult(r.is_error, r.structured_content or {}, "") for r in results]

        return asyncio.run(run())

    def result(self, tool: str, **arguments: Any) -> dict[str, Any]:
        outcome = self.call(tool, **arguments)
        assert not outcome.is_error, outcome.text
        return outcome.data["result"]

    def play_to(self, snapshot: Snapshot) -> None:
        self.save.write(snapshot)
        assert not self.call("snapshot").is_error


@pytest.fixture
def mezzala(tmp_path: Path) -> Callable[..., Mezzala]:
    def start(first: Snapshot, view: View = View.FULL) -> Mezzala:
        save = FakeSave()
        save.write(first)
        database = tmp_path / "snapshots.db"
        career = Career(save.locate, SnapshotStore(database), save.read, save.stamp)
        return Mezzala(save, career, database, WatchlistStore(database), view)

    return start
