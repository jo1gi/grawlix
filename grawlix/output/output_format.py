from grawlix.book import Book, SingleFile, OnlineFile, ImageList, HtmlFiles, Book, OfflineFile, BookData
from grawlix.exceptions import UnsupportedOutputFormat
from grawlix.encryption import decrypt

import httpx
from typing import Callable, Optional

Update = Optional[Callable[[float], None]]

class OutputFormat:
    # Extension for output files
    extension: str
    input_types: list[type[BookData]]

    def __init__(self) -> None:
        self._client = httpx.AsyncClient()


    async def close(self) -> None:
        """Cleanup"""
        await self._client.aclose()


    async def download(self, book: Book, location: str, update_func: Update) -> None:
        """
        Download book

        :param book: Book to download
        :param location: Path to where the file is written
        :param update_func: Function to update progress bar
        """
        raise UnsupportedOutputFormat


    async def _download_single_file(self, book: Book, location: str, update_func: Update) -> None:
        """
        Download and write an `grawlix.SingleFile` to disk

        :param book: Book to download
        :param location: Path to where the file is written
        :raises UnsupportedOutputFormat: If datatype is not supported by format
        """
        if not isinstance(book.data, SingleFile):
            raise UnsupportedOutputFormat
        if not book.data.file.extension == self.extension:
            raise UnsupportedOutputFormat
        if isinstance(book.data.file, OnlineFile):
            await self._download_and_write_file(book.data.file, location, update_func)
        elif isinstance(book.data.file, OfflineFile):
            self._write_offline_file(book.data.file, location)


    async def _download_file(self, file: OnlineFile, update: Update = None) -> bytes:
        """
        Download `grawlix.OnlineFile` 

        :param file: File to download
        :param update: Update function that is called with a percentage every time a chunk is downloaded
        :returns: Content of downloaded file
        """
        content = b""
        async with self._client.stream("GET", file.url, headers = file.headers, cookies = file.cookies, follow_redirects=True) as request:
            total_filesize = int(request.headers["Content-length"])
            async for chunk in request.aiter_bytes():
                content += chunk
                if update:
                    update(len(chunk)/total_filesize)
            if file.encryption is not None:
                content = decrypt(content, file.encryption)
        return content


    async def _download_and_write_file(self, file: OnlineFile, location: str, update: Update = None) -> None:
        """
        Download `grawlix.OnlineFile` and write to content to disk

        :param file: File to download
        :param location: Path to where the file is written
        :param update: Update function that is called with a percentage every time a chunk is downloaded
        """
        content = await self._download_file(file, update)
        with open(location, "wb") as f:
            f.write(content)


    def _write_offline_file(self, file: OfflineFile, location: str) -> None:
        """
        Write the content of an `OfflineFile` to disk

        :param file: File to write to disk
        :param location: Path to where the file is written
        """
        with open(location, "wb") as f:
            content = file.content
            if file.encryption:
                content = decrypt(content, file.encryption)
            f.write(content)
