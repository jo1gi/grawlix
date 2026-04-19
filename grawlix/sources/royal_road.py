from .source import Source
from grawlix import source
from grawlix.book import Book, HtmlFile, HtmlFiles, Metadata
from grawlix.utils import http, blob

from bs4 import BeautifulSoup

SUPPORTED_URLS = [
    r"https://www.royalroad.com/fiction/\d+/[^/]+"
]

async def instanciate(url: str) -> http.Client:
    return http.create_client()


async def id_of_url(client: http.Client, url: str) -> str:
    return url


async def download(client: http.Client, url: str) -> Book:
    response = await client.get(url)
    soup = BeautifulSoup(response.text, "lxml")
    chapters = []
    for chapter in soup.find_all("tr", class_="chapter-row"):
        chapters.append(
            HtmlFile(
                title = chapter.find("a").text.strip(),
                file = blob.request(
                    url = f"https://royalroad.com{chapter.get('data-url')}",
                    format = blob.Format.Html,
                ),
                selector = { "class": "chapter-content" }
            )
        )
    return Book(
        data = HtmlFiles(
            cover = blob.request(
                url = soup.find("div", class_="cover-art-container") \
                    .find("img") \
                    .get("src") \
                    .replace("full", "large"),
                format = blob.Format.Jpg
            ),
            htmlfiles = chapters
        ),
        metadata = Metadata(
            title = soup.find("meta", attrs={"name":"twitter:title"}).get("content"),
            authors = [ soup.find("meta", attrs={"name":"twitter:creator"}).get("content") ]
        ),
        overwrite = True
    )


SOURCE = source.Source(
    name = "Royal Road",
    url_support = source.url_matches_regex(SUPPORTED_URLS),
    id_of_url = id_of_url,
    download = download,
    instanciate_without_login = instanciate,
)
