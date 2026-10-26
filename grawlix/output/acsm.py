from grawlix.book import Book, SingleFile
from .output_format import OutputFormat, Update
import shutil
import subprocess

class Acsm(OutputFormat):
    extension = "acsm"
    input_types = [SingleFile]

    async def download(self, book: Book, location: str, update_func: Update) -> None:
        await self._download_single_file(book, location, update_func)
        # TODO: Implement more general solution
        # knock (if installed) fulfils the ACSM and strips the DRM, producing the ebook:
        # https://web.archive.org/web/20221016154220/https://github.com/BentonEdmondson/knock
        if shutil.which("knock") is not None:
            subprocess.run(
                ["knock", location],
                capture_output = True
            )
        # TODO: Warn when knock isn't installed
