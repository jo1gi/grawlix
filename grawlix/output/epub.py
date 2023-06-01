from grawlix.book import HtmlFiles, HtmlFile, OnlineFile, Book, SingleFile, Metadata
from grawlix.exceptions import UnsupportedOutputFormat
from .output_format import OutputFormat, Update

import asyncio
from bs4 import BeautifulSoup
import os
from ebooklib import epub

class Epub(OutputFormat):
    extension = "epub"
    input_types = [SingleFile, HtmlFiles]

    async def download(self, book: Book, location: str, update: Update) -> None:
        if isinstance(book.data, SingleFile):
            await self._download_single_file(book, location, update)
        elif isinstance(book.data, HtmlFiles):
            await self._download_html_files(book.data, book.metadata, location, update)
        else:
            raise UnsupportedOutputFormat

    async def _download_html_files(self, html: HtmlFiles, metadata: Metadata, location: str, update: Update) -> None:
        output = epub.EpubBook()
        output.set_title(metadata.title)
        for author in metadata.authors:
            output.add_author(author)
        file_count = len(html.htmlfiles) + 1 # Html files + cover

        async def download_cover(cover_file: OnlineFile):
            cover_filename = f"cover.{cover_file.extension}"
            epub_cover = epub.EpubCover(file_name = cover_filename)
            epub_cover.content = await self._download_file(cover_file)
            output.add_item(epub_cover)
            epub_cover_page = epub.EpubCoverHtml(image_name = cover_filename)
            if update:
                update(1/file_count)
            return epub_cover_page


        async def download_file(index: int, file: HtmlFile):
            response = await self._client.get(
                file.file.url,
                headers = file.file.headers,
                cookies = file.file.cookies,
                follow_redirects=True
            )
            soup = BeautifulSoup(response.text, "lxml")
            selected_element = soup.find(attrs=file.selector)
            epub_file = epub.EpubHtml(
                title = file.title,
                file_name = f"part {index}.html",
                content = str(selected_element)
            )
            if update:
                update(1/file_count)
            return epub_file

        # Download files
        tasks = [
            download_file(index, file)
            for index, file in enumerate(html.htmlfiles)
        ]
        if html.cover:
            tasks.append(download_cover(html.cover))
        epub_files = await asyncio.gather(*tasks)

        # Add files to epub
        for epub_file in epub_files:
            output.add_item(epub_file)
            output.spine.append(epub_file)
            output.toc.append(epub_file)

        # Complete book
        output.add_item(epub.EpubNcx())
        output.add_item(epub.EpubNav())
        epub.write_epub(location, output)
