from .source import Source
from grawlix.encryption import XOrEncryption
from grawlix.book import Book, Metadata, ImageList, OnlineFile, Series, Result
from grawlix.exceptions import InvalidUrl

import re
import blackboxprotobuf
import json
import rich

class MangaPlus(Source):
    name: str = "Manga Plus"
    match = [
        r"https?://mangaplus.shueisha.co.jp/viewer/\d+",
        r"https?://mangaplus.shueisha.co.jp/titles/\d+"
    ]
    _authentication_methods: list[str] = []


    async def download(self, url: str) -> Result:
        if re.match(self.match[0], url):
            issue_id = url.split('/')[-1]
            return await self._download_issue(issue_id)
        if re.match(self.match[1], url):
            series_id = url.split("/")[-1]
            return await self._download_series(series_id)
        raise InvalidUrl


    async def download_book_from_id(self, book_id: str) -> Book:
        return await self._download_issue(book_id)


    async def _download_series(self, series_id: str) -> Series:
        """
        Download series from Manga Plus

        :param series_id: Identifier for series
        :returns: Series data
        """
        response = await self._client.get(
            f"https://jumpg-api.tokyo-cdn.com/api/title_detailV2",
            params = {
                "title_id": series_id,
                "lang": "eng",
                "os": "android",
                "os_ver": "32",
                "app_ver": "40",
                "secret": "2afb69fbb05f57a1856cf75e1c4b6ee6"
            },
        )
        data, _ = blackboxprotobuf.protobuf_to_json(response.content)
        parsed = json.loads(data)
        title = parsed["1"]["8"]["1"]["2"]
        issues = []
        def add_issues(data: dict, main: str):
            if main in data:
                x = data[main]
                if isinstance(x, list):
                    for i in x:
                        issues.append(i["2"])
                else:
                    issues.append(x["2"])
        for a in parsed["1"]["8"]["28"]:
            add_issues(a, "2")
            add_issues(a, "3")
            add_issues(a, "4")
        return Series(
            title,
            book_ids = issues
        )

    async def _download_issue(self, issue_id: str) -> Book:
        """
        Download issue from Manga Plus

        :param issue_id: Identifier for issue
        :returns: Issue metadata
        """
        url = f"https://jumpg-webapi.tokyo-cdn.com/api/manga_viewer?chapter_id={issue_id}&split=yes&img_quality=super_high"
        response = await self._client.get(url)
        content, _ = blackboxprotobuf.protobuf_to_json(response.content)
        images = []
        parsed = json.loads(content)
        for image in parsed["1"]["10"]["1"]:
            if "1" in image:
                images.append(
                    OnlineFile(
                        image["1"]["1"],
                        extension = "jpg",
                        encryption = XOrEncryption(bytes.fromhex(image["1"]["5"]))
                    )
                )
            elif "3" in image:
                title = image["3"]["1"]["4"]
        return Book(
            data = ImageList(images),
            metadata = Metadata(
                title,
                series = parsed["1"]["10"]["5"]
            )
        )
