from grawlix import logging
from grawlix.book import Result, Book, Metadata, OnlineFile, ImageList, Series
from grawlix.encryption import Encryption
from grawlix.exceptions import InvalidUrl, AccessDenied
from .source import Source

import re
from typing import Tuple, List
from hashlib import sha256
from Crypto.Cipher import AES

class DcUniverseInfinite(Source):
    name = "DC Universe Infinite"
    match: list[str] = [
        # Reader page
        r"https://www.dcuniverseinfinite.com/comics/book/[^/]+/[^/]+/c/reader",
        # Issue info page
        r"https://www.dcuniverseinfinite.com/comics/book/[^/]+/[^/]+/c",
        # Series info page
        r"https://www.dcuniverseinfinite.com/comics/series/[^/]+/[^/]+"
    ]
    _authentication_methods = [ "cookies" ]


    async def download(self, url: str) -> Result:
        # Set headers
        auth_token = self._client.cookies.get("session")
        self._client.headers.update({
            "Authorization": f"Token {auth_token}",
            "X-Consumer-Key": await self.download_consumer_secret()
        })
        self.plan = await self.download_plan()
        logging.debug(f"{self.plan=}")
        # Download book
        typ, id = self.extract_id_from_url(url)
        if typ == "book":
            logging.debug(f"Book id: {id}")
            return await self.download_book_from_id(id)
        else:
            logging.debug(f"Series id: {id}")
            return await self.download_series(id)


    async def download_series(self, series_id: str) -> Series[str]:
        # TODO Check for ultra releases
        response = await self._client.get(
            f"https://www.dcuniverseinfinite.com/api/comics/1/series/{series_id}/?trans=en"
        )
        content = response.json()
        return Series(
            title = content["title"],
            book_ids = [x for x in content["book_uuids"]["issue"]]
        )


    async def download_book_from_id(self, book_id: str) -> Book:
        return Book(
            data = await self.download_pages(book_id),
            metadata = await self.download_book_metadata(book_id)
        )


    async def download_pages(self, book_id: str) -> ImageList:
        """
        Download comic pages

        :param book_id: Id of comic
        :return: List of comic pages
        """
        response = await self._client.get(
            f"https://www.dcuniverseinfinite.com/api/5/1/rights/comic/{book_id}?trans=en"
        )
        jwt = response.json()
        response = await self._client.get(
            "https://www.dcuniverseinfinite.com/api/comics/1/book/download/?page=1&quality=HD&trans=en",
            headers = {
                "X-Auth-JWT": jwt
            }
        )
        response = response.json()
        if not "uuid" in response:
            raise AccessDenied
        uuid = response["uuid"]
        job_id = response["job_id"]
        format_id = response["format"]
        images: List[OnlineFile] = []
        for page in response["images"]:
            page_number = page["page_number"]
            images.append(OnlineFile(
                url = page["signed_url"],
                extension = "jpg",
                encryption = DcUniverseInfinteEncryption(uuid, page_number, job_id, format_id)
            ))
        return ImageList(images)


    async def download_book_metadata(self, book_id: str) -> Metadata:
        """
        Download book metadata

        :param book_id: Id of book
        :return: Book metadata
        """
        response = await self._client.get(
            f"https://www.dcuniverseinfinite.com/api/comics/1/book/{book_id}/?trans=en"
        )
        content = response.json()
        return Metadata(
            title = content["title"],
            series = content["series_title"],
            index = int(content["issue_number"]),
            publisher = "DC"
        )


    def extract_id_from_url(self, url: str) -> Tuple[str, str]:
        """
        Extract book or series id from url

        :param url: Url of page with id
        :return: Type (book or series) and id
        """
        match_index = self.get_match_index(url)
        if match_index == 0:
            book_id = url.split("/")[-3]
            return ("book", book_id)
        if match_index == 1:
            book_id = url.split("/")[-2]
            return ("book", book_id)
        if match_index == 2:
            series_id = url.split("/")[-1]
            return ("series", series_id)
        raise InvalidUrl


    async def download_consumer_secret(self) -> str:
        """Download consumer secret"""
        response = await self._client.get(
            "https://www.dcuniverseinfinite.com/api/5/consumer/www?trans=en"
        )
        return response.json()["consumer_secret"]


    async def download_plan(self) -> str:
        """Download user subscribtion plan"""
        response = await self._client.get(
            "https://www.dcuniverseinfinite.com/api/claims/?trans=en"
        )
        return response.json()["data"]["urn:df:clm:premium"]["plan"]


class DcUniverseInfinteEncryption:
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
