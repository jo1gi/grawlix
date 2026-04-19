from grawlix import logging, source, utils
from grawlix.book import Book, Metadata, ImageList, Series, Result, StandardBookId
from grawlix.exceptions import InvalidUrl
from grawlix.utils import blob, http

from typing import TypeAlias
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:111.0) Gecko/20100101 Firefox/111.0"
MOBILE_USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"

SUPPORTED_URLS = [
    r"https://www.webtoons.com/../.+/.+/.+/viewer\?title_no=\d+&episode_no=\d+",
    r"https://www.webtoons.com/../.+/.+/list\?title_no=\d+"
]

BookId: TypeAlias = StandardBookId[str]


async def instanciate(url: str) -> http.Client:
    return http.create_client()


async def id_from_url(state: http.Client, url: str) -> BookId:
    if re.match(SUPPORTED_URLS[0], url):
        return StandardBookId("book", url)
    if re.match(SUPPORTED_URLS[1], url):
        return StandardBookId("series", url)
    raise InvalidUrl


async def download_episode(state: http.Client, url: str) -> Book:
    """
    Download single webtoon episode

    :param state: The state.
    :param url: Url of episode.
    :returns: Episode
    """
    response = await state.get(url, follow_redirects = True)
    soup = BeautifulSoup(response.text, "lxml")
    title = soup.find("h1", class_="subj_episode").get("title")
    series = soup.find("div", class_="subj_info").find("a").get("title")
    images = []
    for image in soup.find("div", class_="viewer_img _img_viewer_area").find_all("img"):
        images.append(
            blob.request(
                url = image.get("data-url"),
                format = blob.Format.Png,
                headers = { "Referer": "https://www.webtoons.com/" }
            )
        )
    return Book(
        data = ImageList(images),
        metadata = Metadata(
            title,
            series = series
        )
    )


async def download_series(state: http.Client, url: str) -> Series[StandardBookId[str]]:
    """
    Download a series of webtoons

    :param state: The state
    :param url: Url of series
    :returns: Webtoons series data
    """
    parsed_url = urlparse(url)
    response = await state.get(
        f"https://m.webtoons.com{parsed_url.path}",
        params = parsed_url.query,
        headers = {
            "User-Agent": MOBILE_USER_AGENT,
        },
        cookies = {
            "needGDPR": "FALSE",
            "needCCPA": "FALSE",
            "needCOPPA": "FALSE"
        },
        follow_redirects = True,
    )
    soup = BeautifulSoup(response.text, "lxml")
    title = soup.find("meta", property="og:title").get("content")

    series_id = utils.get_arg_from_url(url, "title_no")
    response = await state.get(f"https://m.webtoons.com/api/v1/canvas/{series_id}/episodes?pageSize=1000")
    episodes = []
    for episode in response.json()["result"]["episodeList"]:
        path = episode["viewerLink"]
        episodes.append(StandardBookId("book", f"https://webtoons.com{path}"))

    return Series(
        title,
        book_ids = episodes
    )


async def download(state: http.Client, book_id: BookId) -> Result[StandardBookId[str]]:
    if book_id.variant == "book":
        return await download_episode(state, book_id.value)
    else:
        return await download_series(state, book_id.value)



SOURCE = source.Source[http.Client, BookId](
    name = "Webtoons",
    url_support = source.url_matches_regex(SUPPORTED_URLS),
    id_of_url = id_from_url,
    download = download,
    instanciate_without_login = instanciate,
)
