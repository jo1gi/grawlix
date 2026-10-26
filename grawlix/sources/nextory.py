from grawlix.book import Book, Metadata, OnlineFile, BookData, EpubInParts, Result, Series
from grawlix.encryption import AESEncryption
from grawlix.exceptions import DataNotFound
from .source import Source

from typing import Tuple
from datetime import date
from urllib3.util import parse_url
import uuid
import base64

LOCALE = "en_GB"

class Nextory(Source):
    name: str = "Nextory"
    match = [
        r"https?://((www|catalog-\w\w).)?nextory.+"
    ]
    _authentication_methods = [ "login" ]

    # Authentication methods

    async def login(self, url: str, username: str, password: str) -> None:
        # Set permanent headers
        device_id = self._create_device_id()
        self._client.headers.update(
            {
                "X-Application-Id": "200",
                "X-App-Version": "2026.07.9",
                "X-Locale": LOCALE,
                "X-Model": "Personal Computer",
                "X-Device-Id": device_id,
                "X-OS-INFO": "Personal Computer",
                "locale": LOCALE,
            }
        )
        # Account login: yields the login token
        session_response = await self._client.post(
            "https://api.nextory.com/user/v1/sessions",
            json = {
                "identifier": username,
                "password": password
            },
        )
        session_response = session_response.json()
        login_token = session_response["login_token"]
        country = session_response["country"]
        self._client.headers.update(
            {
                "token": login_token,
                "X-Login-Token": login_token,
                "X-Country-Code": country,
            }
        )
        # Profile login: API calls also need a profile token
        profiles_response = await self._client.get(
            "https://api.nextory.com/user/v1/me/profiles",
        )
        profiles_response = profiles_response.json()
        profile = profiles_response["profiles"][0]
        login_key = profile["login_key"]
        authorize_response = await self._client.post(
            "https://api.nextory.com/user/v1/profile/authorize",
            json = {
                "login_key": login_key
            }
        )
        authorize_response = authorize_response.json()
        profile_token = authorize_response["profile_token"]
        self._client.headers.update({"X-Profile-Token": profile_token})


    @staticmethod
    def _create_device_id() -> str:
        """Fixed device id (uuid3 of a constant), so every run looks like the same device"""
        return str(uuid.uuid3(uuid.NAMESPACE_DNS, "audiobook-dl"))


    # Main download methods

    async def download(self, url: str) -> Result:
        url_id = self._extract_id_from_url(url)
        path_segments = (parse_url(url).path or "").split("/")
        if "series" in path_segments or "serier" in path_segments:
            return await self._download_series(url_id)
        else:
            return await self._download_book(url_id)


    @staticmethod
    def _extract_id_from_url(url: str) -> str:
        """
        Extract id of book from url. This id is not always the internal id for
        the book.

        :param url: Url to book information page
        :returns: Id in url
        """
        return parse_url(url).path.split("-")[-1].replace("/", "")


    async def download_book_from_id(self, book_id: str) -> Book:
        return await self._download_book(book_id)


    # Book download path

    async def _download_book(self, book_id: str) -> Book:
        product_data = await self._get_product_data(book_id)
        _, format_id = self._find_format(product_data)
        # Nextory serves every book via the epub endpoint; PDFs arrive wrapped in an epub (see pdf_converter)
        data = await self._get_epub_data(format_id)
        metadata = self._extract_metadata(product_data)

        return Book(
            data = data,
            metadata = metadata,
        )


    async def _get_product_data(self, book_id: str) -> dict:
        """
        Fetch product data from Nextory API

        :param book_id: Id of book (can be URL id or internal id)
        :returns: Product data dictionary
        """
        response = await self._client.get(
            f"https://api.nextory.com/library/v1/products/{book_id}",
        )
        return response.json()


    @staticmethod
    def _find_format(product_data) -> Tuple[str, str]:
        """Find a supported book format (epub or pdf)"""
        for format_type in ("epub", "pdf"):
            for fmt in product_data.get("formats", []):
                if fmt["type"] == format_type:
                    return (format_type, fmt["identifier"])
        raise DataNotFound


    def _extract_metadata(self, product_data: dict) -> Metadata:
        """
        Extract metadata from Nextory product data

        :param product_data: Product data from Nextory API
        :returns: Metadata object
        """
        # Find epub or pdf format for format-specific metadata
        ebook_format = None
        for fmt_type in ("epub", "pdf"):
            for fmt in product_data.get("formats", []):
                if fmt.get("type") == fmt_type:
                    ebook_format = fmt
                    break
            if ebook_format:
                break

        # Basic metadata
        title = product_data.get("title", "Unknown")
        authors = [author["name"] for author in product_data.get("authors", [])]
        description = product_data.get("description_full")
        language = product_data.get("language")

        # Format-specific metadata
        publisher = None
        isbn = None
        release_date = None
        translators = []
        if ebook_format:
            publisher = ebook_format.get("publisher", {}).get("name") if ebook_format.get("publisher") else None
            isbn = ebook_format.get("isbn")
            translators = [t["name"] for t in ebook_format.get("translators", [])]
            pub_date = ebook_format.get("publication_date")
            if pub_date:
                # Format is YYYY-MM-DD
                release_date = date.fromisoformat(pub_date)

        # Series info
        series = None
        index = None
        series_info = product_data.get("series")
        if series_info:
            series = series_info.get("name")
        volume = product_data.get("volume")
        if volume:
            index = volume

        return Metadata(
            title=title,
            authors=authors,
            translators=translators,
            language=language,
            publisher=publisher,
            isbn=isbn,
            description=description,
            release_date=release_date,
            series=series,
            index=index,
            source="Nextory"
        )


    async def _get_epub_data(self, epub_id: str) -> BookData:
        """
        Download epub data for book

        :param epub_id: Id of epub file
        :returns: Epub data
        """
        # Nextory splits books into one encrypted epub per chapter. Parts overlap:
        # the same paths recur, sometimes as stubs or with placeholder comments,
        # so they are decrypted and merged into one epub on output.
        response = await self._client.get(
            f"https://api.nextory.com/reader/books/{epub_id}/packages/epub"
        )
        epub_data = response.json()
        encryption = AESEncryption(
            key = self._fix_key(epub_data["crypt_key"]),
            iv = self._fix_key(epub_data["crypt_iv"])
        )
        files = [
            OnlineFile(
                url = part["spine_url"],
                extension = "epub",
                encryption = encryption
            )
            for part in epub_data["spines"]
        ]
        files_in_toc = {}
        for item in epub_data["toc"]["childrens"]: # (sic) API field name
            files_in_toc[item["src"]] = item["name"]
        return EpubInParts(
            files,
            files_in_toc
        )

    @staticmethod
    def _fix_key(value: str) -> bytes:
        """
        Decode a base64 key/iv. Some responses append a single stray
        character after the (correctly padded) base64 data. Valid base64 is
        always a multiple of 4 long, so strip the last character only when
        the length is off. Decoding as-is and falling back on error is not
        enough: a 32 byte key with a stray character decodes without error
        to the wrong bytes.
        """
        return base64.b64decode(value[:-1] if len(value) % 4 else value)


    # Series download path

    async def _download_series(self, series_id: str) -> Series:
        """
        Download series from Nextory

        :param series_id: Id of series on Nextory
        :returns: Series data
        """
        response = await self._client.get(
            f"https://api.nextory.com/discovery/v1/series/{series_id}/products",
            params = {
                "content_type": "book",
                "page": 0,
                "per": 100,
            }
        )
        series_data = response.json()
        book_ids = [book["id"] for book in series_data["products"]]
        return Series(
            title = series_data["products"][0]["series"]["name"],
            book_ids = book_ids,
        )
