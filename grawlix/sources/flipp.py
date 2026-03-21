from grawlix.book import Book, Metadata, ImageList, OnlineFile, Series, Result
from grawlix.exceptions import InvalidUrl, DataNotFound
from grawlix import logging, source, utils

from dataclasses import dataclass
import re
from urllib.parse import urlparse
from typing import Tuple, Optional, TypeAlias
import httpx

BASEURL = "https://reader.flipp.dk/html5/reader"

LANGUAGE_CODE_MAPPING = {
    "dk": "da-DK",
    "no": "nb-NO",
    "se": "sv-SE"
}

SUPPORTED_URLS = [
    r"https?://reader.flipp.(dk|no|se)/html5/reader/(production|stage)/default.aspx\?pubname=&edid=([^/]+)",
    r"https?://(magasiner|blader).flipp.(dk|no|se)/flipp/web-app/#/publications/.+"
]

@dataclass(slots=True)
class BookId:
    issue_id: str | None
    series_id: str
    tld: str


@dataclass(slots=True)
class State:
    client: httpx.AsyncClient
    index_cache: dict


async def instanciate(url: str) -> State:
    return State(
        client = httpx.AsyncClient(),
        index_cache = {}
    )


async def id_of_url(state: State, url: str) -> BookId:
    tld = utils.extract_top_level_domain(url)

    if re.match(SUPPORTED_URLS[0], url):
        issue_id = utils.get_arg_from_url(url, "edid")

        # Download series id
        # TODO Make faster
        response = await state.client.get(f"{BASEURL}/stage/default.aspx?pubname=&edid={issue_id}", timeout = 20.)
        search = re.search(r'publicationguid = "([^"]+)', response.text)
        if search is None:
            raise DataNotFound
        series_id = search.group(1)
        return BookId(issue_id, series_id, tld)

    if re.match(SUPPORTED_URLS[1], url):
        series_id = url.split("/")[-1]
        return BookId(None, series_id, tld)

    raise InvalidUrl


async def download_index(state: State, tld: str) -> dict:
    """
    Download the index of the books and series for the language.

    :param state: The state of the source.
    :param tld: The top level domain of the flipp site.
    :returns: The index.
    """
    # The index takes a long time to download and contains a lot of data
    if tld in state.index_cache:
        return state.index_cache[tld]

    index = await state.client.post(
        "https://flippapi.egmontservice.com/api/signin",
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:111.0) Gecko/20100101 Firefox/111.0"
        },
        json = {
            "email": "",
            "password": "",
            "token": "",
            "languageCulture": LANGUAGE_CODE_MAPPING[tld],
            "appId": "",
            "appVersion": "",
            "uuid": "",
            "os": ""
        }
    )
    state.index_cache[tld] = index.json()
    return index.json()

async def get_pages(state: State, issue_id: str, series_id: str) -> list[OnlineFile]:
    """
    Download page metadata for book

    :param issue_id: Issue id
    :param series_id: Series id
    :return: Page image links
    """
    response = await state.client.get(
        f"{BASEURL}/get_page_groups_from_eid.aspx?pubid={series_id}&eid={issue_id}",
    )
    result = []
    for page in response.json()["pageGroups"]:
        # Find image id in low quality image url
        low_quality_url = urlparse(page["pages"][0]["image"])
        image_id = low_quality_url.path[1:-9]
        high_quality_url = f"http://pages.cdn.pagesuite.com/{image_id}/highpage.jpg?method=true"
        result.append(OnlineFile(high_quality_url, "jpg"))
    return result


def extract_series_metadata(index: dict, series_id: str) -> dict:
    """
    Extract information about the series from the index.

    :param index: The index of series from Flipp.
    :parmam series_id: The series identifier.
    :returns: The series metadata
    """
    for publication in index["publications"]:
        if publication["customPublicationCode"] == series_id:
            return publication
    raise DataNotFound


async def download_book(state: State, issue_id: str, series_id: str, tld: str) -> Book:
    """
    Download book from Flipp

    :param issue_id: Issue identifier
    :param series_id: Series identifier
    :returns: Book metadata
    """
    index = await download_index(state, tld)
    pages = await get_pages(state, issue_id, series_id)
    series_metadata = extract_series_metadata(index, series_id)

    for issue in series_metadata["issues"]:
        if issue["customIssueCode"] == issue_id:
            issue["series_name"] = series_metadata["name"]
            issue_metadata = issue
            break
    if issue_metadata is None:
        raise DataNotFound

    return Book(
        data = ImageList(pages),
        metadata = Metadata(
            title = f"{issue_metadata['series_name']} {issue_metadata['issueName']}",
            series = issue_metadata["series_name"],
            identifier = issue_id
        ),
    )


async def download_series(state: State, series_id: str, tld: str) -> Series:
    index = await download_index(state, tld)
    metadata = extract_series_metadata(index, series_id)

    issues = []
    for issue in metadata["issues"]:
        issue_id = issue["customIssueCode"]
        issues.append(BookId(issue_id, series_id, tld))

    return Series(
        title = metadata["name"],
        book_ids = issues
    )


async def download(state: State, book_id: BookId) -> Result:
    if book_id.issue_id is not None:
        return await download_book(state, book_id.issue_id, book_id.series_id, book_id.tld)
    else:
        return await download_series(state, book_id.series_id, book_id.tld)


SOURCE = source.Source[State, BookId](
    name = "Flipp",
    url_support = source.url_matches_regex(SUPPORTED_URLS),
    id_of_url = id_of_url,
    download = download,
    instanciate_without_login = instanciate,
)
