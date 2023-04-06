from grawlix.exceptions import NoSourceFound

from .source import Source
from .flipp import Flipp
from .mangaplus import MangaPlus
from .saxo import Saxo
from .webtoons import Webtoons

import re


def find_source(url: str) -> Source:
    """
    Find source that matches url

    :param url: Url of book to download
    :returns: Source for downloading url
    """
    for cls in get_source_classes():
        for num, match in enumerate(cls.match):
            if re.match(match, url):
                source = cls()
                return source
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
