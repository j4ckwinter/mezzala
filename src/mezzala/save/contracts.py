from datetime import date

import fmsave


def is_running(entry: fmsave.ContractChainEntry, today: date) -> bool:
    started = entry.start is not None and entry.start <= today
    return started and (entry.end is None or entry.end >= today)


def running_at_contract_club(contract: fmsave.Contract, today: date) -> list[fmsave.ContractChainEntry]:
    return [
        entry
        for entry in contract.chain
        if entry.club_uid == contract.club_uid and entry.has_terms and is_running(entry, today)
    ]


def start_of(entry: fmsave.ContractChainEntry) -> date:
    return entry.start or date.min


def signed_record(contract: fmsave.Contract, today: date) -> fmsave.ContractChainEntry | None:
    running = running_at_contract_club(contract, today)
    if len(running) < 2:
        return None
    return min(running, key=start_of)


def contract_end(contract: fmsave.Contract, today: date) -> date | None:
    signed = signed_record(contract, today)
    return contract.end if signed is None else signed.end


def contract_wage(contract: fmsave.Contract, today: date) -> int | None:
    signed = signed_record(contract, today)
    return contract.wage if signed is None else signed.wage
