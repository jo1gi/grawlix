from grawlix.book import Book, Series, Result

from typing import Generic, TypeVar, Tuple, Optional
from http.cookiejar import MozillaCookieJar
import requests
import re

T = TypeVar("T")

class Source(Generic[T]):
    """
    General class for downloading books from various sources
    """

    name: str = "UNKNOWN"
    match: list[str] = []
    _authentication_methods: list[str] = []
    authenticated = False

    def __init__(self):
        self._session = requests.Session()


    @property
    def requires_authentication(self) -> bool:
        """Does the source require authentication to download books"""
        return len(self._authentication_methods) > 0


    @property
    def supports_login(self) -> bool:
        """Does the source support authentication with username and password"""
        return "login" in self._authentication_methods


    def login(self, username: str, password: str, **kwargs: str):
        """
        Login to source

        :param username: Username of user for source
        :param password: Password of user for source
        """
        raise NotImplementedError


    @property
    def supports_cookies(self) -> bool:
        """Does the source support authentication with cookie file"""
        return "cookies" in self._authentication_methods


    def load_cookies(self, cookie_file: str):
        """
        Authenticate with source with netscape cookie file

        :param cookie_file: Path to netscape cookie file
        """
        if self.supports_cookies:
            cookie_jar = MozillaCookieJar()
            cookie_jar.load(cookie_file, ignore_expires=True)
            self._session.cookies.update(cookie_jar)
            self.authenticated = True


    def download(self, url: str) -> Result[T]:
        """
        Download book metadata from source

        :param url: Url of book to download
        :returns: Book metadata
        """
        raise NotImplementedError


    def download_book_from_id(self, book_id: T) -> Book:
        """
        Download book from id

        :param book_id: Internal id of book
        :returns: Downloaded book metadata
        """
        raise NotImplementedError


    def get_match_index(self, url: str) -> Optional[int]:
        """
        Find the first regex in `self.match` that matches url

        :param url: Url to match
        :returns: Index of regex
        """
        for index, match in enumerate(self.match):
            if re.match(match, url):
                return index
        return None
