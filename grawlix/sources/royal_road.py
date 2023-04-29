from .source import Source
from grawlix.book import Book, HtmlFile, HtmlFiles, OnlineFile, Metadata

from bs4 import BeautifulSoup

class RoyalRoad(Source):
    name: str = "Royal Road"
    match = [
        r"https://www.royalroad.com/fiction/\d+/[^/]+"
    ]
    _authentication_methods: list[str] = []


    async def download(self, url: str) -> Book:
        response = await self._client.get(url)
        soup = BeautifulSoup(response.text, "lxml")
        chapters = []
        for chapter in soup.find_all("tr", class_="chapter-row"):
            chapters.append(
                HtmlFile(
                    title = chapter.find("a").text.strip(),
                    file = OnlineFile(
                        url = f"https://royalroad.com{chapter.get('data-url')}",
                        extension = "html"
                    ),
                    selector = { "class": "chapter-content" }
                )
            )
        return Book(
            data = HtmlFiles(
                cover = OnlineFile(
                    url = soup.find("div", class_="cover-art-container") \
                        .find("img") \
                        .get("src") \
                        .replace("full", "large"),
                    extension = "jpg"
                ),
                htmlfiles = chapters
            ),
            metadata = Metadata(
                title = soup.find("meta", attrs={"name":"twitter:title"}).get("content"),
                authors = [ soup.find("meta", attrs={"name":"twitter:creator"}).get("content") ]
            ),
            overwrite = True
        )
