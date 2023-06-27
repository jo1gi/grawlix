from .source import Source
from grawlix.book import Book, HtmlFile, HtmlFiles, OnlineFile, Metadata

from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; rv:113.0) Gecko/20100101 Firefox/113.0"

class FanfictionNet(Source):
    name: str = "fanfiction.net"
    match = [
        r"https://www.fanfiction.net/s/\d+/\d+.*"
    ]
    _authentication_methods: list[str] = [ "cookies" ]

    async def download(self, url: str) -> Book:
        book_id = self._extract_id(url)
        response = await self._client.get(
            f"https://www.fanfiction.net/s/{book_id}/1",
            headers = {
                "User-Agent": USER_AGENT
            }
        )
        soup = BeautifulSoup(response.text, "lxml")
        chapters = []
        for index, chapter in enumerate(soup.find(id="chap_select").find_all("option")):
            chapters.append(
                HtmlFile(
                    title = chapter.text,
                    file = OnlineFile(
                        url = f"https://www.fanfiction.net/s/{book_id}/{index+1}",
                        extension = "html",
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:113.0) Gecko/20100101 Firefox/113.0",
                        },
                        cookies = self._client.cookies
                    ),
                    selector = { "id": "storytext" }
                )
            )
        return Book(
            data = HtmlFiles(htmlfiles = chapters),
            metadata = Metadata(
                title = soup.find("b", class_="xcontrast_txt").text,
            )
        )

    @staticmethod
    def _extract_id(url: str) -> str:
        """
        Extracts book id from url

        :param url: Url of book
        :returns: Id of book
        """
        return url.split("/")[4]
