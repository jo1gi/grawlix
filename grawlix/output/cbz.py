from .metadata import comicinfo
from grawlix.book import ImageList, Book
from grawlix.utils import blob, http

from zipfile import ZipFile
import asyncio
import math

async def create_cbz_file(book: Book[ImageList], location: str, update: http.Update) -> None:
    client = http.create_client()
    semaphore = asyncio.Semaphore(10)
    images = book.data.images
    image_count = len(images)
    with ZipFile(location, mode="w") as zip:
        async def download_page(index: int, file: blob.Blob):
            async with semaphore:
                content = await blob.get_content(file, client)
                padded_index = str(index).zfill(math.ceil(math.log10(image_count)))
                zip.writestr(f"Image {padded_index}.{blob.extension_of_format(file.format)}", content)
                if update:
                    update(1/image_count)
        tasks = [
            asyncio.create_task(download_page(index, file))
            for index, file in enumerate(images)
        ]
        await asyncio.wait(tasks)
        zip.writestr("ComicInfo.xml", comicinfo.from_metadata(book.metadata))
