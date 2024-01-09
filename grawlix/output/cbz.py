from .output_format import OutputFormat, Update, Book
from grawlix.book import ImageList, OnlineFile
from grawlix.exceptions import UnsupportedOutputFormat
from .metadata.comicinfo import to_comic_info

from zipfile import ZipFile
import asyncio
import math

class Cbz(OutputFormat):
    """Comic book zip file"""

    extension: str = "cbz"
    input_types = [ImageList]

    async def download(self, book: Book, location: str, update: Update) -> None:
        if not isinstance(book.data, ImageList):
            raise UnsupportedOutputFormat
        semaphore = asyncio.Semaphore(10)
        images = book.data.images
        image_count = len(images)
        with ZipFile(location, mode="w") as zip:
            async def download_page(index: int, file: OnlineFile):
                async with semaphore:
                    content = await self._download_file(file)
                    padded_index = str(index).zfill(math.ceil(math.log10(image_count)))
                    zip.writestr(f"Image {padded_index}.{file.extension}", content)
                    if update:
                        update(1/image_count)
            tasks = [
                asyncio.create_task(download_page(index, file))
                for index, file in enumerate(images)
            ]
            await asyncio.wait(tasks)
            zip.writestr("ComicInfo.xml", to_comic_info(book.metadata))
