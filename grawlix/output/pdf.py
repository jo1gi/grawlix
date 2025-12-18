from grawlix.book import Book, SingleFile
from .output_format import OutputFormat, Update


class Pdf(OutputFormat):
    extension = "pdf"
    input_types = [SingleFile]

    async def download(self, book: Book, location: str, update_func: Update) -> None:
        await self._download_single_file(book, location, update_func)
