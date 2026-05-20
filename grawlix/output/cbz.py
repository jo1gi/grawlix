from .metadata import comicinfo
from .context import Context

from grawlix.book import ImageList, Book
from grawlix.utils import blob, http

from zipfile import ZipFile
import asyncio
import math

async def create_cbz_file(context: Context, book: Book[ImageList], location: str) -> None:
    """
    Create cbz file from list of images.

    :param context: The download context.
    :param book: The book to download.
    :param location: The location where the book should be downloaded.
    """
    semaphore = asyncio.Semaphore(10)
    images = book.data.images
    image_count = len(images)
    with ZipFile(location, mode="w") as zip:
        async def download_page(index: int, file: blob.Blob):
            async with semaphore:
                content = await blob.get_content(file, context.client)
                padded_index = str(index).zfill(math.ceil(math.log10(image_count)))
                zip.writestr(f"Image {padded_index}.{file.extension()}", content)
                context.advance(1/image_count)
        tasks = [
            asyncio.create_task(download_page(index, file))
            for index, file in enumerate(images)
        ]
        await asyncio.wait(tasks)
        zip.writestr("ComicInfo.xml", comicinfo.from_metadata(book.metadata))
