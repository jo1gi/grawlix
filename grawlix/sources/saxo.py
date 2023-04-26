from grawlix.book import Book, Metadata, SingleFile, OnlineFile
from grawlix import AESEncryption
from grawlix.exceptions import ThrottleError

import re
from .source import Source

class Saxo(Source):
    name: str = "Saxo"
    match = [
        r"https://(\w+\.)?saxo.(com|dk)/.+\d+$"
    ]
    _authentication_methods = [ "login" ]
    user_id: str

    async def login(self, username: str, password: str, **kwargs) -> None:
        response = await self._client.post(
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
        self._client.headers = {
            "Appauthorization": f"bearer {bearer_token}",
            "App-Os": "android",
            "App-Version": "6.2.4"
        }
        self.user_id = json["id"]


    async def download(self, url: str) -> Book:
        isbn = self._extract_isbn_from_url(url)
        book_id = await self._get_book_id(isbn)
        metadata = await self._get_book_metadata(book_id)
        ebook_id = metadata["id"] # Id of ebook file
        return Book(
            metadata = self._extract_metadata(metadata),
            data = SingleFile(
                OnlineFile(
                    url = await self._get_book_file_link(ebook_id),
                    extension = "epub",
                    # Encryption keys extracted from app
                    encryption = AESEncryption(
                        key = b"CD3E9D141D8EFC0886912E7A8F3652C4",
                        iv = b"78CB354D377772F1"
                    )
                )
            )
        )


    async def _get_book_id(self, isbn: str) -> str:
        """
        Download internal book id of book from isbn

        :param isbn: Isbn of book
        :returns: Saxo internal book id
        """
        response = await self._client.get(
            f"https://api-read.saxo.com/api/v2/search/user/{self.user_id}/premium/books/{isbn}"
        )
        return response.json()["items"][0]["bookId"]


    async def _get_book_metadata(self, book_id: str) -> dict:
        """
        Download metadata of book

        :param book_id: Id of book
        :returns: Metadata of book
        """
        response = await self._client.get(
            f"https://api-read.saxo.com/api/v2/book/{book_id}/user/{self.user_id}/details"
        )
        return response.json()["ebooks"][0]


    async def _get_book_file_link(self, ebook_id: str) -> str:
        """
        Download link to epub file

        :param ebook_id: Id of ebook file
        :returns: Link to ebook file
        :raises ThrottleError: If there have been too many downloads
        """
        response = await self._client.get(
            f"https://api-read.saxo.com/api/v1/book/{ebook_id}/content/encryptedstream/"
        )
        json = response.json()
        if not "link" in json:
            raise ThrottleError
        return json["link"]


    @staticmethod
    def _extract_metadata(metadata: dict) -> Metadata:
        """
        Extract metadata from matadata response from Saxo

        :param metadata: Metadata response from saxo
        :returns: Metadata formatted as `grawlix.Metadata`
        """
        return Metadata(
            title = metadata["title"],
            authors = [metadata["author"]] if "author" in metadata else [],
            language = metadata.get("languageLocalized")
        )


    @staticmethod
    def _extract_isbn_from_url(url: str) -> str:
        """
        Extracts isbn from url

        :param url: Url of book
        :returns: Isbn of book
        """
        isbn_match = re.search(f"\d+$", url)
        if isbn_match and isbn_match.group():
            return isbn_match.group()
        raise NotImplemented
