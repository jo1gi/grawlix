from . import dcuniverseinfinite, ereolen, fanfictionnet, flipp, \
    globalcomix, internet_archive, mangaplus, marvel, nextory, royal_road, saxo, storytel, \
    webtoons

from grawlix import source
from grawlix.exceptions import InvalidUrl
from grawlix.source import UrlSupport


SOURCES: list[source.Source] = [
    dcuniverseinfinite.SOURCE,
    ereolen.SOURCE,
    fanfictionnet.SOURCE,
    flipp.SOURCE,
    globalcomix.SOURCE,
    internet_archive.SOURCE,
    mangaplus.SOURCE,
    marvel.SOURCE,
    nextory.SOURCE,
    royal_road.SOURCE,
    saxo.SOURCE,
    storytel.SOURCE,
    webtoons.SOURCE,
]

cache: dict[str, source.Instance] = {}

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


def save_instance_to_cache(instance: source.Instance) -> None:
    """
    Save an instance to the cache.

    :param instance: The instance to save.
    """
    cache[instance.source.name] = instance


def load_instance_from_cache(definition: source.Source) -> source.Instance | None:
    """
    Load instance from cached instances.

    :param defintion: The definition to load instance of from cache.
    :return: The instance if it is availabe; `None` otherwise.
    """
    return cache.get(definition.name)
