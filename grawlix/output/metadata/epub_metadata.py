"""
Generic EPUB metadata writer

Handles writing metadata to EPUB files from book.Metadata
"""

from grawlix import logging
from grawlix.book import Metadata
import zipfile
import tempfile
import os
import shutil


def write_metadata_to_epub(metadata: Metadata, epub_path: str) -> None:
    """
    Write metadata to EPUB file

    :param metadata: Metadata object from book
    :param epub_path: Path to the EPUB file
    """
    try:
        from lxml import etree as ET
        using_lxml = True
    except ImportError:
        import xml.etree.ElementTree as ET
        using_lxml = False

    # EPUB namespaces
    NAMESPACES = {
        'opf': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'dcterms': 'http://purl.org/dc/terms/',
    }

    # Register namespaces for ElementTree
    if not using_lxml:
        for prefix, uri in NAMESPACES.items():
            ET.register_namespace(prefix, uri)

    # Create temporary directory for EPUB extraction
    temp_dir = tempfile.mkdtemp()

    try:
        # Extract EPUB
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # Find OPF file
        opf_path = _find_opf_file(temp_dir)
        if not opf_path:
            logging.debug("Could not find OPF file in EPUB")
            return

        # Parse OPF file
        if using_lxml:
            parser = ET.XMLParser(recover=True, encoding='utf-8')
            tree = ET.parse(opf_path, parser)
        else:
            tree = ET.parse(opf_path)

        root = tree.getroot()

        # Find metadata element
        if using_lxml:
            metadata_elem = root.find('.//opf:metadata', NAMESPACES)
        else:
            metadata_elem = root.find('opf:metadata', NAMESPACES)

        if metadata_elem is None:
            logging.debug("Could not find metadata element in OPF")
            return

        # Update metadata
        _update_epub_metadata(metadata_elem, metadata, NAMESPACES, using_lxml)

        # Write updated OPF
        if using_lxml:
            tree.write(opf_path, encoding='utf-8', xml_declaration=True, pretty_print=True)
        else:
            tree.write(opf_path, encoding='utf-8', xml_declaration=True)

        # Repack EPUB
        _repack_epub(temp_dir, epub_path)

        logging.debug("Successfully wrote metadata to EPUB")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def _find_opf_file(epub_dir: str) -> str:
    """Find the OPF file in extracted EPUB directory"""
    container_path = os.path.join(epub_dir, 'META-INF', 'container.xml')

    if os.path.exists(container_path):
        try:
            from lxml import etree as ET
        except ImportError:
            import xml.etree.ElementTree as ET

        tree = ET.parse(container_path)
        root = tree.getroot()
        rootfile = root.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile')
        if rootfile is not None:
            opf_relative_path = rootfile.get('full-path')
            return os.path.join(epub_dir, opf_relative_path)

    # Fallback: search for .opf file
    for root_dir, dirs, files in os.walk(epub_dir):
        for file in files:
            if file.endswith('.opf'):
                return os.path.join(root_dir, file)

    return None


def _update_epub_metadata(metadata_elem, metadata: Metadata, ns: dict, using_lxml: bool) -> None:
    """Update EPUB metadata elements from Metadata object"""
    if using_lxml:
        from lxml import etree as ET
    else:
        import xml.etree.ElementTree as ET

    # Helper function to create/update element
    def update_or_create_element(tag: str, text: str, attribs: dict = None):
        if not text:
            return

        # Remove existing elements with this tag
        for elem in list(metadata_elem.findall(tag, ns)):
            metadata_elem.remove(elem)

        # Create new element
        elem = ET.SubElement(metadata_elem, tag)
        elem.text = str(text)
        if attribs:
            for key, value in attribs.items():
                elem.set(key, value)

    # Helper to create meta element
    def create_meta(name: str, content):
        if content is None:
            return
        meta = ET.SubElement(metadata_elem, f"{{{ns['opf']}}}meta")
        meta.set('name', name)
        meta.set('content', str(content))

    # Title
    update_or_create_element(f"{{{ns['dc']}}}title", metadata.title)

    # Original Title (EPUB 3 with refinements)
    if metadata.original_title:
        # Create title with ID for main title
        for elem in list(metadata_elem.findall(f"{{{ns['dc']}}}title", ns)):
            elem.set('id', 'main-title')

        # Add original title
        orig_title = ET.SubElement(metadata_elem, f"{{{ns['dc']}}}title")
        orig_title.set('id', 'original-title')
        orig_title.text = metadata.original_title

        # Add meta refinement for original title
        meta = ET.SubElement(metadata_elem, f"{{{ns['opf']}}}meta")
        meta.set('refines', '#original-title')
        meta.set('property', 'title-type')
        meta.text = 'original'

    # Authors
    for author in metadata.authors:
        creator = ET.SubElement(metadata_elem, f"{{{ns['dc']}}}creator")
        creator.text = author
        creator.set(f"{{{ns['opf']}}}role", "aut")

    # Translators
    for translator in metadata.translators:
        contributor = ET.SubElement(metadata_elem, f"{{{ns['dc']}}}contributor")
        contributor.text = translator
        contributor.set(f"{{{ns['opf']}}}role", "trl")

    # Description
    update_or_create_element(f"{{{ns['dc']}}}description", metadata.description)

    # Language
    update_or_create_element(f"{{{ns['dc']}}}language", metadata.language)

    # Publisher
    update_or_create_element(f"{{{ns['dc']}}}publisher", metadata.publisher)

    # ISBN (from identifier field)
    if metadata.isbn:
        # Remove existing ISBN identifiers
        for elem in list(metadata_elem.findall(f"{{{ns['dc']}}}identifier", ns)):
            scheme = elem.get(f"{{{ns['opf']}}}scheme")
            if scheme and scheme.upper() == "ISBN":
                metadata_elem.remove(elem)

        # Add new ISBN
        identifier = ET.SubElement(metadata_elem, f"{{{ns['dc']}}}identifier")
        identifier.text = metadata.isbn
        identifier.set(f"{{{ns['opf']}}}scheme", "ISBN")

    # Release Date (convert date to string)
    release_date_str = metadata.release_date.isoformat() if metadata.release_date else None
    update_or_create_element(f"{{{ns['dc']}}}date", release_date_str)

    # Category
    if metadata.category:
        subject = ET.SubElement(metadata_elem, f"{{{ns['dc']}}}subject")
        subject.text = metadata.category

    # Tags
    for tag in metadata.tags:
        subject = ET.SubElement(metadata_elem, f"{{{ns['dc']}}}subject")
        subject.text = tag

    # Series info (Calibre format) - using series and index fields
    if metadata.series:
        create_meta("calibre:series", metadata.series)
        create_meta("calibre:series_index", metadata.index)

    # EPUB 3 rendition properties (fixed-layout support)
    # These use <meta property="...">value</meta> format, not name/content
    def create_meta_property(property_name: str, value: str):
        if not value:
            return
        # Remove existing property if present
        for elem in list(metadata_elem):
            if elem.get('property') == property_name:
                metadata_elem.remove(elem)
        meta = ET.SubElement(metadata_elem, 'meta')
        meta.set('property', property_name)
        meta.text = value

    if metadata.rendition_layout:
        create_meta_property('rendition:layout', metadata.rendition_layout)
    if metadata.rendition_spread:
        create_meta_property('rendition:spread', metadata.rendition_spread)
    if metadata.rendition_orientation:
        create_meta_property('rendition:orientation', metadata.rendition_orientation)


def _repack_epub(epub_dir: str, output_path: str) -> None:
    """Repack EPUB directory into ZIP file"""
    # Remove old EPUB
    if os.path.exists(output_path):
        os.remove(output_path)

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub_zip:
        # mimetype must be first and uncompressed
        mimetype_path = os.path.join(epub_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            epub_zip.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)

        # Add all other files
        for root, dirs, files in os.walk(epub_dir):
            for file in files:
                if file == 'mimetype':
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, epub_dir)
                epub_zip.write(file_path, arcname)
