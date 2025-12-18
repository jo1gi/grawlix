"""
Convert PDF-in-epub files to proper PDF format.
Some sources (like Nextory) wrap PDF pages in epub containers.
"""

import os
import re
import zipfile
from io import BytesIO
from pypdf import PdfWriter, PdfReader


def convert_pdf_epub_to_pdf(epub_path: str) -> str:
    """
    Extract embedded PDFs from an epub and merge them into a single PDF.

    :param epub_path: Path to the epub file containing embedded PDFs
    :return: Path to the created PDF file
    """
    pdf_path = epub_path.rsplit('.', 1)[0] + '.pdf'

    with zipfile.ZipFile(epub_path, 'r') as zf:
        # Find all PDF files in the epub
        pdf_files = [f for f in zf.namelist() if f.endswith('.pdf')]

        if not pdf_files:
            raise ValueError("No PDF files found in epub")

        # Sort by numeric order (1.pdf, 2.pdf, ..., 10.pdf, 11.pdf, ...)
        def extract_number(path: str) -> int:
            match = re.search(r'/(\d+)\.pdf$', path)
            return int(match.group(1)) if match else 0

        pdf_files.sort(key=extract_number)

        # Merge all PDFs
        writer = PdfWriter()
        for pdf_file in pdf_files:
            pdf_data = zf.read(pdf_file)
            reader = PdfReader(BytesIO(pdf_data))
            for page in reader.pages:
                writer.add_page(page)

        # Write merged PDF
        with open(pdf_path, 'wb') as out_file:
            writer.write(out_file)

    # Remove the original epub
    os.remove(epub_path)

    return pdf_path


def is_pdf_in_epub(epub_path: str) -> bool:
    """
    Check if an epub contains embedded PDF files instead of HTML.

    :param epub_path: Path to the epub file
    :return: True if the epub contains PDF files
    """
    try:
        with zipfile.ZipFile(epub_path, 'r') as zf:
            for name in zf.namelist():
                if name.endswith('.pdf'):
                    return True
    except (zipfile.BadZipFile, FileNotFoundError):
        pass
    return False
