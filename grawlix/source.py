from grawlix import book
from grawlix.utils import http

from dataclasses import dataclass
from typing import Generic, Callable, Awaitable
from enum import Enum
import re


class UrlSupport(Enum):
    Unsupported = 0
    SupportedDomain = 1
    SupportedUrl = 2


@dataclass(slots=True)
class Source[State, BookId]:
    """
    The definition of a source. Defined the attributes and functions a source
    needs to implement.
    """
    name: str
    url_support: Callable[[str], UrlSupport]
    id_of_url: Callable[[State, str], Awaitable[BookId]]
    download: Callable[[State, BookId], Awaitable[book.Result]]
    login: Callable[[str, str, str], Awaitable[State]] | None = None
    load_cookies: Callable[[str], Awaitable[State]] | None = None
    instanciate_without_login: Callable[[str], Awaitable[State]] | None = None


@dataclass(slots=True)
class Instance[State, BookId]:
    source: Source[State, BookId]
    state: State

    async def download(self, book_id: BookId) -> book.Result:
        return await self.source.download(self.state, book_id)


def url_matches_regex(regexes: list[str]) -> Callable[[str], UrlSupport]:
    def inner(url: str) -> UrlSupport:
        for regex in regexes:
            if re.match(regex, url):
                return UrlSupport.SupportedUrl
        return UrlSupport.Unsupported
    return inner


async def client_state_from_cookies(cookie_file: str) -> http.Client:
    client = http.create_client()
    http.load_cookies(client, cookie_file)
    return client
