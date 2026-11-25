from factory import eleven, player, snapshot

from mezzala.save.nations import nation_name


def players():
    return [
        player("Irishman", nationalities=("Republic of Ireland",)),
        player("Dual National", nationalities=("Jamaica", "England")),
        player("Spaniard", nationalities=("Spain",)),
        player("Unknown Origin"),
    ]


def search(mezzala, **arguments):
    result = mezzala(snapshot([*eleven(), *players()])).result("find_players", **arguments)
    return {found["player"]["name"]: found for found in result["players"]}


def test_results_show_nationality_and_whether_a_work_permit_is_needed(mezzala):
    found = search(mezzala)
    assert found["Dual National"]["player"]["nationality"] == "Jamaica, England"
    assert found["Unknown Origin"]["player"]["nationality"] == "unknown"
    assert found["Irishman"]["needs_no_work_permit"] is True
    assert found["Spaniard"]["needs_no_work_permit"] is False


def test_work_permit_free_keeps_british_and_irish_players_including_second_nationalities(mezzala):
    assert set(search(mezzala, work_permit_free=True)) == {"Irishman", "Dual National"}


def test_nationality_matches_either_nationality_whatever_the_case(mezzala):
    assert set(search(mezzala, nationality="england")) == {"Dual National"}
    assert set(search(mezzala, nationality="Spain")) == {"Spaniard"}


def test_nations_are_named_from_fms_database_ids():
    assert [nation_name(i) for i in (765, 793, 801, 785, 789)] == [
        "England", "Scotland", "Wales", "Northern Ireland", "Republic of Ireland"]  # fmt: skip
    assert nation_name(999_999_999) == "nation 999999999"
