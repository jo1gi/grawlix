from grawlix.exceptions import DataNotFound

from urllib.parse import urlparse, parse_qs

def get_arg_from_url(url: str, key: str) -> str:
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    try:
        return query[key][0]
    except:
        raise DataNotFound
