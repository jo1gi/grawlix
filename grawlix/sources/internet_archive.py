from grawlix.book import Book, SingleFile, Metadata, OfflineFile
from .source import Source

import random
import string
from bs4 import BeautifulSoup
import asyncio

class InternetArchive(Source):
    name: str = "Internet Archive"
    match: list[str] = [
        r"https://archive.org/details/.+"
    ]
    _authentication_methods = [ "login", "cookies" ]
    _login_credentials = [ "username", "password" ]

    @staticmethod
    def _format_data(content_type: str, fields):
        data = ""
        for name, value in fields.items():
            data += f"--{content_type}\x0d\x0aContent-Disposition: form-data; name=\"{name}\"\x0d\x0a\x0d\x0a{value}\x0d\x0a"
        data += content_type+"--"
        return data


    async def login(self, username: str, password: str, **kwargs) -> None:
        await self._client.get("https://archive.org/account/login")
        content_type = "----WebKitFormBoundary"+"".join(random.sample(string.ascii_letters + string.digits, 16))
        headers = {'Content-Type': 'multipart/form-data; boundary='+content_type}
        data = self._format_data(content_type, {"username":username, "password":password, "submit_by_js":"true"})
        response = await self._client.post(
            "https://archive.org/account/login",
            data=data,
            headers=headers
        )
        if not "Successful login" in response.text:
            print("Failed login")
            exit(1)


    async def _download_acsm(self, book_id: str) -> bytes:
        """
        Loan book on archive.org and download acsm file

        :param book_id: Id of book
        """
        await self._client.post(
            "https://archive.org/services/loans/loan/searchInside.php",
            data = {
                "action": "grant_access",
                "identifier": book_id
            }
        )
        await self._client.post(
            "https://archive.org/services/loans/loan/",
            data = {
                "action": "browse_book",
                "identifier": book_id
            }
        )
        # TODO: Error handling
        await self._client.post(
            "https://archive.org/services/loans/loan/",
            data = {
                "action": "create_token",
                "identifier": book_id
            }
        )
        acsm_response = await self._client.get(
            f"https://archive.org/services/loans/loan/?action=media_url&identifier={book_id}&format=pdf&redirect=1",
            follow_redirects = True
        )
        return acsm_response.content


    async def download(self, url: str) -> Book:
        book_id = url.split("/")[4]
        metadata, acsm_file = await asyncio.gather(
            self._download_metadata(book_id),
            self._download_acsm(book_id)
        )
        return Book(
            data = SingleFile(
                OfflineFile(
                    content = acsm_file,
                    extension = "acsm",
                )
            ),
            metadata = Metadata(
                title = metadata["title"],
                authors = [ metadata.get("creator") ] if "creator" in metadata else []
            )
        )


    async def _download_metadata(self, book_id: str) -> dict:
        """
        Download metadata for book

        :param book_id: Id of book
        :returns: Dictionary with metadata
        """
        page_response = await self._client.get(
            f"https://archive.org/details/{book_id}"
        )
        soup = BeautifulSoup(page_response.text, "lxml")
        metadata_url = soup.find("ia-book-theater").get("bookmanifesturl")
        metadata_response = await self._client.get(
            f"https:{metadata_url}"
        )
        return metadata_response.json()["data"]["metadata"]
