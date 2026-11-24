STORED_UNITS_PER_POUND = 1


def pounds(stored: int) -> float:
    return stored / STORED_UNITS_PER_POUND


def sign(stored: int) -> str:
    return "-" if stored < 0 else ""


def format_money(stored: int | None) -> str:
    if stored is None:
        return "unknown"
    amount = abs(pounds(stored))
    if round(amount / 1_000) >= 1_000:
        return f"{sign(stored)}£{amount / 1_000_000:.1f}m"
    if amount >= 1_000:
        return f"{sign(stored)}£{amount / 1_000:.0f}k"
    return f"{sign(stored)}£{amount:.0f}"


def format_weekly_wage(stored: int | None) -> str:
    if stored is None:
        return "unknown"
    return f"{sign(stored)}£{abs(pounds(stored)):,.0f} p/w"


def stored_from_pounds(amount: float) -> int:
    return round(amount * STORED_UNITS_PER_POUND)
