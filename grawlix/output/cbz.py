from .output_format import OutputFormat, Update
from grawlix.book import ImageList

import zipfile

class Cbz(OutputFormat):
    """Comic book zip file"""

    extension: str = "cbz"

    def dl_image_list(self, book: ImageList, location: str, update: Update) -> None:
        image_count = len(book.images)
        with zipfile.ZipFile(location, mode="w") as zip:
            for n, file in enumerate(book.images):
                content = self._download_file(file)
                zip.writestr(f"Image {n}.{file.extension}", content)
                if update:
                    update(1/image_count)
