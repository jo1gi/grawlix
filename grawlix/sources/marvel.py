from grawlix.book import Book, Metadata, ImageList, OnlineFile, Series, Result
from grawlix.exceptions import InvalidUrl, DataNotFound
from grawlix import logging

from .source import Source

import re
from datetime import date

# Personal marvel ip key
API_KEY = "83ac0da31d3f6801f2c73c7e07ad76e8"

class Marvel(Source[str]):
    name: str = "Marvel"
    match = [
        r"https://www.marvel.com/comics/issue/\d+/.+",
        r"https://read.marvel.com/#/book/\d+",
        r"https://www.marvel.com/comics/series/\d+/.+"
    ]
    _authentication_methods: list[str] = [ "cookies" ]


    async def download(self, url: str) -> Result[str]:
        match_index = self.get_match_index(url)
        if match_index == 0:
            issue_id = await self._get_issue_id(url)
            return await self.download_book_from_id(issue_id)
        if match_index == 1:
            issue_id = url.split("/")[-1]
            return await self.download_book_from_id(issue_id)
        if match_index == 2:
            return await self._download_series(url)
        raise InvalidUrl


    async def _download_series(self, url: str) -> Series[str]:
        """
        Download series

        :param url: Url of series
        :returns: Series data
        """
        series_id = url.split("/")[-2]
        issue_ids = await self._download_issue_ids(series_id)
        metadata = await self._download_series_metadata(series_id)
        return Series(
            title = metadata["data"]["results"][0]["title"],
            book_ids = issue_ids
        )


    async def _download_issue_ids(self, series_id: str) -> list[str]:
        """
        Download issue ids from series

        :param series_id: Id of comic series on marvel.com
        :returns: List of comic ids for marvel comics
        """
        response = await self._client.get(
            f"https://api.marvel.com/browse/comics?byType=comic_series&isDigital=1&limit=10000&byId={series_id}",
        )
        issue_ids = [issue["digital_id"] for issue in response.json()["data"]["results"]]
        return issue_ids


    async def _download_series_metadata(self, series_id: str) -> dict:
        """
        Download series metadata

        :param series_id: Id of comic series on marvel.com
        :returns: Dictionary with metadata
        """
        response = await self._client.get(
            f"https://gateway.marvel.com:443/v1/public/series/{series_id}?apikey={API_KEY}",
            headers = {
                "Referer": "https://developer.marvel.com/"
            }
        )
        return response.json()

    async def _get_issue_id(self, url: str) -> str:
        """
        Download issue id from url

        :param url: Url to issue info page
        :return: Issue id
        """
        response = await self._client.get(url)
        search = re.search(r"digital_comic_id: \"(\d+)\"", response.text)
        if not search:
            raise DataNotFound
        return search.group(1)



    async def download_book_from_id(self, issue_id: str) -> Book:
        return Book(
            metadata = await self._download_issue_metadata(issue_id),
            data = await self._download_issue_pages(issue_id)
        )


    async def _download_issue_metadata(self, issue_id: str) -> Metadata:
        """
        Download and parse metadata for issue

        :param issue_id: Identifier for issue
        :returns: Issue metadata
        """
        response = await self._client.get(
            f"https://bifrost.marvel.com/v1/catalog/digital-comics/metadata/{issue_id}"
        )
        issue_meta = response.json()["data"]["results"][0]["issue_meta"]
        return Metadata(
            title = issue_meta["title"],
            series = issue_meta.get("series_title"),
            description = issue_meta.get("description"),
            publisher = "Marvel",
            release_date = date.fromisoformat(issue_meta.get("release_date_digital")),
            authors = [c["full_name"] for c in issue_meta["creators"]["extended_list"]] if "extended_list" in issue_meta["creators"] else []
        )


    async def _download_issue_pages(self, issue_id: str) -> ImageList:
        """
        Download list of page links for issue

        :param issue_id: Identifier for issue
        :returns: List of links to comic pages
        """
        response = await self._client.get(
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
        return ImageList(images)
