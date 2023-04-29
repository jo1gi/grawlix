from .source import Source
from grawlix.book import Book, Metadata, ImageList, OnlineFile, Series, Result
from grawlix.utils import get_arg_from_url
from grawlix.exceptions import InvalidUrl

from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:111.0) Gecko/20100101 Firefox/111.0"
MOBILE_USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"

class Webtoons(Source[str]):

    name: str = "Webtoons"
    match = [
        r"https://www.webtoons.com/../.+/.+/.+/viewer\?title_no=\d+&episode_no=\d+",
        r"https://www.webtoons.com/../.+/.+/list\?title_no=\d+"
    ]
    _authentication_methods: list[str] = []

    async def download(self, url: str) -> Result[str]:
        if re.match(self.match[0], url):
            return await self._download_episode(url)
        if re.match(self.match[1], url):
            return await self._download_series(url)
        raise InvalidUrl


    async def download_book_from_id(self, book_id: str) -> Book:
        return await self._download_episode(book_id)


    async def _download_series(self, url: str) -> Series[str]:
        """
        Download a series of webtoons

        :param url: Url of series
        :returns: Webtoons series data
        """
        parsed_url = urlparse(url)
        response = await self._client.get(
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
        episodes = []
        for episode in soup.find_all("li", class_="_episodeItem"):
            episode_link = episode.find("a").get("href")
            episodes.append(episode_link)
        return Series(
            title,
            book_ids = episodes
        )


    async def _download_episode(self, url: str) -> Book:
        """
        Download single webtoon episode

        :param url: Url of episode
        :returns: Episode
        """
        response = await self._client.get(url, follow_redirects = True)
        soup = BeautifulSoup(response.text, "lxml")
        title = soup.find("h1", class_="subj_episode").get("title")
        series = soup.find("div", class_="subj_info").find("a").get("title")
        images = []
        for image in soup.find("div", class_="viewer_img _img_viewer_area").find_all("img"):
            images.append(
                OnlineFile(
                    url = image.get("data-url"),
                    extension = "png",
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
