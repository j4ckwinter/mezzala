import os
from pathlib import Path

import pytest

from mezzala.save.saves import NoSaveFound, newest_save

MAC_GAMES = Path("Library/Application Support/Sports Interactive/Football Manager 27/games")
WINDOWS_GAMES = Path("Documents/Sports Interactive/Football Manager 27/games")
ONEDRIVE_GAMES = Path("OneDrive/Documents/Sports Interactive/Football Manager 27/games")


def save_at(home: Path, folder: Path, name: str, modified: int) -> Path:
    save = home / folder / name
    save.parent.mkdir(parents=True, exist_ok=True)
    save.write_bytes(b"")
    os.utime(save, ns=(modified, modified))
    return save


def test_the_most_recently_written_save_is_used_whichever_folder_it_is_in(tmp_path: Path) -> None:
    save_at(tmp_path, MAC_GAMES, "old.fm", 1_000)
    newer = save_at(tmp_path, WINDOWS_GAMES, "new.fm", 2_000)

    assert newest_save(tmp_path) == newer


def test_a_save_in_a_onedrive_documents_folder_is_found(tmp_path: Path) -> None:
    save = save_at(tmp_path, ONEDRIVE_GAMES, "career.fm", 1_000)

    assert newest_save(tmp_path) == save


def test_files_that_are_not_saves_are_ignored(tmp_path: Path) -> None:
    save = save_at(tmp_path, MAC_GAMES, "career.fm", 1_000)
    save_at(tmp_path, MAC_GAMES, "notes.txt", 2_000)

    assert newest_save(tmp_path) == save


def test_no_saves_names_the_folders_searched_and_the_save_option(tmp_path: Path) -> None:
    with pytest.raises(NoSaveFound) as raised:
        newest_save(tmp_path)

    assert str(tmp_path / ONEDRIVE_GAMES) in str(raised.value)
    assert "--save" in str(raised.value)
