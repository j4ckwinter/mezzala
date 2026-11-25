from dataclasses import replace
from datetime import date

from factory import eleven, player, snapshot


def test_the_first_snapshot_becomes_the_baseline(mezzala):
    report = mezzala(snapshot(eleven())).result("regen_intake")
    assert report["compared_with"] is None
    assert report["regens"] == []
    assert "baseline" in report["explanation"]


def test_new_youth_players_since_the_baseline_are_listed_by_potential(mezzala):
    existing = player("Existing Kid", age=16, pa=170)
    app = mezzala(snapshot([*eleven(), existing]))
    app.call("snapshot")
    gem = player("Gem", age=15, ca=60, pa=175)
    decent = player("Decent", age=15, ca=50, pa=125)
    dud = player("Dud", age=15, ca=40, pa=90)
    app.play_to(snapshot([*eleven(), existing, decent, gem, dud], game_date=date(2027, 3, 20)))
    report = app.result("regen_intake")
    assert report["compared_with"] == "2026-06-29"
    assert report["total_new"] == 3
    assert [regen["name"] for regen in report["regens"]] == ["Gem", "Decent"]


def test_a_youth_player_given_a_retired_players_id_counts_as_new(mezzala):
    retired = player("Retired", age=36, ca=90, pa=90)
    app = mezzala(snapshot([*eleven(), retired]))
    app.call("snapshot")
    regen = replace(
        retired, name="Reborn", age=15, birth_date=date(2011, 2, 2), current_ability=50, potential_ability=150
    )
    app.play_to(snapshot([*eleven(), regen], game_date=date(2027, 3, 20)))
    assert [entry["name"] for entry in app.result("regen_intake")["regens"]] == ["Reborn"]


def test_clubs_whose_intakes_produced_the_best_regens_are_listed(mezzala):
    squad = eleven()
    app = mezzala(snapshot(squad))
    app.call("snapshot")
    regens = [player("Gem A", age=15, pa=180, club=2, club_name="Academy FC"),
              player("Gem B", age=15, pa=150, club=2, club_name="Academy FC"),
              player("Lone", age=15, pa=160, club=3, club_name="Elsewhere FC")]  # fmt: skip
    app.play_to(snapshot([*squad, *regens], game_date=date(2027, 3, 20)))
    clubs = app.result("regen_intake")["by_club"]
    assert [(c["club"], c["new_regens"], c["best"]) for c in clubs] == [
        ("Academy FC", 2, "Gem A"),
        ("Elsewhere FC", 1, "Lone"),
    ]


def test_unsigned_regens_are_those_on_youth_contracts_or_without_a_club(mezzala):
    squad = eleven()
    app = mezzala(snapshot(squad))
    app.call("snapshot")
    regens = [player("Youth Deal", age=16, pa=150, youth_contract=True),
              player("Unattached", age=16, pa=150, club=None, value=None),
              player("Professional", age=16, pa=150, youth_contract=False)]  # fmt: skip
    app.play_to(snapshot([*squad, *regens], game_date=date(2027, 3, 20)))
    names = sorted(r["name"] for r in app.result("regen_intake", unsigned_only=True)["regens"])
    assert names == ["Unattached", "Youth Deal"]


def test_since_last_save_compares_with_the_previous_snapshot(mezzala):
    squad = eleven()
    app = mezzala(snapshot(squad))
    app.call("snapshot")
    early = player("Early Regen", age=15, pa=150)
    app.play_to(snapshot([*squad, early], game_date=date(2027, 3, 20)))
    late = player("Late Regen", age=15, pa=150)
    app.play_to(snapshot([*squad, early, late], game_date=date(2027, 4, 20)))
    assert [r["name"] for r in app.result("regen_intake", since_last_save=True)["regens"]] == ["Late Regen"]
    assert sorted(r["name"] for r in app.result("regen_intake")["regens"]) == ["Early Regen", "Late Regen"]
