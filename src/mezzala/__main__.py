import argparse
from pathlib import Path

from mezzala.core.view import View
from mezzala.save.career import Career
from mezzala.save.reader import read_snapshot
from mezzala.save.saves import newest_save
from mezzala.save.store import SnapshotStore
from mezzala.save.watchlist import WatchlistStore
from mezzala.server import create_server

DEFAULT_DATABASE = Path.home() / ".mezzala" / "snapshots.db"


def main() -> None:
    parser = argparse.ArgumentParser(prog="mezzala", description="Football Manager 27 transfer MCP server")
    parser.add_argument(
        "--save", type=Path, help="the .fm save to read; defaults to whichever FM27 save was written last"
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE, help="where snapshots are kept")
    arguments = parser.parse_args()
    pinned: Path | None = arguments.save
    locate = (lambda: pinned) if pinned is not None else (lambda: newest_save(Path.home()))
    career = Career(locate, SnapshotStore(arguments.database), read_snapshot)
    create_server(career, WatchlistStore(arguments.database), View.FULL).run()


if __name__ == "__main__":
    main()
