from datetime import date

import fmsave
from factory import eleven, snapshot


def test_first_call_stores_the_save_as_a_snapshot(mezzala):
    app = mezzala(snapshot(eleven()))
    report = app.call("snapshot").data
    assert report["context"]["snapshots"] == 1
    assert report["context"]["game_date"] == "2026-06-29"
    assert report["context"]["club"] == "Paisley"
    assert report["snapshot_dates"] == ["2026-06-29"]


def test_an_unchanged_save_is_not_read_again(mezzala):
    app = mezzala(snapshot(eleven()))
    app.call("snapshot")
    app.call("squad_gaps")
    assert app.save.reads == 1


def test_a_save_at_a_later_date_adds_a_snapshot(mezzala):
    app = mezzala(snapshot(eleven()))
    app.call("snapshot")
    app.play_to(snapshot(eleven(), game_date=date(2026, 9, 1)))
    assert app.call("snapshot").data["snapshot_dates"] == ["2026-06-29", "2026-09-01"]


def test_saving_again_on_the_same_day_replaces_that_snapshot(mezzala):
    app = mezzala(snapshot(eleven()))
    app.call("snapshot")
    app.play_to(snapshot(eleven(ca=120)))
    report = app.call("snapshot").data
    assert report["snapshot_dates"] == ["2026-06-29"]
    assert report["context"]["snapshots"] == 1


def test_an_unreadable_save_falls_back_to_the_last_snapshot(mezzala):
    app = mezzala(snapshot(eleven()))
    app.call("snapshot")
    app.save.version += 1
    app.save.failing = fmsave.CorruptSaveError("half written")
    report = app.call("snapshot").data
    assert report["context"]["game_date"] == "2026-06-29"
    assert "using the snapshot from 2026-06-29" in report["context"]["notes"][0]


def test_an_unreadable_first_save_is_reported(mezzala):
    app = mezzala(snapshot(eleven()))
    app.save.failing = fmsave.CorruptSaveError("half written")
    assert app.call("snapshot").is_error


def test_snapshots_survive_a_restart(mezzala, tmp_path):
    from mezzala.career import Career
    from mezzala.store import SnapshotStore

    app = mezzala(snapshot(eleven()))
    app.call("snapshot")
    app.play_to(snapshot(eleven(), game_date=date(2026, 9, 1)))
    restarted = type(app)(app.save, Career(app.save.path, SnapshotStore(tmp_path / "snapshots.db"), app.save.read,
                                           app.save.stamp))  # fmt: skip
    assert restarted.call("snapshot").data["snapshot_dates"] == ["2026-06-29", "2026-09-01"]
    assert app.save.reads == 2
