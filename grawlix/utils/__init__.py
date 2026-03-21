from grawlix.exceptions import DataNotFound

from urllib.parse import urlparse, parse_qs
import importlib.resources


def extract_top_level_domain(url: str) -> str:
    """
    Extract the top level domain from an url.

    :param url: The url to extract the tld from.
    :returns: The tld.
    """
    parsed_url = urlparse(url)
    tld = parsed_url.netloc.split(".")[-1]
    return tld


def get_arg_from_url(url: str, key: str) -> str:
    """
    Get a url parameter from the url.

    :param url: The url to extract the parameter from.
    :param key: the key of the parameter.
    :returns: the value of the parameter.
    """
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    try:
        return query[key][0]
    except:
        raise DataNotFound


def read_asset_file(path: str) -> str:
    """
    Read asset file from the grawlix module

    :param path: Path relative to root of grawlix module
    """
    return importlib.resources.files("grawlix") \
        .joinpath(path) \
        .read_text(encoding="utf8")
