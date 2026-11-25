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
SWITCHED_ON = frozenset({"true", "on", "yes", "1"})
SWITCHED_OFF = frozenset({"false", "off", "no", "0", ""})


def fog_of_war(text: str) -> View:
    switch = text.strip().lower()
    if switch in SWITCHED_ON:
        return View.SPOILER_FREE
    if switch in SWITCHED_OFF:
        return View.FULL
    raise argparse.ArgumentTypeError(f"expected on or off, not {text!r}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="mezzala", description="Football Manager 27 transfer MCP server")
    parser.add_argument(
        "--save", type=Path, help="the .fm save to read; defaults to whichever FM27 save was written last"
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE, help="where snapshots are kept")
    parser.add_argument(
        "--fog-of-war",
        type=fog_of_war,
        nargs="?",
        const=View.SPOILER_FREE,
        default=View.FULL,
        help="hide what FM hides: show ability as stars, leave out hidden attributes (on or off; default off)",
    )
    arguments = parser.parse_args()
    pinned: Path | None = arguments.save
    locate = (lambda: pinned) if pinned is not None else (lambda: newest_save(Path.home()))
    career = Career(locate, SnapshotStore(arguments.database), read_snapshot)
    create_server(career, WatchlistStore(arguments.database), arguments.fog_of_war).run()


if __name__ == "__main__":
    main()
