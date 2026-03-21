from . import dcuniverseinfinite, ereolen, fanfictionnet, flipp, \
    internet_archive, mangaplus, marvel, nextory, royal_road, saxo, storytel, \
    webtoons

from grawlix import source
from grawlix.exceptions import InvalidUrl
from grawlix.source import UrlSupport


SOURCES: list[source.Source] = [
    dcuniverseinfinite.SOURCE,
    ereolen.SOURCE,
    fanfictionnet.SOURCE,
    flipp.SOURCE,
    internet_archive.SOURCE,
    mangaplus.SOURCE,
    marvel.SOURCE,
    nextory.SOURCE,
    royal_road.SOURCE,
    saxo.SOURCE,
    storytel.SOURCE,
    webtoons.SOURCE,
]


def find_source(url: str) -> source.Source:
    """
    Find source that matches url

    :param url: Url of book to download
    :returns: Source type for downloading url
    """
    for definition in SOURCES:
        support = definition.url_support(url)
        if support == UrlSupport.SupportedUrl:
            return definition
    raise InvalidUrl
