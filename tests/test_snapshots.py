from datetime import date
from pathlib import Path

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


def test_snapshots_survive_a_restart(mezzala):
    app = mezzala(snapshot(eleven()))
    app.call("snapshot")
    app.play_to(snapshot(eleven(), game_date=date(2026, 9, 1)))
    restarted = app.another_server()
    assert restarted.call("snapshot").data["snapshot_dates"] == ["2026-06-29", "2026-09-01"]
    assert app.save.reads == 2


def test_tools_called_together_after_a_save_read_it_once(mezzala):
    app = mezzala(snapshot(eleven()))
    app.save.read_seconds = 0.2
    results = app.call_together("snapshot", "squad_gaps", "sell_high", "contract_watch")
    assert [result.is_error for result in results] == [False] * 4
    assert app.save.reads == 1


def test_a_second_server_sees_a_same_day_resave_by_the_first(mezzala):
    first = mezzala(snapshot(eleven(ca=100)))
    second = first.another_server()
    first.call("squad_gaps")
    second.call("squad_gaps")
    first.play_to(snapshot(eleven(ca=130)))
    eleven_level = second.result("squad_gaps")["starting_eleven_median_ability"]
    assert eleven_level == 130


def test_saves_with_the_same_name_in_different_folders_keep_separate_histories(mezzala):
    app = mezzala(snapshot(eleven()))
    app.call("snapshot")
    app.save.path = Path("elsewhere/career.fm")
    app.play_to(snapshot(eleven(), game_date=date(2030, 1, 1)))
    assert app.call("snapshot").data["snapshot_dates"] == ["2030-01-01"]


def test_the_server_follows_a_save_written_after_it_started(mezzala):
    app = mezzala(snapshot(eleven()))
    app.call("snapshot")
    app.save.path = Path("new career.fm")
    app.play_to(snapshot(eleven(), game_date=date(2026, 7, 2)))
    context = app.call("snapshot").data["context"]
    assert (context["save"], context["game_date"]) == ("new career.fm", "2026-07-02")


def test_reloading_an_older_save_counts_only_snapshots_up_to_its_date(mezzala):
    app = mezzala(snapshot(eleven()))
    app.call("snapshot")
    app.play_to(snapshot(eleven(), game_date=date(2026, 12, 1)))
    app.play_to(snapshot(eleven(), game_date=date(2026, 9, 1)))
    report = app.call("snapshot").data
    assert report["snapshot_dates"] == ["2026-06-29", "2026-09-01"]
    assert report["context"]["snapshots"] == 2
