from .source import Source
from grawlix.book import Book, Metadata, ImageList, OnlineFile, Series, Result
from grawlix.exceptions import InvalidUrl, DataNotFound
from grawlix.logging import debug
from grawlix.utils import get_arg_from_url

import re
from urllib.parse import urlparse
from typing import Tuple, Optional

BASEURL = "https://reader.flipp.dk/html5/reader"

LANGUAGE_CODE_MAPPING = {
    "dk": "da-DK",
    "no": "nb-NO",
    "se": "sv-SE"
}

class Flipp(Source):
    name: str = "Flipp"
    match = [
        r"https?://reader.flipp.(dk|no|se)/html5/reader/production/default.aspx\?pubname=&edid=([^/]+)",
        r"https?://(magasiner|blader).flipp.(dk|no|se)/flipp/web-app/#/publications/.+"
    ]
    _authentication_methods: list[str] = []
    _login_cache: dict = {}



    async def download(self, url: str) -> Result:
        domain_extension = self.get_domain_extension(url)
        if re.match(self.match[0], url):
            issue_id = self._extract_issue_id(url)
            series_id = await self._get_series_id(issue_id)
            debug(f"{series_id=}")
            return await self._download_book(issue_id, series_id, domain_extension)
        elif re.match(self.match[1], url):
            return await self._download_series(url, domain_extension)
        raise InvalidUrl


    async def download_book_from_id(self, book_id: Tuple[str, str, str]) -> Book:
        series_id, issue_id, language_code = book_id
        return await self._download_book(issue_id, series_id, language_code)


    async def _download_series(self, url: str, language_code) -> Series:
        """
        Download series with book ids from Flipp

        :param url: Url of series
        :returns: Series object
        """
        series_id = url.split("/")[-1]
        login_info = await self._download_login_info(language_code)
        series_metadata = self._extract_series_data(login_info, series_id)
        issues = []
        for issue in series_metadata["issues"]:
            issue_id = issue["customIssueCode"]
            issues.append((series_id, issue_id, language_code))
        return Series(
            title = series_metadata["name"],
            book_ids = issues
        )


    async def _download_login_info(self, language_code: str) -> dict:
        """
        Download login info from Flipp
        Will use cache if available

        :returns: Login info
        """
        if language_code in self._login_cache:
            return self._login_cache[language_code]
        login_cache = await self._client.post(
            "https://flippapi.egmontservice.com/api/signin",
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:111.0) Gecko/20100101 Firefox/111.0"
            },
            json = {
                "email": "",
                "password": "",
                "token": "",
                "languageCulture": LANGUAGE_CODE_MAPPING[language_code],
                "appId": "",
                "appVersion": "",
                "uuid": "",
                "os": ""
            }
        )
        self._login_cache[language_code] = login_cache.json()
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


    async def _download_book(self, issue_id: str, series_id: str, language_code: str) -> Book:
        """
        Download book from Flipp

        :param issue_id: Issue identifier
        :param series_id: Series identifier
        :returns: Book metadata
        """
        pages = await self._get_pages(issue_id, series_id)
        metadata = await self._get_metadata(issue_id, series_id, language_code)
        return Book(
            data = ImageList(pages),
            metadata = Metadata(
                title = f"{metadata['series_name']} {metadata['issueName']}",
                series = metadata["series_name"],
                identifier = issue_id
            ),
        )


    async def _get_metadata(self, issue_id: str, series_id: str, language_code: str) -> dict:
        """
        Download and extract issue data

        :param issue_id: Issue id
        :param series_id: Series id
        :returns: Issue metadata
        """
        login_info = await self._download_login_info(language_code)
        series_metadata = self._extract_series_data(login_info, series_id)
        for issue in series_metadata["issues"]:
            if issue["customIssueCode"] == issue_id:
                issue["series_name"] = series_metadata["name"]
                return issue
        raise DataNotFound


    @staticmethod
    def get_domain_extension(url: str) -> str:
        """
        Extract domain extension from url

        :param url: Url to parse
        :returns: Domain extension of url
        """
        parsed_url = urlparse(url)
        extension = parsed_url.netloc.split(".")[-1]
        return extension


    @staticmethod
    def _extract_issue_id(url: str) -> str:
        """
        Extract eid from url

        :param url: Url to extract data from
        :returns: Eid in url
        """
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
