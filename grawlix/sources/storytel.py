from grawlix.book import Book, Metadata, SingleFile, OnlineFile, Result, Series
from grawlix.exceptions import SourceNotAuthenticated, InvalidUrl, DataNotFound
from grawlix import logging
from .source import Source

import json
import re
from urllib3.util import parse_url
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from typing import Any
from datetime import datetime

class Storytel(Source):
    name: str = "Storytel"
    match = [
        r"https?://(?:www.)?(?:storytel|mofibo).com/(?P<language>\w+)(?:/(?P<language2>\w+))?/(?P<list_type>(?:books|series|authors|narrators|publishers|categories))/.+",
    ]
    _authentication_methods = [ "login" ]
    __download_counter = 0

    # Authentication methods

    async def login(self, username: str, password: str, **kwargs) -> None:
        self.__username = username
        self.__password = self.encrypt_password(password)
        self._client.headers.update({"User-Agent": "Storytel/23.49 (Android 13; Pixel 6) Release/2288481"})
        await self.authenticate()


    @staticmethod
    def encrypt_password(password: str) -> str:
        """
        Encrypt password with predefined keys.
        This encrypted password is used for login.

        :param password: User defined password
        :returns: Encrypted password
        """
        # Thanks to https://github.com/javsanpar/storytel-tui
        key = b"VQZBJ6TD8M9WBUWT"
        iv = b"joiwef08u23j341a"
        msg = pad(password.encode(), AES.block_size)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        cipher_text = cipher.encrypt(msg)
        return cipher_text.hex()


    async def authenticate(self) -> None:
        """Authenticate with storytel"""
        response = await self._client.post(
            f"https://www.storytel.com/api/login.action?m=1&token=guestsv&userid=-1&version=23.49&terminal=android&locale=sv&deviceId=995f2562-0e44-4410-b1b9-8d08261f33c4&kidsMode=false",
            data = {
                "uid": self.__username,
                "pwd": self.__password
            }
        )
        if response.status_code != 200:
            raise SourceNotAuthenticated
        user_data = response.json()
        jwt = user_data["accountInfo"]["jwt"]
        self._client.headers.update({"authorization": f"Bearer {jwt}"})


    async def reauthenticate(self) -> None:
        """Reauthenticate if required"""
        if self.__download_counter > 0 and self.__download_counter % 10 == 0:
            await self.authenticate()


    # Main download methods

    async def download(self, url: str) -> Result:
        await self.reauthenticate()

        if m := re.match(self.match[0], url):
            language, language2, list_type = m.groups()

            if list_type == "books":
                book_id = self.extract_id_from_url(url)
                logging.debug(f"{book_id=}")
                return await self.download_book_from_id(book_id)

            if list_type in ("series", "authors", "narrators"):
                return await self.download_list(url, list_type, language)

        raise InvalidUrl


    @staticmethod
    def extract_id_from_url(url: str) -> str:
        """
        Extract id from url

        :param url: Url containing id
        :return: Id
        """
        parsed = parse_url(url)
        if parsed.path is None:
            raise DataNotFound
        return parsed.path.split("-")[-1]


    # Book download path

    async def download_book_from_id(self, book_id: str) -> Book:
        # Epub location
        response = await self._client.get(
            f"https://api.storytel.net/assets/v2/consumables/{book_id}/ebook",
        )
        self.__download_counter += 1
        epub_url = response.headers["Location"]

        # Book details
        response = await self._client.get(
            f"https://api.storytel.net/book-details/consumables/{book_id}?kidsMode=false&configVariant=default"
        )
        details = response.json()
        logging.debug(f"Full book details JSON: {json.dumps(details, indent=2)}")

        # Extract metadata from details
        metadata = self._extract_metadata(details)

        book = Book(
            metadata = metadata,
            data = SingleFile(
                OnlineFile(
                    url = epub_url,
                    extension = "epub",
                    headers = self._client.headers
                )
            ),
            source_data = {
                "source_name": "storytel",
                "details": details
            }
        )
        return book


    def _extract_metadata(self, details: dict) -> Metadata:
        """
        Extract metadata from Storytel book details JSON

        :param details: Book details from Storytel API
        :return: Metadata object
        """
        # Extract ebook-specific format data
        ebook_format = None
        for fmt in details.get("formats", []):
            if fmt.get("type") == "ebook":
                ebook_format = fmt
                break

        # Extract basic metadata
        title = details.get("title", "Unknown")
        authors = [author["name"] for author in details.get("authors", [])]
        language = details.get("language")
        description = details.get("description")

        # Extract ebook-specific publisher and release date
        publisher = None
        release_date = None
        if ebook_format:
            publisher = ebook_format.get("publisher", {}).get("name")
            release_date_str = ebook_format.get("releaseDate")
            if release_date_str:
                # Parse ISO format date
                release_date = datetime.fromisoformat(release_date_str.replace("Z", "+00:00")).date()

        # Extract series information
        series = None
        index = None
        series_info = details.get("seriesInfo")
        if series_info:
            series = series_info.get("name")
            index = series_info.get("orderInSeries")

        return Metadata(
            title=title,
            authors=authors,
            language=language,
            publisher=publisher,
            description=description,
            release_date=release_date,
            series=series,
            index=index,
            source="Storytel"
        )


    # List download path

    async def download_list(self, url: str, list_type: str, language: str) -> Series:
        """
        Download list of books

        :param url: Url of list page
        :param list_type: Type of list (either series, authors, or narrators)
        :param language: The language of the books in the list
        :return: List of books
        """
        list_id = self.extract_id_from_url(url)
        logging.debug(f"{list_id=}")
        list_details = await self.download_list_details(list_id, list_type, language)

        books: list[str] = [
            item["id"]
            for item in list_details["items"]
            if "ebook" in [format["type"] for format in item["formats"]]
        ]

        return Series(
            title = list_details["title"],
            book_ids = books
        )


    async def download_list_details(
        self,
        list_id: str,
        list_type: str,
        languages: str,
        formats: str = "ebook",
    ) -> dict[str, Any]:
        """Download details about book list

        :param formats: comma separated list of formats (abook,ebook,podcast)
        :param languages: comma separated list of languages (en,de,tr,ar,ru,pl,it,es,sv,fr,nl)
        """
        # API returns only 10 items per request, so we need to paginate
        # Start with None to ensure we enter the loop and make the first request
        result: dict[str, Any] = {"nextPageToken": None}
        is_first_page = True

        while result["nextPageToken"] is not None or is_first_page:
            params: dict[str, str] = {
                "includeListDetails": "true",  # include listMetadata,filterOptions,sortOption sections
                "includeFormats": formats,
                "includeLanguages": languages,
                "kidsMode": "false",
            }
            if result.get("nextPageToken"):
                params["nextPageToken"] = result["nextPageToken"]

            response = await self._client.get(
                f"https://api.storytel.net/explore/lists/{list_type}/{list_id}",
                params=params,
            )

            data = response.json()
            if is_first_page:
                result = data
                is_first_page = False
            else:
                result["items"].extend(data["items"])
                result["nextPageToken"] = data["nextPageToken"]
            logging.debug(f"{result=}")

        return result
