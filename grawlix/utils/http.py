from grawlix import encryption, logging

from http.cookiejar import MozillaCookieJar
from typing import TypeAlias, Optional, Callable, Any, Literal
from dataclasses import dataclass
import httpx
import asyncio

Client: TypeAlias = httpx.AsyncClient
Update = Optional[Callable[[float], None]]

@dataclass(slots=True)
class Request:
    method: Literal["GET", "POST"]
    url: str
    headers: dict[str, str] | None = None
    cookies: Any = None
    follow_redirects: bool = True


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


async def download_with_progress(client: Client, request: Request, update: Update = None) -> bytes:
    """

    :param client: The client used to download the file.
    :param file: The file to download.
    :param update: Function called when a chunk is downloaded.
    """

    async def inner() -> bytes:
        content = b""
        async with client.stream(
                request.method,
                request.url,
                headers=request.headers,
                cookies=request.cookies,
                follow_redirects=request.follow_redirects
                ) as response:
            total_filesize = int(response.headers["Content-length"])
            async for chunk in response.aiter_bytes():
                content += chunk
                if update:
                    update(len(chunk)/total_filesize)
            return content

    e: BaseException = RuntimeError()
    for i in range(3):
        try:
            return await inner()
        except Exception as exception:
            logging.debug(f"Failed request to {request.url}. Trying again in 2 seconds.")
            e = exception
            await asyncio.sleep(2)
    raise e
