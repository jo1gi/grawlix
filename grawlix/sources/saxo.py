from grawlix.book import Book, Metadata, SingleFile, OnlineFile
from grawlix import source, AESEncryption
from grawlix.exceptions import ThrottleError, InvalidUrl
from grawlix.utils import http, option

import re
from .source import Source
from dataclasses import dataclass

SUPPORTED_URLS = [
    r"https://(\w+\.)?saxo.(com|dk)/.+\d+$"
]


@dataclass(slots=True)
class State:
    client: http.Client
    user_id: str


async def login(url: str, username: str, password: str) -> State:
    client = http.create_client()
    response = await client.post(
        "https://auth-read.saxo.com/auth/token",
        data = {
            "username": username,
            "password": password,
            "grant_type": "password",
        },
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    json = response.json()
    bearer_token = json["access_token"]
    client.headers = {
        "Appauthorization": f"bearer {bearer_token}",
        "App-Os": "android",
        "App-Version": "6.2.4"
    }
    user_id = json["id"]
    return State(client, user_id)


async def id_of_url(state: State, url: str) -> str:
    isbn_match = re.search(r"\d+$", url)
    if not isbn_match or not isbn_match.group():
        raise InvalidUrl
    isbn = isbn_match.group()

    response = await state.client.get(
        f"https://api-read.saxo.com/api/v2/search/user/{state.user_id}/premium/books/{isbn}"
    )
    return response.json()["items"][0]["bookId"]


async def download(state: State, book_id: str) -> Book:
    response = await state.client.get(
        f"https://api-read.saxo.com/api/v2/book/{book_id}/user/{state.user_id}/details"
    )
    metadata = response.json()["ebooks"][0]
    ebook_id = metadata["id"]

    response = await state.client.get(
        f"https://api-read.saxo.com/api/v1/book/{ebook_id}/content/encryptedstream/"
    )
    json = response.json()
    if not "link" in json:
        raise ThrottleError
    url = json["link"]

    return Book(
        metadata = Metadata(
            title = metadata["title"],
            authors = option.to_list(metadata.get("author")),
            language = metadata.get("languageLocalized")
        ),
        data = SingleFile(
            OnlineFile(
                url = url,
                extension = "epub",
                # Encryption keys extracted from app
                encryption = AESEncryption(
                    key = b"CD3E9D141D8EFC0886912E7A8F3652C4",
                    iv = b"78CB354D377772F1"
                )
            )
        )
    )


SOURCE = source.Source(
    name = "Saxo",
    url_support = source.url_matches_regex(SUPPORTED_URLS),
    id_of_url = id_of_url,
    download = download,
    login = login,
)
