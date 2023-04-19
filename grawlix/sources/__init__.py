from grawlix.exceptions import NoSourceFound

from .source import Source
from .flipp import Flipp
from .mangaplus import MangaPlus
from .saxo import Saxo
from .webtoons import Webtoons

import re

source_cache: dict[str, Source] = {}

def load_source(url: str) -> Source:
    """
    Find source that matches url
    Will save loaded sources in cache

    :param url: Url of book to download
    :returns: Source type for downloading url
    """
    source_cls = find_source(url)
    source_name = source_cls.name
    if source_name in source_cache:
        return source_cache[source_name]
    else:
        source = source_cls()
        source_cache[source_name] = source
        return source


def find_source(url: str) -> type[Source]:
    """
    Find source that matches url

    :param url: Url of book to download
    :returns: Source type for downloading url
    """
    for cls in get_source_classes():
        for num, match in enumerate(cls.match):
            if re.match(match, url):
                return cls
    raise NoSourceFound


def get_source_classes() -> list[type[Source]]:
    """
    Get all source types

    :returns: A list of all available source types
    """
    return [
        Flipp,
        MangaPlus,
        Saxo,
        Webtoons
    ]