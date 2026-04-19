from grawlix import logging, source
from grawlix.book import Book, Metadata, Result, Series
from grawlix.exceptions import SourceNotAuthenticated, InvalidUrl, DataNotFound
from grawlix.utils import http, blob
from .source import Source

import re
from urllib.parse import urlparse
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from typing import Any, Literal
from dataclasses import dataclass

VERSION = "23.49"

SUPPORTED_URLS = [
    r"https?://(?:www.)?(?:storytel|mofibo).com/(?P<language>\w+)(?:/(?P<language2>\w+))?/(?P<list_type>(?:books|series|authors|narrators|publishers|categories))/.+",
]

@dataclass(slots=True)
class State:
    client: http.Client
    username: str
    password: str
    download_counter: int = 0


@dataclass(slots=True)
class Id:
    variant: Literal["books", "series", "authors", "narrators"]
    value: str


async def authenticate(state: State):
    """Authenticates with storytel"""
    if not state.download_counter % 10 == 0:
        return
    response = await state.client.post(
        f"https://www.storytel.com/api/login.action",
        params = {
            "m": "1", "token": "guestsv", "userid": "-1", "version": VERSION,
            "terminal": "android", "locale": "sv", "deviceId":
            "995f2562-0e44-4410-b1b9-8d08261f33c4", "kidsMode": "false"
        },
        data = {
            "uid": state.username,
            "pwd": state.password
        }
    )
    if response.status_code != 200:
        raise SourceNotAuthenticated
    user_data = response.json()
    jwt = user_data["accountInfo"]["jwt"]
    state.client.headers.update({"authorization": f"Bearer {jwt}"})


async def login(url: str, username: str, password: str) -> State:
    """
    Login to Storytel. It stores the username and password (the password is in
    an encrypted for) and reauthenticates periodically when downloading to keep
    up to date authentication tokens.

    :param url: The url from storytel (unused)
    :param username: The username/email of the user
    :param password: The password of the user
    :return: An authenticated state
    """
    client = http.create_client()
    client.headers.update({
        "User-Agent": f"Storytel/{VERSION} (Android 13; Pixel 6) Release/2288481"
    })

    # Encrypt the password with predefined keys
    # Thanks to https://github.com/javsanpar/storytel-tui
    key = b"VQZBJ6TD8M9WBUWT"
    iv = b"joiwef08u23j341a"
    msg = pad(password.encode(), AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_password = cipher.encrypt(msg).hex()

    state = State(client, username, encrypted_password)
    await authenticate(state)
    return state


async def id_of_url(state: State, url: str) -> Id:
    if m := re.match(SUPPORTED_URLS[0], url):
        language, language2, list_type = m.groups()
        if list_type not in ["books", "series", "authors" "narrators"]:
            raise InvalidUrl

        parsed_url = urlparse(url)
        if parsed_url.path is None:
            raise InvalidUrl
        id = parsed_url.path.split("-")[-1]

        return Id(list_type, id) #type: ignore
    raise InvalidUrl


async def download_book(state: State, book_id: str) -> Book:
    # Epub location
    response = await state.client.get(
        f"https://api.storytel.net/assets/v2/consumables/{book_id}/ebook",
    )
    state.download_counter += 1
    epub_url = response.headers["Location"]

    # Book details
    response = await state.client.get(
        f"https://api.storytel.net/book-details/consumables/{book_id}?kidsMode=false&configVariant=default"
    )
    details = response.json()

    return Book(
        metadata = Metadata(
            title = details["title"]
        ),
        data = blob.request(
            url = epub_url,
            format = blob.Format.Epub,
            headers = state.client.headers
        )
    )


async def download_list(state: State, list_type: str, list_id: str) -> Series[Id]:
    nextPageToken = 0

    # API returns only 10 items per request
    # if the nextPageToken
    result: dict[str, Any] = {"nextPageToken": False}

    while result["nextPageToken"] is not None:
        params: dict[str, str] = {
            "includeListDetails": "true",  # include listMetadata,filterOptions,sortOption sections
            "includeFormats": "ebooks",
            # "includeLanguages": languages,
            "kidsMode": "false",
        }
        if result["nextPageToken"]:
            params["nextPageToken"] = result["nextPageToken"]

        response = await state.client.get(
            f"https://api.storytel.net/explore/lists/{list_type}/{list_id}",
            params=params,
        )

        data = response.json()
        if result["nextPageToken"] == 0:
            result = data
        else:
            result["items"].extend(data["items"])
            result["nextPageToken"] = data["nextPageToken"]
        logging.debug(f"{result=}")

    books: list[Id] = [
        Id("books", item["id"])
        for item in result["items"]
        if "ebook" in [format["type"] for format in item["formats"]]
    ]

    return Series(
        title = result["title"],
        book_ids = books
    )


async def download(state: State, id: Id) -> Result[Id]:
    await authenticate(state)
    if id.variant == "books":
        return await download_book(state, id.value)
    else:
        return await download_list(state, id.variant, id.value)


SOURCE = source.Source(
    name = "Storytel",
    url_support = source.url_matches_regex(SUPPORTED_URLS),
    login = login,
    id_of_url = id_of_url,
    download = download,
)
