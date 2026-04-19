from .source import Source
from grawlix import source, logging
from grawlix.book import Book, Metadata, ImageList, Series, Result, StandardBookId
from grawlix.encryption import XOrEncryption
from grawlix.exceptions import InvalidUrl
from grawlix.utils import blob, http

import re
import blackboxprotobuf
import json
from typing import TypeAlias

SUPPORTED_URLS = [
    r"https?://mangaplus.shueisha.co.jp/viewer/\d+",
    r"https?://mangaplus.shueisha.co.jp/titles/\d+"
]

Id: TypeAlias = StandardBookId[str]

async def instanciate(url: str) -> http.Client:
    return http.create_client()


async def id_of_url(client: http.Client, url: str) -> Id:
    if re.match(SUPPORTED_URLS[0], url):
        issue_id = url.split('/')[-1]
        return StandardBookId("book", issue_id)
    if re.match(SUPPORTED_URLS[1], url):
        series_id = url.split("/")[-1]
        return StandardBookId("series", series_id)
    raise InvalidUrl


async def download_issue(client: http.Client, issue_id: str) -> Book:
    response = await client.get(
        f"https://jumpg-webapi.tokyo-cdn.com/api/manga_viewer",
        params = {
            "chapter_id": issue_id,
            "split": "yes",
            "img_quality": "super_high"
        }
    )
    content, _ = blackboxprotobuf.protobuf_to_json(response.content)
    images = []
    parsed = json.loads(content)
    for image in parsed["1"]["10"]["1"]:
        if "1" in image:
            images.append(
                blob.request(
                    url = image["1"]["1"],
                    format = blob.Format.Jpg,
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


async def download_series(client: http.Client, series_id: str) -> Series[Id]:
    """
    Download series from Manga Plus.

    :param client: An http client.
    :param series_id: Identifier for series.
    :returns: Series data.
    """
    response = await client.get(
        "https://jumpg-webapi.tokyo-cdn.com/api/title_detailV3",
        params = {
            "title_id": series_id,
            "clang": "eng",
            "os": "android",
            "os_ver": "32",
            "app_ver": "42",
            "secret": "2afb69fbb05f57a1856cf75e1c4b6ee6"
        },
    )
    data, _ = blackboxprotobuf.protobuf_to_json(response.content)
    parsed = json.loads(data)
    title = parsed["1"]["8"]["1"]["2"]

    issues = []
    def add_issues(data: dict, main: str):
        """
        Add ids to `issues`.
        """
        if main in data:
            x = data[main]
            if isinstance(x, list):
                for i in x:
                    issues.append(StandardBookId("book", i["2"]))
            else:
                issues.append(StandardBookId("book", x["2"]))

    for a in parsed["1"]["8"]["28"]:
        add_issues(a, "2")
        add_issues(a, "3")
        add_issues(a, "4")

    return Series(
        title,
        book_ids = issues
    )


async def download(client: http.Client, id: Id) -> Result[Id]:
    if id.variant == "book":
        return await download_issue(client, id.value)
    else:
        return await download_series(client, id.value)


SOURCE = source.Source(
    name = "Manga Plus",
    url_support = source.url_matches_regex(SUPPORTED_URLS),
    id_of_url = id_of_url,
    download = download,
    instanciate_without_login = instanciate,
)
