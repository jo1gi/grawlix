from grawlix.book import Result, Book, SingleFile, Metadata, OnlineFile
from grawlix.encryption import AESCTREncryption
from grawlix.exceptions import InvalidUrl, DataNotFound
from grawlix.utils import nearest_string
from .source import Source

from bs4 import BeautifulSoup
import json
import re
from Crypto.Cipher import AES
from base64 import b64decode

LOGIN_PAGE_URL = "https://ereolen.dk/adgangsplatformen/login?destination=/user"
KEY_ENCRYPTION_KEY = bytes([30, 193, 150, 69, 32, 247, 35, 95, 92, 255, 193, 159, 121, 40, 151, 179, 39, 159, 75, 110, 32, 205, 210, 58, 81, 55, 158, 33, 8, 149, 108, 74])
KEY_ENCRYPTION_IV = bytes([0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0])

class Ereolen(Source):
    name: str = "eReolen"
    match: list[str] = [
        r"https://ereolen.dk/ting/object/\d+-.+/read/?$",
        r"https://ereolen.dk/ting/object/\d+-[^/]+/?$"
    ]
    _authentication_methods = [ "login" ]
    _login_credentials = [ "username", "password", "library" ]


    async def login(self, username: str, password: str, **kwargs) -> None:
        library = kwargs["library"]
        login_page = await self._client.get(LOGIN_PAGE_URL, follow_redirects=True)
        login_soup = BeautifulSoup(login_page.text, "lxml")
        borchk_login_form = login_soup.find(id="borchk-login-form")
        login_path = borchk_login_form.get("action")
        library_attr_name = borchk_login_form.find("label").get("for")
        libraries = self._extract_available_libraries(login_page.text)
        if not library in libraries:
            library = nearest_string(library, list(libraries.keys()))
        await self._client.post(
            f"https://login.bib.dk{login_path}",
            headers = { "Content-Type": "application/x-www-form-urlencoded" },
            data = {
                library_attr_name: library,
                "agency": libraries[library],
                "loginBibDkUserId": username,
                "pincode": password
            },
            follow_redirects = True
        )


    def _extract_available_libraries(self, login_page: str) -> dict[str, str]:
        """
        Extract list of available libraries from login page

        :param login_page: Content of login page as string
        :returns: Dictionary with name and id of each library
        """
        match = re.search("libraries = ({.+})<", login_page)
        if match is None:
            raise DataNotFound
        library_data = json.loads(match.group(1))
        libraries: dict[str, str] = {}
        for library in library_data["folk"]:
            library_name = library["name"]
            library_id = library["branchId"]
            libraries[library_name] = library_id
        return libraries


    async def download(self, url: str) -> Result:
        book_id: str = await self._get_book_id(url)
        metadata_response = await self._client.get(
            f"https://bookstreaming.pubhub.dk/v1/order/metadata/{book_id}",
        )
        metadata = metadata_response.json()
        key = self._decrypt_key(metadata["key"])
        return Book(
            data = SingleFile(
                OnlineFile(
                    url = f"https://bookstreaming.pubhub.dk/v1/order/file/{book_id}",
                    extension = "epub",
                    encryption = AESCTREncryption(
                        key,
                        nonce = bytes([0,0,0,0,0,0,0,0]),
                        initial_value = bytes([0,0,0,0,0,0,0,0])
                    )
                )
            ),
            metadata = Metadata(
                title = metadata["title"],
                authors = [ metadata["author"] ]
            )
        )


    def _decrypt_key(self, key: str) -> bytes:
        """
        Decrypt book encryption key

        :param key: Base64 encoded and encrypted key
        :returns: Decoded and decrypted key
        """
        decoded_key = b64decode(key)
        cipher = AES.new(KEY_ENCRYPTION_KEY, AES.MODE_CBC, KEY_ENCRYPTION_IV)
        return cipher.decrypt(decoded_key)[:16]


    async def _get_book_id(self, url: str) -> str:
        """
        Download and extract book_id

        :param url: Url to book page
        :returns: Book id
        """
        if re.match(self.match[0], url):
            if url.endswith("/"):
                url = url[:-1]
            return await self._get_book_id_from_reader(url)
        if re.match(self.match[1], url):
            return await self._get_book_id_from_reader(f"{url}/read")
        else:
            raise InvalidUrl


    async def _get_book_id_from_reader(self, url: str) -> str:
        """
        Download and extract book_id from reader page

        :param url: Url to reader page
        :returns: Book id
        """
        page = await self._client.get(url)
        soup = BeautifulSoup(page.text, "lxml")
        return soup.find("div", id="pubhub-reader").get("order-id")
