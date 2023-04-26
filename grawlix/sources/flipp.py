from .source import Source
from grawlix.book import Book, Metadata, ImageList, OnlineFile, Series, Result
from grawlix.exceptions import InvalidUrl, DataNotFound
from grawlix.utils import get_arg_from_url

import re
from urllib.parse import urlparse
from typing import Tuple, Optional

BASEURL = "https://reader.flipp.dk/html5/reader"

class Flipp(Source):
    name: str = "Flipp"
    match = [
        r"https?://reader.flipp.dk/html5/reader/production/default.aspx\?pubname=&edid=([^/]+)",
        r"https?://magasiner.flipp.dk/flipp/web-app/#/publications/.+"
    ]
    _authentication_methods: list[str] = []
    _login_cache: Optional[dict] = None

    async def download(self, url: str) -> Result:
        if re.match(self.match[0], url):
            eid = self._get_eid(url)
            publication_id = await self._get_series_id(eid)
            return await self._download_book(eid, publication_id)
        elif re.match(self.match[1], url):
            return await self._download_series(url)
        raise InvalidUrl


    async def download_book_from_id(self, book_id: Tuple[str, str]) -> Book:
        series_id, issue_id = book_id
        return await self._download_book(issue_id, series_id)


    async def _download_series(self, url: str) -> Series:
        """
        Download series with book ids from Flipp

        :param url: Url of series
        :returns: Series object
        """
        series_id = url.split("/")[-1]
        login_info = await self._download_login_info()
        series_metadata = self._extract_series_data(login_info, series_id)
        issues = []
        for issue in series_metadata["issues"]:
            issue_id = issue["customIssueCode"]
            issues.append((series_id, issue_id))
        return Series(
            title = series_metadata["name"],
            book_ids = issues
        )


    async def _download_login_info(self) -> dict:
        """
        Download login info from Flipp
        Will use cache if available

        :returns: Login info
        """
        if self._login_cache:
            return self._login_cache
        login_cache = await self._client.post(
            "https://flippapi.egmontservice.com/api/signin",
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:111.0) Gecko/20100101 Firefox/111.0"
            },
            json = {
                "email": "",
                "password": "",
                "token": "",
                "languageCulture": "da-DK",
                "appId": "",
                "appVersion": "",
                "uuid": "",
                "os": ""
            }
        )
        self._login_cache = login_cache.json()
        return login_cache.json()


    def _extract_series_data(self, response: dict, series_id: str) -> dict:
        """
        Extract metadata about series from login response

        :param response: Login response from Flipp
        :param series_id: Id of series
        :returns: Metadata about series
        """
        for publication in response["publications"]:
            if publication["customPublicationCode"] == series_id:
                return publication
        raise DataNotFound


    async def _download_book(self, issue_id: str, series_id: str) -> Book:
        """
        Download book from Flipp

        :param issue_id: Issue identifier
        :param series_id: Series identifier
        :returns: Book metadata
        """
        pages = await self._get_pages(issue_id, series_id)
        metadata = await self._get_metadata(issue_id, series_id)
        return Book(
            data = ImageList(pages),
            metadata = Metadata(
                title = f"{metadata['series_name']} {metadata['issueName']}",
                series = metadata["series_name"],
                identifier = issue_id
            ),
        )


    async def _get_metadata(self, issue_id: str, series_id: str) -> dict:
        """
        Download and extract issue data

        :param issue_id: Issue id
        :param series_id: Series id
        :returns: Issue metadata
        """
        login_info = await self._download_login_info()
        series_metadata = self._extract_series_data(login_info, series_id)
        for issue in series_metadata["issues"]:
            if issue["customIssueCode"] == issue_id:
                issue["series_name"] = series_metadata["name"]
                return issue
        raise DataNotFound

    def _get_eid(self, url: str) -> str:
        return get_arg_from_url(url, "edid")


    async def _get_series_id(self, issue_id: str) -> str:
        """
        Download series id from issue id

        :param issue_id: Issue id
        :returns: Series id
        """
        response = await self._client.get(f"{BASEURL}/production/default.aspx?pubname=&edid={issue_id}")
        # TODO Make faster
        search = re.search(r'publicationguid = "([^"]+)', response.text)
        if search is None:
            raise DataNotFound
        return search.group(1)


    async def _get_pages(self, issue_id: str, series_id: str) -> list[OnlineFile]:
        """
        Download page metadata for book

        :param issue_id: Issue id
        :param series_id: Series id
        :return: Page image links
        """
        response = await self._client.get(
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
