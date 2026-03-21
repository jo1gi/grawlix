from typing import TypeAlias
import httpx
from http.cookiejar import MozillaCookieJar

Client: TypeAlias = httpx.AsyncClient


def create_client() -> Client:
    """
    Creates a new http client.

    :returns: The new http client.
    """
    return httpx.AsyncClient()


def load_cookies(client: Client, cookie_file: str):
    """
    Load cookies from `cookie_file` into the client.

    :param client: The http client
    :param cookie_file: The path to the file with cookies
    """
    cookie_jar = MozillaCookieJar()
    cookie_jar.load(cookie_file, ignore_expires=True)
    client.cookies.update(cookie_jar)
