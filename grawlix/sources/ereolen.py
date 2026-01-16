from grawlix.book import Result, Book, SingleFile, Metadata, OnlineFile
from grawlix.encryption import AESCTREncryption
from grawlix.exceptions import InvalidUrl, DataNotFound
from grawlix.utils import nearest_string, get_arg_from_url
from grawlix import logging
from .source import Source

from bs4 import BeautifulSoup
import json
import re
from Crypto.Cipher import AES
from base64 import b64decode
from urllib.parse import urlparse
import importlib

KEY_ENCRYPTION_KEY = bytes([30, 193, 150, 69, 32, 247, 35, 95, 92, 255, 193, 159, 121, 40, 151, 179, 39, 159, 75, 110, 32, 205, 210, 58, 81, 55, 158, 33, 8, 149, 108, 74])
KEY_ENCRYPTION_IV = bytes([0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0])

class Ereolen(Source):
    name: str = "eReolen"
    library_domains = importlib.resources.files("grawlix") \
        .joinpath("assets/ereolen/libraries.txt") \
        .read_text("utf8") \
        .split("\n")
    match: list[str] = [
        rf"https://(www.)?({'|'.join(library_domains)})/reader\?orderid=.+$",
    ]
    _authentication_methods = [ "login" ]


    async def login(self, url: str, username: str, password: str) -> None:
        hostname = urlparse(url).hostname
        login_page = await self._client.get(f"https://{hostname}/login", follow_redirects=True)
        login_soup = BeautifulSoup(login_page.text, "lxml")
        borchk_login_form = login_soup.find(id="borchk-login-form")
        if borchk_login_form is None:
            raise DataNotFound
        login_path = borchk_login_form.get("action")
        library_id = borchk_login_form.find(id="libraryid-input").get("value")
        library_name = borchk_login_form.find(id="libraryname-input").get("value")
        logging.debug(f"{library_name=} {library_id=}")
        await self._client.post(
            f"https://login.bib.dk{login_path}",
            headers = { "Content-Type": "application/x-www-form-urlencoded" },
            data = {
                "libraryName": library_name,
                "agency": library_id,
                "loginBibDkUserId": username,
                "pincode": password
            },
            follow_redirects = True,
            timeout = 20.,
        )


    async def download(self, url: str) -> Result:
        book_id: str = get_arg_from_url(url, "orderid")
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
