from grawlix import logging, source
from grawlix.book import Result, Book, Metadata, ImageList, Series, StandardBookId
from grawlix.encryption import Encryption
from grawlix.exceptions import InvalidUrl, AccessDenied, SourceNotAuthenticated
from grawlix.utils import blob, http
from .source import Source

import re
from typing import Tuple, List, TypeAlias
from hashlib import sha256
from Crypto.Cipher import AES

SUPPORTED_URLS = [
    # Reader page
    r"https://www.dcuniverseinfinite.com/comics/book/[^/]+/[^/]+/c/reader",
    # Issue info page
    r"https://www.dcuniverseinfinite.com/comics/book/[^/]+/[^/]+/c",
    r"https://www.dcuniverseinfinite.com/comics/book/-/[^/]",
    # Series info page
    r"https://www.dcuniverseinfinite.com/comics/series/[^/]+/[^/]+"
]


async def authenticate_client(client: http.Client, auth_token: str):
    """
    Authenticate the client using a authorization token.

    :param client: The client to authenticate.
    :param auth_token: The authorization token.
    """
    response = await client.get(
        "https://www.dcuniverseinfinite.com/api/5/consumer/www?trans=en"
    )
    consumer_secret = response.json()["consumer_secret"]

    client.headers.update({
        "Authorization": f"Token {auth_token}",
        "X-Consumer-Key": consumer_secret,
    })


async def login(url: str, username: str, auth_token: str) -> http.Client:
    client = http.create_client()
    await authenticate_client(client, auth_token)
    return client


async def load_cookies(cookie_file: str) -> http.Client:
    client = http.create_client()
    http.load_cookies(client, cookie_file)
    auth_token = client.cookies.get("session")
    if auth_token is None:
        raise SourceNotAuthenticated
    await authenticate_client(client, auth_token)
    return client


async def id_of_url(client: http.Client, url: str) -> StandardBookId[str]:
    if re.match(SUPPORTED_URLS[0], url):
        book_id = url.split("/")[-3]
        return StandardBookId("book", book_id)
    if re.match(SUPPORTED_URLS[1], url):
        book_id = url.split("/")[-2]
        return StandardBookId("book", book_id)
    if re.match(SUPPORTED_URLS[2], url):
        book_id = url.split("/")[-1]
        return StandardBookId("book", book_id)
    if re.match(SUPPORTED_URLS[3], url):
        series_id = url.split("/")[-1]
        return StandardBookId("series", series_id)
    raise InvalidUrl


async def download_series(client: http.Client, series_id: str) -> Series:
    # TODO Check for ultra releases
    response = await client.get(
        f"https://www.dcuniverseinfinite.com/api/comics/1/series/{series_id}/?trans=en"
    )
    content = response.json()
    return Series(
        title = content["title"],
        book_ids = [StandardBookId("book", x) for x in content["book_uuids"]["issue"]]
    )


async def download_issue(client: http.Client, issue_id: str) -> Book:
    response = await client.get(
        f"https://www.dcuniverseinfinite.com/api/5/1/rights/comic/{issue_id}?trans=en"
    )
    jwt = response.json()
    if type(jwt) is not str:
        raise AccessDenied
    response = await client.get(
        "https://www.dcuniverseinfinite.com/api/comics/1/book/download/?page=1&quality=HD&trans=en",
        headers = {
            "X-Auth-JWT": jwt
        }
    )
    response = response.json()
    if not "uuid" in response:
        logging.debug(f"{response=}")
        raise AccessDenied
    uuid = response["uuid"]
    job_id = response["job_id"]
    format_id = response["format"]
    images: List[blob.Blob] = []
    for page in response["images"]:
        page_number = page["page_number"]
        images.append(blob.request(
            url = page["signed_url"],
            format = blob.Format.Jpg,
            encryption = DcUniverseInfiniteEncryption(uuid, page_number, job_id, format_id)
        ))

    response = await client.get(
        f"https://www.dcuniverseinfinite.com/api/comics/1/book/{issue_id}/?trans=en"
    )
    metadata = response.json()

    return Book(
        data = ImageList(images),
        metadata = Metadata(
            title = metadata["title"],
            series = metadata["series_title"],
            index = int(metadata["issue_number"]),
            publisher = "DC"
        )
    )


async def download(client: http.Client, id: StandardBookId[str]) -> Result:
    if id.variant == "book":
        return await download_issue(client, id.value)
    else:
        return await download_series(client, id.value)



SOURCE = source.Source(
    name = "DC Universe Infinite",
    url_support = source.url_matches_regex(SUPPORTED_URLS),
    id_of_url = id_of_url,
    download = download,
    login = login,
    load_cookies = load_cookies,
)


class DcUniverseInfiniteEncryption:
    """
    DC Universe Infinite encryption scheme.

    It uses AES-CBC with extra data at the start of the file indicating the
    length and the iv.

    The key is generated from metadata about the book.
    """
    key: bytes

    def __init__(self, uuid: str, page_number: int, job_id: str, format_id: str):
        string_key = f"{uuid}{page_number}{job_id}{format_id}"
        self.key = sha256(string_key.encode("utf8")).digest()


    def decrypt(self, data: bytes) -> bytes:
        # The first 8 bytes contains the size of the output file
        original_size = int.from_bytes(data[0:8], byteorder="little")
        # The next 16 bytes are the initialization vector
        iv = data[8:24]
        # The rest of the data is the encrypted image
        encrypted_image = data[24:]
        # Decrypting image
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return cipher.decrypt(encrypted_image)
