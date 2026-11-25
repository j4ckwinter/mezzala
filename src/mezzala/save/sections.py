from collections.abc import Callable, Iterable

import fmsave


def optional_section[T](read: Callable[[], Iterable[T]]) -> list[T]:
    try:
        return list(read())
    except fmsave.ReaderCheckError:
        return []
