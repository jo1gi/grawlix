from grawlix.book import Book, Metadata, ImageList, OnlineFile, Series, Result, StandardBookId
from grawlix.exceptions import InvalidUrl, DataNotFound
from grawlix import logging, source
from grawlix.utils import http

from .source import Source

from bs4 import BeautifulSoup
from datetime import date
import re

SUPPORTED_URLS = [
    r"https://www.marvel.com/comics/issue/\d+/.+",
    r"https://read.marvel.com/#/book/\d+",
    r"https://www.marvel.com/comics/series/\d+/.+"
]


async def id_of_url(client: http.Client, url: str) -> StandardBookId[str]:
    if re.match(SUPPORTED_URLS[0], url):
        response = await client.get(url)
        search = re.search(r"\"digitalComicID\":(\d+)", response.text)
        if not search:
            raise DataNotFound
        issue_id = search.group(1)
        return StandardBookId("book", issue_id)

    if re.match(SUPPORTED_URLS[1], url):
        issue_id = url.split("/")[-1]
        return StandardBookId("book", issue_id)

    if re.match(SUPPORTED_URLS[2], url):
        series_id = url.split("/")[-2]
        return StandardBookId("series", series_id)

    raise InvalidUrl


async def download_series(client: http.Client, series_id: str) -> Series:
    """
    Download information about a series from Marvel.

    :param client: The http client.
    :param series_id: The id of the series to download from.
    :returns: The series data
    """
    response = await client.get(
        f"https://bifrost.marvel.com/v1/catalog/comics/mu?",
        params = {
            "byId": series_id,
            "byZone": "marvel_site_zone", "byType": "comic_series", "orderBy":
            "release_date+desc", "formatType":
            "issue,digitalcomic,collection,digitalverticalcomic", "limit":
            10000, "offset": 0, "variants": "false"
        },
        timeout = 20.,
    )
    issue_ids = [
        StandardBookId("book", issue["digital_id"]) for issue in response.json()["data"]["results"]
    ]

    response = await client.get(
        f"https://www.marvel.com/comics/series/{series_id}/"
    )
    soup = BeautifulSoup(response.text, "lxml")
    header = soup.find("h1")
    if header is None:
        raise DataNotFound
    title = header.get_text()

    return Series(
        title = title,
        book_ids = issue_ids
    )


async def download_issue(client: http.Client, issue_id: str) -> Book:
    """
    Download information about an issue from Marvel.

    :param client: The authneticated http client.
    :param issue_id: The id of the issue to download.
    :return: Information about the issue.
    """
    response = await client.get(
        f"https://bifrost.marvel.com/v1/catalog/digital-comics/metadata/{issue_id}"
    )
    issue_meta = response.json()["data"]["results"][0]["issue_meta"]

    if "extended_list" in issue_meta["creators"]:
        authors = [
            c["full_name"]
            for c in issue_meta["creators"]["extended_list"]
        ]
    else:
        authors = []

    metadata = Metadata(
        title = issue_meta["title"],
        series = issue_meta.get("series_title"),
        description = issue_meta.get("description"),
        publisher = "Marvel",
        release_date = date.fromisoformat(issue_meta.get("release_date_digital")),
        authors = authors,
    )

    response = await client.get(
        f"https://bifrost.marvel.com/v1/catalog/digital-comics/web/assets/{issue_id}"
    )

    images = []
    for page in response.json()["data"]["results"][0]["pages"]:
        images.append(
            OnlineFile(
                url = page["assets"]["source"],
                extension = "jpg"
            )
        )

    return Book(
        metadata = metadata,
        data = ImageList(images),
    )


async def download(client: http.Client, id: StandardBookId[str]) -> Result:
    if id.variant == "book":
        return await download_issue(client, id.value)
    else:
        return await download_series(client, id.value)


SOURCE = source.Source(
    name = "Marvel",
    url_support = source.url_matches_regex(SUPPORTED_URLS),
    id_of_url = id_of_url,
    download = download,
    load_cookies = source.client_state_from_cookies,
)
