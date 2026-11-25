from datetime import date

from factory import eleven, player, snapshot

from mezzala.core.players import Vacancy

BIG, SMALL = 20, 21


def vacancy(club, name, reputation, balance=None):
    return Vacancy(club, name, reputation, date(2026, 6, 29), balance, None)


def jobs(app, **arguments):
    return app.result("next_job", **arguments)["jobs"]


def test_open_jobs_are_listed_biggest_club_first_with_their_squad_and_money(mezzala):
    squad = [
        *eleven(),
        *[player(f"Big {n}", club=BIG, ca=140, positions=("dc",)) for n in range(3)],
    ]
    vacancies = (vacancy(SMALL, "Small FC", 3_000), vacancy(BIG, "Big FC", 7_000, balance=9_000_000))
    found = jobs(mezzala(snapshot(squad, vacancies=vacancies, club_reputation=5_000)))
    assert [(job["club"], job["bigger_than_yours"]) for job in found] == [("Big FC", True), ("Small FC", False)]
    assert found[0]["balance"] == "£9.0m"
    assert found[0]["best_eleven_average"] > 0


def test_bigger_only_leaves_out_smaller_clubs(mezzala):
    vacancies = (vacancy(SMALL, "Small FC", 3_000), vacancy(BIG, "Big FC", 7_000))
    found = jobs(mezzala(snapshot(eleven(), vacancies=vacancies, club_reputation=5_000)), bigger_only=True)
    assert [job["club"] for job in found] == ["Big FC"]


def test_vacancies_survive_a_restart(mezzala):
    app = mezzala(snapshot(eleven(), vacancies=(vacancy(BIG, "Big FC", 7_000),)))
    app.call("snapshot")
    assert [job["club"] for job in jobs(app.another_server())] == ["Big FC"]


def test_a_club_whose_players_are_not_loaded_has_no_best_eleven(mezzala):
    found = jobs(mezzala(snapshot(eleven(), vacancies=(vacancy(99, "Unloaded FC", 4_000),))))
    assert found[0]["best_eleven_average"] is None
