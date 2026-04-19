from grawlix.book import Book, Metadata
from grawlix.exceptions import DataNotFound, AccessDenied, SourceNotAuthenticated
from grawlix import logging, source
from grawlix.utils import http, option, blob

from typing import TypeAlias
import random
import string
from bs4 import BeautifulSoup
import asyncio
import json

Id: TypeAlias = str
State: TypeAlias = http.Client

SUPPORTED_URLS: list[str] = [
    r"https://archive.org/details/.+"
]


async def id_of_url(client: http.Client, url: str) -> Id:
    book_id = url.split("/")[4]
    return book_id


async def download_acsm(client: State, book_id: Id) -> bytes:
    await client.post(
        "https://archive.org/services/loans/loan/searchInside.php",
        data = {
            "action": "grant_access",
            "identifier": book_id
        }
    )
    await client.post(
        "https://archive.org/services/loans/loan/",
        data = {
            "action": "browse_book",
            "identifier": book_id
        }
    )
    # TODO: Error handling
    await client.post(
        "https://archive.org/services/loans/loan/",
        data = {
            "action": "create_token",
            "identifier": book_id
        }
    )
    acsm_response = await client.get(
        f"https://archive.org/services/loans/loan/?action=media_url&identifier={book_id}&format=pdf&redirect=1",
        follow_redirects = True
    )
    return acsm_response.content


async def download_metadata(state: State, book_id: Id) -> dict:
    page_response = await state.get(
        f"https://archive.org/details/{book_id}"
    )
    soup = BeautifulSoup(page_response.text, "lxml")
    reader_data = json.loads(soup.find(class_="js-bookreader").get("value"))
    metadata_url = f"https:{reader_data['url']}"
    logging.debug(f"{metadata_url=}")
    metadata_response = await state.get(
        metadata_url
    )
    return metadata_response.json()["data"]["metadata"]


async def download(client: http.Client, book_id: Id) -> Book:
    metadata, acsm_file = await asyncio.gather(
        download_metadata(client, book_id),
        download_acsm(client, book_id)
    )
    return Book(
        data = blob.Blob(
            content = acsm_file,
            format = blob.Format.Acsm,
        ),
        metadata = Metadata(
            title = metadata["title"],
            authors = option.to_list(metadata.get("creator")),
        ),
    )


SOURCE = source.Source(
    name = "Internet Archive",
    url_support = source.url_matches_regex(SUPPORTED_URLS),
    id_of_url = id_of_url,
    download = download,
    load_cookies = source.client_state_from_cookies,
)
