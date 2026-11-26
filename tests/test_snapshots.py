from dataclasses import replace
from datetime import date
from pathlib import Path

import fmsave
from factory import eleven, player, snapshot


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


def test_an_overspent_budget_reads_as_a_negative_amount(mezzala):
    context = mezzala(snapshot(eleven(), transfer_budget=-2_500_000)).call("snapshot").data["context"]
    assert context["transfer_budget"] == "-£2.5m"


def test_a_save_briefly_missing_while_fm_rewrites_it_falls_back_to_the_last_snapshot(mezzala):
    app = mezzala(snapshot(eleven()))
    app.call("snapshot")
    app.save.missing.add(app.save.path)
    notes = app.call("snapshot").data["context"]["notes"]
    assert "using the snapshot from 2026-06-29" in notes[0]


def test_a_vanished_save_is_not_swapped_for_another_save_in_the_folder(mezzala):
    app = mezzala(snapshot(eleven()))
    app.call("snapshot")
    app.save.missing.add(app.save.path)
    app.save.path = Path("old career.fm")
    context = app.call("snapshot").data["context"]
    assert context["save"] == "career.fm"
    assert "using the snapshot from 2026-06-29" in context["notes"][0]


def test_a_vanished_only_save_falls_back_to_the_last_snapshot(mezzala):
    app = mezzala(snapshot(eleven()))
    app.call("snapshot")
    app.save.missing.add(app.save.path)
    app.save.no_saves = True
    assert "using the snapshot from 2026-06-29" in app.call("snapshot").data["context"]["notes"][0]


def test_a_wage_bill_over_budget_reads_as_negative_headroom(mezzala):
    over = snapshot(eleven())
    over = replace(over, budget=replace(over.budget, wage_payroll_weekly=65_000))
    assert mezzala(over).call("snapshot").data["context"]["wage_headroom"] == "-£5,000 p/w"


def test_a_budget_just_under_a_million_reads_as_a_million(mezzala):
    context = mezzala(snapshot(eleven(), transfer_budget=999_999)).call("snapshot").data["context"]
    assert context["transfer_budget"] == "£1.0m"


def store_original_format_snapshot(database_path, players):
    import json
    import sqlite3
    import zlib

    from mezzala.save.store import ORIGINAL_FIELDS, encode_player

    original_rows = [encode_player(player)[:ORIGINAL_FIELDS] for player in players]
    database = sqlite3.connect(database_path)
    database.execute(
        "CREATE TABLE snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, career TEXT NOT NULL, "
        "game_date TEXT NOT NULL, file_mtime_ns INTEGER NOT NULL, file_size INTEGER NOT NULL, "
        "club_uid INTEGER NOT NULL, club_name TEXT NOT NULL, club_reputation INTEGER NOT NULL, "
        "budget TEXT NOT NULL, players BLOB NOT NULL, UNIQUE (career, game_date))"
    )
    database.execute(
        "INSERT INTO snapshots (career, game_date, file_mtime_ns, file_size, club_uid, club_name, club_reputation, "
        "budget, players) VALUES (?, '2026-06-29', 1, 1, 1, 'Paisley', 5000, '[100000, 60000, 55000]', ?)",
        (str(Path("career.fm").resolve()), zlib.compress(json.dumps(original_rows).encode())),
    )
    database.commit()
    database.close()


def test_an_unchanged_save_is_read_again_when_its_snapshot_is_in_an_older_format(mezzala, tmp_path):
    squad = [*eleven(), player("Youth Deal", youth_contract=True)]
    store_original_format_snapshot(tmp_path / "snapshots.db", squad)
    app = mezzala(snapshot(squad))
    found = app.result("find_players", youth_contract_only=True)["players"]
    assert app.save.reads == 1
    assert [f["player"]["name"] for f in found] == ["Youth Deal"]


def test_a_snapshot_in_an_older_format_still_loads_when_the_save_cannot_be_read(mezzala, tmp_path):
    store_original_format_snapshot(tmp_path / "snapshots.db", eleven())
    app = mezzala(snapshot(eleven()))
    app.save.failing = fmsave.CorruptSaveError("half written")
    report = app.call("squad").data
    assert len(report["result"]["available"]) == 11
    assert "using the snapshot from 2026-06-29" in report["context"]["notes"][0]


def test_adding_a_column_another_server_already_added_is_harmless():
    import sqlite3

    from mezzala.save.store import SCHEMA, add_column

    database = sqlite3.connect(":memory:")
    database.execute(SCHEMA)
    add_column(database, "format", "INTEGER NOT NULL DEFAULT 1")


def test_loan_wages_and_clause_expiry_survive_a_restart(mezzala):
    from mezzala.core.players import ReleaseClause, ReleaseScope

    loanee = player("Loanee", club=1, on_loan=True, loan_parent_club_uid=9, wage=9_000, loan_wage=1_500)
    lapsed = player("Lapsed Clause", release_clauses=(ReleaseClause(ReleaseScope.DOMESTIC, 100_000, date(2026, 6, 1)),))
    app = mezzala(snapshot([*eleven(), loanee, lapsed]))
    app.call("snapshot")
    restarted = app.another_server()
    squad = {m["player"]["name"]: m["player"]["wage_while_on_loan"] for m in restarted.result("squad")["available"]}
    assert squad["Loanee"] == "£1,500 p/w"
    assert restarted.result("find_players", max_release_clause=1_000_000)["players"] == []
    assert app.save.reads == 1


def test_the_new_player_and_club_facts_survive_a_restart(mezzala):
    from mezzala.core.players import Injury, MentoringGroup, PendingDeal, SeasonStats, StaffMember, Tactic
    from mezzala.save.store import SnapshotStore

    season = SeasonStats(900, 10, 2, 6.9, 3, 2, 2.5, 1.5, 20, 12, 40, 8, 15, 9, 30, 1)
    starter = replace(
        eleven()[0], adaptability=12, loyalty=13, pressure=14, sportsmanship=15, temperament=16, controversy=4,
        left_foot=8, right_foot=20, height_cm=188, traits=("shoots from distance",), condition=96, match_sharpness=71,
        banned_from=("Scottish Cup",), injury="Twisted Ankle", injured_until=date(2026, 7, 10),
        injuries=(Injury(date(2026, 4, 25), "major", "in training"),), season=season,
        nationalities=("Scotland", "Ghana"), club_country="Scotland", squad_status="fringe player",
        renewal_offer=PendingDeal(1, "Paisley", date(2026, 6, 20), date(2029, 5, 31), 2_400),
        moves_lined_up=(PendingDeal(7, "Rival FC", date(2026, 7, 1), None, None),),
    )  # fmt: skip
    first = replace(
        snapshot([starter, *eleven()[1:]]),
        staff=(StaffMember("Coach", "coach", 44, {"attacking": 14}),),
        tactics=(Tactic("Press", "positive", ("gk", "dc", None)),),
        mentoring=(MentoringGroup("Group 1", (starter.uid,)),),
    )
    app = mezzala(first)
    app.call("snapshot")
    stored = SnapshotStore(app.database).load(str(Path("career.fm").resolve()), first.game_date)
    assert stored == first


def test_every_answer_says_when_the_save_was_written(mezzala):
    app = mezzala(snapshot(eleven()))
    app.save.version = 1_782_000_000_000_000_000
    assert app.call("squad").data["context"]["save_written"] == "2026-06-21 00:00 UTC"


def test_the_write_time_is_unknown_when_falling_back_to_a_stored_snapshot(mezzala):
    app = mezzala(snapshot(eleven()))
    app.call("squad")
    app.save.missing.add(app.save.path)
    assert app.call("squad").data["context"]["save_written"] == "unknown"


def test_the_instructions_warn_that_changes_in_fm_show_only_after_saving():
    from mezzala.server import INSTRUCTIONS

    assert "show until the manager saves again" in INSTRUCTIONS


def test_the_write_time_is_unknown_when_a_newer_save_cannot_be_read(mezzala):
    app = mezzala(snapshot(eleven()))
    app.call("squad")
    app.save.version += 1
    app.save.failing = fmsave.CorruptSaveError("half written")
    assert app.call("squad").data["context"]["save_written"] == "unknown"
