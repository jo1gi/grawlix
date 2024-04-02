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

class Storytel(Source):
    name: str = "Storytel"
    match = [
        r"https?://(?:www.)?(?:storytel|mofibo).com/(?P<language>\w+)(?:/(?P<language2>\w+))?/(?P<list_type>(?:books|series|authors|narrators|publishers|categories))/.+",
    ]
    _authentication_methods = [ "login" ]
    __download_counter = 0

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

        return Book(
            metadata = Metadata(
                title = details["title"]
            ),
            data = SingleFile(
                OnlineFile(
                    url = epub_url,
                    extension = "epub",
                    headers = self._client.headers
                )
            )
        )


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

        :param formats: comma serapted list of formats (abook,ebook,podcast)
        :param languages: comma seperated list of languages (en,de,tr,ar,ru,pl,it,es,sv,fr,nl)
        """
        nextPageToken = 0

        # API returns only 10 items per request
        # if the nextPageToken
        result: dict[str, Any] = {"nextPageToken": False}

        while result["nextPageToken"] is not None:
            params: dict[str, str] = {
                "includeListDetails": "true",  # include listMetadata,filterOptions,sortOption sections
                "includeFormats": formats,
                "includeLanguages": languages,
                "kidsMode": "false",
            }
            if result["nextPageToken"]:
                params["nextPageToken"] = result["nextPageToken"]

            response = await self._client.get(
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

        return result


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


    async def reauthenticate(self) -> None:
        """Reauthenticate if required"""
        if self.__download_counter > 0 and self.__download_counter % 10 == 0:
            await self.authenticate()


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


    async def login(self, username: str, password: str, **kwargs) -> None:
        self.__username = username
        self.__password = self.encrypt_password(password)
        self._client.headers.update({"User-Agent": "Storytel/23.49 (Android 13; Pixel 6) Release/2288481"})
        await self.authenticate()
