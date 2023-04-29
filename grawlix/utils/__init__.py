from grawlix.exceptions import DataNotFound

from urllib.parse import urlparse, parse_qs
from functools import lru_cache

def get_arg_from_url(url: str, key: str) -> str:
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    try:
        return query[key][0]
    except:
        raise DataNotFound


@lru_cache
def levenstein_distance(a: str, b: str) -> int:
    """
    Calculates the levenstein distance between `a` and `b`

    https://en.wikipedia.org/wiki/Levenshtein_distance
    """
    if len(a) == 0:
        return len(b)
    if len(b) == 0:
        return len(a)
    if a[0] == b[0]:
        return levenstein_distance(a[1:], b[1:])
    return 1 + min(
        levenstein_distance(a, b[1:]), # Character is inserted
        levenstein_distance(a[1:], b), # Character is deleted
        levenstein_distance(a[1:], b[1:]) # Character is replaced
    )



def nearest_string(input: str, list: list[str]) -> str:
    """
    Finds the nearest string in `list` to `input` based on levenstein distance
    """
    return sorted(list, key = lambda x: levenstein_distance(input, x))[0]
