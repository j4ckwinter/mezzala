from pathlib import Path

GAMES_FOLDERS = (
    Path("Library/Application Support/Sports Interactive/Football Manager 27/games"),
    Path("Documents/Sports Interactive/Football Manager 27/games"),
    Path("AppData/Local/Sports Interactive/Football Manager 27/games"),
)


class NoSaveFound(FileNotFoundError):
    pass


def newest_save(home: Path) -> Path:
    saves = [save for folder in GAMES_FOLDERS for save in (home / folder).glob("*.fm")]
    if not saves:
        searched = ", ".join(str(home / folder) for folder in GAMES_FOLDERS)
        raise NoSaveFound(f"No .fm saves found in {searched}. Pass --save with the path to your save.")
    return max(saves, key=lambda save: save.stat().st_mtime_ns)
