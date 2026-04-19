from grawlix import source
from grawlix.book import Book, Metadata, BookData, EpubInParts, Result, Series, StandardBookId
from grawlix.encryption import AESEncryption
from grawlix.exceptions import InvalidUrl
from grawlix.utils import http, blob

from typing import Optional, TypeAlias
import uuid
import base64

State: TypeAlias = http.Client
Id: TypeAlias = StandardBookId[str]

LOCALE = "en_GB"

SUPPORTED_URLS = [
    r"https?://((www|catalog-\w\w).)?nextory.+"
]

async def login(url: str, username: str, password: str) -> State:
    client = http.create_client()

    # Set permanent headers
    client.headers.update(
        {
            "X-Application-Id": "200",
            "X-App-Version": "5.4.1",
            "X-Locale": LOCALE,
            "X-Model": "Personal Computer",
            "X-Device-Id": str(uuid.uuid3(uuid.NAMESPACE_DNS, "audiobook-dl")),
            "X-Os-Info": "Android",
            "appid": "200",
        }
    )

    # Login for account
    session_response = await client.post(
        "https://api.nextory.com/user/v1/sessions",
        json = {
            "identifier": username,
            "password": password
        },
    )
    session_response = session_response.json()
    login_token = session_response["login_token"]
    country = session_response["country"]
    client.headers.update(
        {
            "token": login_token,
            "X-Login-Token": login_token,
            "X-Country-Code": country,
        }
    )

    # Login for user
    profiles_response = await client.get(
        "https://api.nextory.com/user/v1/me/profiles",
    )
    profiles_response = profiles_response.json()
    profile = profiles_response["profiles"][0]
    login_key = profile["login_key"]
    authorize_response = await client.post(
        "https://api.nextory.com/user/v1/profile/authorize",
        json = {
            "login_key": login_key
        }
    )
    authorize_response = authorize_response.json()
    profile_token = authorize_response["profile_token"]
    client.headers.update({"X-Profile-Token": profile_token})
    return client


async def id_of_url(state: State, url: str) -> Id:
    id = url.split("-")[-1].replace("/", "")
    if "serier" in url:
        return StandardBookId("book", id)
    else:
        return StandardBookId("series", id)


async def download_series(client: State, series_id: str) -> Series[Id]:
    """
    Download series from Nextory.

    :param client: The authenticated http client.
    :param series_id: Id of series on Nextory.
    :returns: Series data.
    """
    response = await client.get(
        f"https://api.nextory.com/discovery/v1/series/{series_id}/products",
        params = {
            "content_type": "book",
            "page": 0,
            "per": 100,
        }
    )
    series_data = response.json()
    book_ids = []
    for book in series_data["products"]:
        book_id = book["id"]
        book_ids.append(StandardBookId("book", book_id))
    return Series(
        title = series_data["products"][0]["series"]["name"],
        book_ids = book_ids,
    )


def fix_key(value: str) -> bytes:
    return base64.b64decode(value[:-1])


async def download_book(client: State, book_id: str) -> Book:
    product_data = await client.get(
        f"https://api.nextory.com/library/v1/products/{book_id}"
    )
    product_data = product_data.json()

    for format in product_data["formats"]:
        if format["type"] == "epub":
            epub_id = format["identifier"]
    if epub_id is None:
        raise InvalidUrl

    series_name = None
    if "series" in product_data:
        series_name = product_data["series"]["name"]

    # Nextory books are for some reason split up into multiple epub files -
    # one for each chapter file. All of these files has to be decrypted and
    # combined afterwards. Many of the provided epub files contain the same
    # files and some of them contain the same file names but with variation
    # in the content and comments that describe what should have been there
    # if the book was whole from the start.
    response = await client.get(
        f"https://api.nextory.com/reader/books/{epub_id}/packages/epub"
    )
    epub_data = response.json()
    encryption = AESEncryption(
        key = fix_key(epub_data["crypt_key"]),
        iv = fix_key(epub_data["crypt_iv"])
    )
    files = []
    for part in epub_data["spines"]:
        files.append(
            blob.request(
                url = part["spine_url"],
                format = blob.Format.Epub,
                encryption = encryption
            )
        )
    files_in_toc = {}
    for item in epub_data["toc"]["childrens"]: # Why is it "childrens"?
        files_in_toc[item["src"]] = item["name"]

    return Book(
        data = EpubInParts(files, files_in_toc),
        metadata = Metadata(
            title = product_data["title"],
            authors = [author["name"] for author in product_data["authors"]],
            series = series_name,
        )
    )


async def download(client: State, id: Id) -> Result[Id]:
    if id.variant == "book":
        return await download_book(client, id.value)
    else:
        return await download_series(client, id.value)


SOURCE = source.Source(
    name = "Nextory",
    url_support = source.url_matches_regex(SUPPORTED_URLS),
    id_of_url = id_of_url,
    download = download,
    login = login,
)
