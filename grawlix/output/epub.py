from grawlix.book import HtmlFiles, HtmlFile, OnlineFile, Book, SingleFile, Metadata, EpubInParts
from grawlix.exceptions import UnsupportedOutputFormat
from .output_format import OutputFormat, Update

import asyncio
import os
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from bs4 import BeautifulSoup
from ebooklib import epub
import rich


def _fix_fixed_layout_page(html_content: bytes, css_content: bytes = None) -> bytes:
    """
    Fix fixed-layout XHTML pages by adding viewport and fixing broken styles.

    Extracts dimensions from CSS and applies them to viewport and inline styles.
    """
    try:
        html_str = html_content.decode('utf-8')
    except UnicodeDecodeError:
        return html_content

    # Extract dimensions from CSS if provided
    width = None
    height = None
    if css_content:
        try:
            css_str = css_content.decode('utf-8')
            # Look for body width/height
            width_match = re.search(r'body\s*\{[^}]*width:\s*(\d+)px', css_str)
            height_match = re.search(r'body\s*\{[^}]*height:\s*(\d+)px', css_str)
            if width_match:
                width = width_match.group(1)
            if height_match:
                height = height_match.group(1)
        except UnicodeDecodeError:
            pass

    if not width or not height:
        return html_content

    # Add viewport meta tag if missing
    if 'name="viewport"' not in html_str and '<head>' in html_str:
        viewport_tag = f'<meta name="viewport" content="width={width}, height={height}"/>'
        html_str = html_str.replace('<head>', f'<head>\n    {viewport_tag}', 1)

    # Fix broken inline styles (width:px; height:px;)
    html_str = re.sub(
        r'style="width:px;\s*height:px;"',
        f'style="width:{width}px; height:{height}px;"',
        html_str
    )

    return html_str.encode('utf-8')


def _get_css_rule_key(rule_text: str) -> str | None:
    """Get unique key for a CSS rule. For @font-face, include font-family."""
    selector = rule_text.split('{')[0].strip()
    if selector == '@font-face':
        # Extract font-family to distinguish different font-faces
        match = re.search(r'font-family:\s*["\']?([^"\';}]+)', rule_text)
        if match:
            return f'@font-face:{match.group(1).strip()}'
        return None  # Skip font-face without font-family
    return selector if selector else None


def _extract_opf_metadata(opf_content: bytes) -> dict:
    """
    Extract rendition properties, cover info, and spine properties from OPF content.

    Returns dict with keys: rendition_layout, rendition_spread,
    rendition_orientation, cover_id, cover_href, spine_properties
    """
    result = {
        'rendition_layout': None,
        'rendition_spread': None,
        'rendition_orientation': None,
        'cover_id': None,
        'cover_href': None,
        'spine_properties': {},  # Maps href -> properties (e.g., 'page-spread-left')
    }

    try:
        root = ET.fromstring(opf_content)
        ns = {
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/',
        }

        # Find metadata element
        metadata = root.find('opf:metadata', ns)
        if metadata is None:
            metadata = root.find('{http://www.idpf.org/2007/opf}metadata')
        if metadata is None:
            return result

        # Extract rendition properties from <meta property="rendition:X">
        for meta in metadata.iter():
            if meta.tag.endswith('}meta') or meta.tag == 'meta':
                prop = meta.get('property', '')
                if prop == 'rendition:layout':
                    result['rendition_layout'] = meta.text
                elif prop == 'rendition:spread':
                    result['rendition_spread'] = meta.text
                elif prop == 'rendition:orientation':
                    result['rendition_orientation'] = meta.text

                # Cover reference: <meta name="cover" content="image-id"/>
                name = meta.get('name', '')
                if name == 'cover':
                    result['cover_id'] = meta.get('content')

        # Parse manifest once for cover info and id->href mapping
        manifest = root.find('opf:manifest', ns)
        if manifest is None:
            manifest = root.find('{http://www.idpf.org/2007/opf}manifest')

        id_to_href = {}
        if manifest is not None:
            for item in manifest.iter():
                item_id = item.get('id')
                item_href = item.get('href')
                if item_id and item_href:
                    id_to_href[item_id] = item_href

                # Check for cover by ID match
                if result['cover_id'] and item_id == result['cover_id'] and not result['cover_href']:
                    result['cover_href'] = item_href

                # Check for cover-image property
                props = item.get('properties', '')
                if 'cover-image' in props and not result['cover_href']:
                    result['cover_href'] = item_href
                    result['cover_id'] = item_id

        # Extract spine properties (page-spread-left, page-spread-right)
        spine = root.find('opf:spine', ns)
        if spine is None:
            spine = root.find('{http://www.idpf.org/2007/opf}spine')
        if spine is not None:
            # Extract spine itemref properties
            for itemref in spine.iter():
                if itemref.tag.endswith('}itemref') or itemref.tag == 'itemref':
                    idref = itemref.get('idref')
                    props = itemref.get('properties')
                    if idref and props and idref in id_to_href:
                        href = id_to_href[idref]
                        result['spine_properties'][href] = props

    except ET.ParseError:
        pass

    return result


class Epub(OutputFormat):
    extension = "epub"
    input_types = [SingleFile, HtmlFiles, EpubInParts]


    async def download(self, book: Book, location: str, update: Update) -> None:
        if isinstance(book.data, SingleFile):
            await self._download_single_file(book, location, update)
        elif isinstance(book.data, HtmlFiles):
            await self._download_html_files(book.data, book.metadata, location, update)
        elif isinstance(book.data, EpubInParts):
            await self._download_epub_in_parts(book.data, book.metadata, location, update)
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


    async def _download_epub_in_parts(self, data: EpubInParts, metadata: Metadata, location: str, update: Update) -> None:
        files = data.files
        file_count = len(files)
        progress = 1/(file_count)
        temporary_file_location = f"{location}.tmp"

        added_files: dict[str, int] = {}  # Track filepath -> content size
        opf_metadata: dict = {}
        css_cache: dict[str, bytes] = {}  # Store CSS content for fixing HTML pages
        cover_href: str = None  # Store cover image path from OPF
        spine_properties: dict[str, str] = {}  # Store spine properties (href -> properties)

        def should_add_file(zipfile: ZipFile, filename: str) -> bool:
            """Check if file should be added (new or larger than existing)"""
            # Skip directory entries, container files (ebooklib handles these), and OPF/NCX
            if filename.endswith("/"):
                return False
            if filename == "mimetype" or filename.startswith("META-INF/"):
                return False
            if filename.endswith(".opf") or filename.endswith(".ncx"):
                return False
            if filename not in added_files:
                return True
            # If file exists, only replace if new version is larger (non-empty beats empty)
            new_size = zipfile.getinfo(filename).file_size
            return new_size > added_files[filename]

        output = epub.EpubBook()
        opf_extracted = False
        for file in files:
            await self._download_and_write_file(file, temporary_file_location)
            with ZipFile(temporary_file_location, "r") as zipfile:
                # Extract OPF metadata from first OPF file (before skipping)
                if not opf_extracted:
                    for filename in zipfile.namelist():
                        if filename.endswith(".opf"):
                            opf_content = zipfile.read(filename)
                            opf_metadata = _extract_opf_metadata(opf_content)
                            # Store rendition properties in metadata
                            if opf_metadata.get('rendition_layout'):
                                metadata.rendition_layout = opf_metadata['rendition_layout']
                            if opf_metadata.get('rendition_spread'):
                                metadata.rendition_spread = opf_metadata['rendition_spread']
                            if opf_metadata.get('rendition_orientation'):
                                metadata.rendition_orientation = opf_metadata['rendition_orientation']
                            if opf_metadata.get('cover_href'):
                                cover_href = opf_metadata['cover_href']
                            if opf_metadata.get('spine_properties'):
                                spine_properties.update(opf_metadata['spine_properties'])
                            opf_extracted = True
                            break

                # Collect CSS files, merging content from all parts
                for filepath in zipfile.namelist():
                    if filepath.endswith(".css"):
                        content = zipfile.read(filepath)
                        if not content:
                            continue  # Skip empty files
                        if filepath not in css_cache:
                            css_cache[filepath] = content
                        else:
                            # Merge: combine rules, keeping the longer version for duplicate selectors
                            existing_str = css_cache[filepath].decode('utf-8', errors='ignore')
                            new_str = content.decode('utf-8', errors='ignore')

                            # Parse existing rules into dict: key -> full rule
                            existing_rules = {}
                            for rule in existing_str.split('}'):
                                if '{' in rule:
                                    rule_key = _get_css_rule_key(rule)
                                    if rule_key:
                                        existing_rules[rule_key] = rule.strip() + '}'

                            # Process new rules: add new ones, replace if longer
                            for rule in new_str.split('}'):
                                if '{' in rule:
                                    rule_key = _get_css_rule_key(rule)
                                    if rule_key:
                                        new_rule = rule.strip() + '}'
                                        if rule_key not in existing_rules or len(new_rule) > len(existing_rules[rule_key]):
                                            existing_rules[rule_key] = new_rule

                            # Rebuild CSS from merged rules
                            css_cache[filepath] = '\n'.join(existing_rules.values()).encode('utf-8')

                for filepath in zipfile.namelist():
                    # Skip CSS files here - they'll be added after all parts are merged
                    if filepath.endswith(".css"):
                        continue
                    if not should_add_file(zipfile, filepath):
                        continue
                    content = zipfile.read(filepath)
                    file_size = len(content)
                    if filepath.endswith("html"):
                        filename = os.path.basename(filepath)
                        # Fix fixed-layout pages if we have rendition:layout
                        if metadata.rendition_layout == 'pre-paginated':
                            # Find matching CSS (e.g., page1.xhtml -> page1.css)
                            css_path = filepath.replace('.xhtml', '.css').replace('.html', '.css')
                            css_content = css_cache.get(css_path)
                            if css_content:
                                content = _fix_fixed_layout_page(content, css_content)
                        is_in_toc = False
                        title = None
                        for key, value in data.files_in_toc.items():
                            toc_filename = key.split("#")[0]
                            if filename == toc_filename:
                                title = value
                                is_in_toc = True
                                break
                        # Use EpubItem to preserve original content (link tags, viewport, etc.)
                        # EpubHtml parses and regenerates HTML, stripping these
                        epub_file = epub.EpubItem(
                            file_name = filepath,
                            content = content,
                            media_type = 'application/xhtml+xml'
                        )
                        output.add_item(epub_file)
                        # Skip nav.xhtml from spine for fixed-layout (causes blank first page)
                        is_nav = any(x in filepath.lower() for x in ['nav.xhtml', 'nav.html', 'toc.xhtml', 'toc.html'])
                        if not (is_nav and metadata.rendition_layout == 'pre-paginated'):
                            # Check for spine properties (page-spread-left/right)
                            # Try matching with different path variations
                            props = None
                            for href, prop_value in spine_properties.items():
                                if filepath.endswith(href) or href.endswith(os.path.basename(filepath)):
                                    props = prop_value
                                    break
                            if props:
                                output.spine.append((epub_file, props))
                            else:
                                output.spine.append(epub_file)
                        if is_in_toc:
                            output.toc.append(epub_file)
                    else:
                        epub_file = epub.EpubItem(
                            file_name = filepath,
                            content = content
                        )
                        output.add_item(epub_file)
                    added_files[filepath] = file_size
            if update:
                update(progress)
        os.remove(temporary_file_location)

        # Add merged CSS files after all parts have been processed
        for css_path, css_content in css_cache.items():
            css_item = epub.EpubItem(
                file_name=css_path,
                content=css_content,
                media_type='text/css'
            )
            output.add_item(css_item)

        # Set cover image if found in source OPF, or detect from first page for fixed-layout
        if not cover_href and metadata.rendition_layout == 'pre-paginated':
            # Find first content page from spine (excluding nav/toc)
            first_page = None
            for spine_item in output.spine:
                item = spine_item[0] if isinstance(spine_item, tuple) else spine_item
                if hasattr(item, 'file_name') and item.file_name:
                    fname = item.file_name.lower()
                    # Skip nav and toc files
                    if 'nav.' in fname or 'toc.' in fname:
                        continue
                    if fname.endswith('.xhtml') or fname.endswith('.html'):
                        first_page = item
                        break

            if first_page and hasattr(first_page, 'content') and first_page.content:
                # Parse HTML to find all images and pick the largest one
                try:
                    content = first_page.content.decode('utf-8') if isinstance(first_page.content, bytes) else first_page.content
                    img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content)
                    if img_matches:
                        page_dir = os.path.dirname(first_page.file_name)
                        # Build lookup dict for item sizes
                        item_sizes = {
                            item.file_name: len(item.content)
                            for item in output.items
                            if hasattr(item, 'file_name') and item.file_name
                            and hasattr(item, 'content') and item.content
                        }
                        best_img = None
                        best_size = 0
                        for img_src in img_matches:
                            img_path = os.path.normpath(os.path.join(page_dir, img_src))
                            # Find matching item by suffix
                            for file_name, size in item_sizes.items():
                                if file_name.endswith(img_path):
                                    if size > best_size:
                                        best_size = size
                                        best_img = img_path
                                    break
                        if best_img:
                            cover_href = best_img
                except (UnicodeDecodeError, AttributeError):
                    pass

        if cover_href:
            # Find the cover image item and mark it as cover
            for item in output.items:
                if hasattr(item, 'file_name') and item.file_name and item.file_name.endswith(cover_href):
                    # Get or create item ID
                    item_id = item.id if hasattr(item, 'id') and item.id else os.path.basename(cover_href).replace('.', '-')
                    if not item.id:
                        item.id = item_id
                    # Add EPUB 2 cover metadata: <meta name="cover" content="image-id"/>
                    output.add_metadata('OPF', 'meta', '', {'name': 'cover', 'content': item_id})
                    # Mark item with EPUB 3 cover-image property
                    if not hasattr(item, 'properties') or item.properties is None:
                        item.properties = []
                    if 'cover-image' not in item.properties:
                        item.properties.append('cover-image')
                    break

        # Apply rendition properties to output (fixed-layout support)
        if metadata.rendition_layout:
            output.add_metadata(None, 'meta', metadata.rendition_layout, {'property': 'rendition:layout'})
        if metadata.rendition_spread:
            output.add_metadata(None, 'meta', metadata.rendition_spread, {'property': 'rendition:spread'})
        if metadata.rendition_orientation:
            output.add_metadata(None, 'meta', metadata.rendition_orientation, {'property': 'rendition:orientation'})

        output.add_item(epub.EpubNcx())
        nav = epub.EpubNav()
        output.add_item(nav)

        # For fixed-layout, remove nav from spine (it shouldn't be in reading order)
        if metadata.rendition_layout == 'pre-paginated':
            output.spine = [item for item in output.spine if item != nav and not (isinstance(item, tuple) and item[0] == nav)]

        epub.write_epub(location, output)
