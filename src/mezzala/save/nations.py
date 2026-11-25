import csv
from functools import cache
from importlib.resources import files

NATIONS_FILE = "nations.csv"


@cache
def nation_names() -> dict[int, str]:
    text = files("mezzala.data").joinpath(NATIONS_FILE).read_text(encoding="utf-8")
    return {int(row["database_id"]): row["name"] for row in csv.DictReader(text.splitlines())}


def nation_name(database_id: int) -> str:
    return nation_names().get(database_id, f"nation {database_id}")
