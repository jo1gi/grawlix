from typing import Callable

def to_list[T](optional: T | None) -> list[T]:
    """
    Convert an optional to a list with zero or one item.

    :param optional: The optional to convert
    :returns: The optional as a list
    """
    if optional is None:
        return []
    else:
        return [ optional ]
