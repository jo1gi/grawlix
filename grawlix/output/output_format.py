from grawlix.book import Book, SingleFile, OnlineFile, ImageList
from grawlix.exceptions import UnsupportedOutputFormat
from grawlix.encryption import decrypt

import requests
from typing import Callable, Optional

Update = Optional[Callable[[float], None]]

class OutputFormat:
    # Extension for output files
    extension: str = ""

    def __init__(self):
        self._session = requests.Session()


    def dl_single_file(self, book: SingleFile, location: str, update_func: Update) -> None:
        """
        Download and write an `grawlix.SingleFile` to disk

        :param book: Book to download
        :param location: Path to where the file is written
        :raises UnsupportedOutputFormat: If datatype is not supported by format
        """
        if not book.file.extension == self.extension:
            raise UnsupportedOutputFormat
        self._download_and_write_file(book.file, location)


    def dl_image_list(self, book: ImageList, location: str, update_func: Update) -> None:
        """
        Download and write an `grawlix.ImageList` to disk

        :param book: Book to download
        :param location: Path to where the file is written
        :raises UnsupportedOutputFormat: If datatype is not supported by format
        """
        raise UnsupportedOutputFormat


    def _download_file(self, file: OnlineFile) -> bytes:
        """
        Download `grawlix.OnlineFile` 

        :param file: File to download
        :returns: Content of downloaded file
        """
        response = self._session.get(
            file.url,
            headers = file.headers
        )
        content = response.content
        if file.encryption is not None:
            content = decrypt(content, file.encryption)
        return content


    def _download_and_write_file(self, file: OnlineFile, location: str) -> None:
        """
        Download `grawlix.OnlineFile` and write to content to disk

        :param file: File to download
        :param location: Path to where the file is written
        """
        content = self._download_file(file)
        with open(location, "wb") as f:
            f.write(content)
