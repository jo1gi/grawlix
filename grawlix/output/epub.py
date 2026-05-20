from .context import Context

from grawlix.book import HtmlFiles, HtmlFile, Book, Metadata, EpubInParts
from grawlix.utils import http, blob

import asyncio
from bs4 import BeautifulSoup
import os
from ebooklib import epub
from zipfile import ZipFile

async def download_html_files(context: Context, book: Book[HtmlFiles], location: str) -> None:
    """
    Download html files into an epub.

    :param context: The download context.
    :param book: The book to download.
    :param location: The output path.
    """
    output = epub.EpubBook()
    output.set_title(book.metadata.title)
    for author in book.metadata.authors:
        output.add_author(author)
    file_count = len(book.data.htmlfiles) + 1 # Html files + cover

    async def download_cover(cover_file: blob.Blob):
        cover_filename = f"cover.{blob.extension_of_format(cover_file.format)}"
        epub_cover = epub.EpubCover(file_name = cover_filename)
        epub_cover.content = await blob.get_content(cover_file, context.client)
        output.add_item(epub_cover)
        epub_cover_page = epub.EpubCoverHtml(image_name = cover_filename)
        context.advance(1/file_count)
        return epub_cover_page


    async def download_file(index: int, file: HtmlFile):
        response = await blob.get_content(file.file, context.client)
        soup = BeautifulSoup(response.text, "lxml")
        selected_element = soup.find(attrs=file.selector)
        epub_file = epub.EpubHtml(
            title = file.title,
            file_name = f"part {index}.html",
            content = str(selected_element)
        )
        context.advance(1/file_count)
        return epub_file

    # Download files
    tasks = [
        download_file(index, file)
        for index, file in enumerate(book.data.htmlfiles)
    ]
    if book.data.cover:
        tasks.append(download_cover(book.data.cover))
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


def find_title_in_toc(filepath: str, table_of_contents: dict[str, str]) -> str | None:
    """
    Find the given filepath in the table of contents.

    :param filepath: The path of an html file in the epub.
    :param table_of_contents: The table of contents for the final epub (from filenames to titles).
    :return: The title of the content of the given filepath
    """
    filename = os.path.basename(filepath)
    for key, title in table_of_contents.items():
        toc_filename = key.split("#")[0]
        if filename == toc_filename:
            return title
    return None


async def merge_epubs(context: Context, book: Book[EpubInParts], location: str) -> None:
    """
    Merge multiple epubs into a single epub.

    :param context: The download context
    :param book: The epubs to merge.
    :param location: The output location of the merged epub.
    """
    epubs = book.data
    metadata = book.metadata
    progress = 1/(len(epubs.files))
    temporary_file_location = f"{location}.tmp"

    added_files: set[str] = set()
    output = epub.EpubBook()
    for file in epubs.files:
        await blob.write_to_file(file, temporary_file_location, context.client)
        with ZipFile(temporary_file_location, "r") as zipfile:
            for filepath in zipfile.namelist():
                # The epubs may contain duplicate files which doesn't make sense to add again.
                # The .opf and .ncx files are generated, so it doesn't make sense to add them.
                if filepath in added_files or filepath.endswith(".opf") or filepath.endswith(".ncx"):
                    continue

                content = zipfile.read(filepath)

                if filepath.endswith("html"):
                    title = find_title_in_toc(filepath, epubs.files_in_toc)
                    epub_file = epub.EpubHtml(
                        title = title,
                        file_name = filepath,
                        content = content
                    )
                    output.add_item(epub_file)
                    output.spine.append(epub_file)

                    file_is_not_in_toc = title is None
                    if file_is_not_in_toc:
                        output.toc.append(epub_file)
                else:
                    epub_file = epub.EpubItem(
                        file_name = filepath,
                        content = content
                    )
                    output.add_item(epub_file)
                added_files.add(filepath)
        context.advance(progress)
    os.remove(temporary_file_location)

    output.add_item(epub.EpubNcx())
    output.add_item(epub.EpubNav())
    epub.write_epub(location, output)
