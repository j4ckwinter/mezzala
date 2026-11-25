from factory import OTHER_CLUB, eleven, mine, player, snapshot


def plan(app, **arguments):
    return app.result("development_plan", **arguments)


def named(entries):
    return [entry["name"] for entry in entries]


def test_a_youngster_close_to_the_weakest_starter_is_ready(mezzala):
    squad = [*eleven(ca=100), mine("Nearly There", positions=("stc",), age=19, ca=98, pa=140)]
    result = plan(mezzala(snapshot(squad)))
    assert named(result["ready_for_first_team"]) == ["Nearly There"]
    assert result["ready_for_first_team"][0]["gap_to_first_team"] == -2


def test_a_youngster_far_off_with_room_to_grow_should_go_on_loan(mezzala):
    squad = [*eleven(ca=110), mine("Needs Games", positions=("stc",), age=18, ca=80, pa=130)]
    squad.append(mine("Too Young", positions=("stc",), age=16, ca=60, pa=130))
    squad.append(mine("No Ceiling", positions=("stc",), age=20, ca=80, pa=84))
    assert named(plan(mezzala(snapshot(squad)))["loan_out"]) == ["Needs Games"]


def test_players_already_out_on_loan_are_listed_separately(mezzala):
    away = player("Away", age=19, ca=85, pa=130, club=OTHER_CLUB, on_loan=True, loan_parent_club_uid=1)
    result = plan(mezzala(snapshot([*eleven(), away])))
    assert named(result["already_on_loan"]) == ["Away"]
    assert "Away" not in named(result["loan_out"])


def test_focus_keeps_youngsters_who_can_reach_the_first_eleven_best_potential_first(mezzala):
    squad = [*eleven(age=25, ca=100), mine("Gem", age=17, ca=70, pa=170), mine("Decent", age=20, ca=95, pa=120),
             mine("Low Ceiling", age=16, ca=40, pa=90, professionalism=20, ambition=20)]  # fmt: skip
    assert named(plan(mezzala(snapshot(squad)))["focus"]) == ["Gem", "Decent"]


def test_loan_players_from_other_clubs_are_not_part_of_the_plan(mezzala):
    loanee = mine("Borrowed", age=19, ca=98, pa=150, on_loan=True, loan_parent_club_uid=9)
    result = plan(mezzala(snapshot([*eleven(ca=100), loanee])))
    assert "Borrowed" not in named(result["ready_for_first_team"]) + named(result["focus"])
