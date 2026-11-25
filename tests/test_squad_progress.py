from dataclasses import replace
from datetime import date

from factory import eleven, mine, snapshot


def progress(app):
    return app.result("squad_progress")


def test_the_first_snapshot_is_the_starting_point(mezzala):
    result = progress(mezzala(snapshot(eleven())))
    assert result["compared_with"] is None and "starting point" in result["explanation"]


def test_the_squad_is_compared_with_the_first_snapshot(mezzala):
    squad = eleven(ca=100, value=1_000_000, wage=2_000)
    app = mezzala(snapshot(squad))
    app.call("snapshot")
    improved = [replace(p, current_ability=120 if p is squad[0] else 110) for p in squad]
    app.play_to(snapshot(improved, game_date=date(2027, 1, 1)))
    signing = mine("Signing", ca=130, value=3_000_000, wage=5_000)
    app.play_to(snapshot([*improved, signing], game_date=date(2027, 6, 1)))
    result = progress(app)
    rows = {row["measure"]: (row["then"], row["now"]) for row in result["measures"]}
    assert result["compared_with"] == "2026-06-29"
    assert rows["players available"] == ("11", "12")
    assert rows["value of the club's players"] == ("£11.0m", "£14.0m")
    assert rows["weekly wage bill"] == ("£22,000 p/w", "£27,000 p/w")
    assert [improver["ability_change"] for improver in result["most_improved"]][:2] == [20, 10]


def test_a_change_of_club_is_explained_instead_of_compared(mezzala):
    squad = eleven()
    app = mezzala(snapshot(squad))
    app.call("snapshot")
    moved = snapshot([replace(p, club_uid=2) for p in squad], game_date=date(2027, 1, 1))
    app.play_to(replace(moved, club_uid=2, club_name="New Club"))
    result = progress(app)
    assert "You managed Paisley in the first snapshot and New Club now" in result["explanation"]
    assert result["measures"] == []
