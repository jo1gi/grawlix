from grawlix import logging, source
from grawlix.book import Result, Book, Metadata, ImageList
from grawlix.exceptions import DataNotFound
from grawlix.utils import http, blob
from typing import TypeAlias

import hashlib

State: TypeAlias = http.Client

SUPPORTED_URLS = [
    r"https://globalcomix.com/read/.+"
]


async def login(url: str, username: str, password: str) -> State:
    client = http.create_client()
    client.headers.update({
        "X-Gc-Client": "gck_b4d492261ec541eda44ce41de79da424",
        "X-Gc-Identmode": "cookie"
    })
    password_and_salt = f"{password}differenthash".encode("utf-8")
    password_hash = hashlib.sha256(password_and_salt).hexdigest()
    logging.debug(f"{password_hash=}")
    login_response = await client.post(
        "https://api.globalcomix.com/v1/auth/request-token",
        json = {
            "meta": {},
            "payload": {
                "email": username,
                "password_hash": password_hash
            }
        }
    )
    logging.trace(f"{login_response.json()=}")
    return client


async def id_of_url(state: State, url: str) -> str:
    return url.split("/")[4]


async def download_book(state: State, book_id: str) -> Book:
    response = await state.get(
        f"https://api.globalcomix.com/v1/readV2/{book_id}"
    )
    metadata = response.json()["payload"]["results"]

    images = []
    for image in metadata["page_objects"]:
        images.append(
            blob.request(
                url = image["desktop_image_url"],
                format = blob.Format.Jpg
            )
        )

    return Book(
        data = ImageList(images),
        metadata = Metadata(
            title = metadata["title"],
            description = metadata["description"],
            series = metadata["comic_name"],
            index = metadata["chapter"],
            language = metadata["lang_id"],
        )
    )


async def download(state: State, id: str) -> Result:
    return await download_book(state, id)


SOURCE = source.Source(
    name = "GlobalComix",
    url_support = source.url_matches_regex(SUPPORTED_URLS),
    login = login,
    id_of_url = id_of_url,
    download = download,
)
