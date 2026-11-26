from datetime import date
from types import SimpleNamespace
from typing import cast

from fmsave import Contract

from mezzala.save.contracts import contract_end, contract_wage

DUNDEE_UNITED = 1556
TODAY = date(2027, 5, 25)


def record(start, end, wage, club=DUNDEE_UNITED, has_terms=True):
    return SimpleNamespace(club_uid=club, start=start, end=end, wage=wage, has_terms=has_terms)


def contract(*chain, end, wage, club=DUNDEE_UNITED):
    return cast(Contract, SimpleNamespace(club_uid=club, chain=chain, end=end, wage=wage))


SIGNED = record(date(2024, 7, 1), date(2027, 5, 31), 2_500)
OFFER = record(date(2027, 5, 20), date(2030, 5, 31), 2_975)


def test_an_open_renewal_offer_does_not_replace_the_contract_it_would_extend():
    ferry = contract(SIGNED, OFFER, end=OFFER.end, wage=OFFER.wage)
    assert contract_end(ferry, TODAY) == date(2027, 5, 31)
    assert contract_wage(ferry, TODAY) == 2_500


def test_a_signed_renewal_replaces_the_old_record_and_is_read_as_it_is():
    renewed = contract(OFFER, end=OFFER.end, wage=OFFER.wage)
    assert contract_end(renewed, TODAY) == date(2030, 5, 31)
    assert contract_wage(renewed, TODAY) == 2_975


def test_an_empty_offer_does_not_wipe_the_contract_end():
    empty = record(date(2027, 5, 22), None, 0)
    farnham = contract(SIGNED, empty, end=None, wage=0)
    assert contract_end(farnham, TODAY) == date(2027, 5, 31)


def test_a_move_elsewhere_that_starts_later_leaves_the_contract_alone():
    pre_contract = record(date(2027, 7, 1), date(2030, 5, 31), 3_400, club=1597)
    leaving = contract(SIGNED, pre_contract, end=SIGNED.end, wage=SIGNED.wage)
    assert contract_end(leaving, TODAY) == date(2027, 5, 31)
