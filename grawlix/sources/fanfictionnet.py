from grawlix import source
from grawlix.book import Book, HtmlFile, HtmlFiles, OnlineFile, Metadata
from grawlix.utils import http

from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; rv:113.0) Gecko/20100101 Firefox/113.0"

SUPPORTED_URLS = [
    r"https://www.fanfiction.net/s/\d+/\d+.*"
]

async def id_of_url(client: http.Client, url: str) -> str:
    return url.split("/")[4]


async def download(client: http.Client, book_id: str) -> Book:
    response = await client.get(
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
                        "User-Agent": USER_AGENT,
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


SOURCE = source.Source(
    name = "fanfiction.net",
    url_support = source.url_matches_regex(SUPPORTED_URLS),
    id_of_url = id_of_url,
    download = download,
    load_cookies = source.client_state_from_cookies
)
