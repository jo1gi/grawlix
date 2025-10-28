# grawlix
![GitHub release](https://img.shields.io/github/v/release/jo1gi/grawlix)
![GitHub top language](https://img.shields.io/github/languages/top/jo1gi/grawlix)
![License](https://img.shields.io/github/license/jo1gi/grawlix)
[![Donate using Ko-Fi](https://img.shields.io/badge/donate-kofi-00b9fe?logo=ko-fi&logoColor=00b9fe)](https://ko-fi.com/jo1gi)

CLI ebook downloader

## Supported services
grawlix currently supports downloading from the following sources:
- [DC Universe Infinite](https://www.dcuniverseinfinite.com)
- [eReolen](https://ereolen.dk)
- [fanfiction.net](https://www.fanfiction.net)
- [Flipp](https://flipp.dk)
- [Internet Archive](https://archive.org)
- [Manga Plus](https://mangaplus.shueisha.co.jp)
- [Marvel Unlimited](https://marvel.com)
- [Nextory](https://nextory.com)
- [Royal Road](https://www.royalroad.com)
- [Saxo](https://saxo.com)
- [Storytel / Mofibo](http://storytel.com)
- [Webtoons](https://webtoons.com)

## Installation

### From pypi (recommended)
```shell
pip install grawlix
```

### From repo (unstable)
```shell
git clone https://github.com/jo1gi/grawlix.git
cd grawlix
python3 setup.py install
```

## Authentication
Authentication can either be done with login (username and password) or cookies.
Not all sources support both methods.

### Login
Some sources require authentication, which can be done either with cli arguments
or a config file.

**Cli example**
```shell
grawlix --username "user@example.com" --password "SuperSecretPassword" <url>
```

**Config file example**
```toml
# Global settings
write_metadata_to_epub = true
output = "~/ebooks/{series}/{index} - {title}.{ext}"

[sources.storytel]
username = "user@example.com"
password = "SuperSecretPassword"
```

Config file should be placed in:
- Linux: `~/.config/grawlix/grawlix.toml`
- macOS: `~/Library/Application Support/grawlix/grawlix.toml`
- Windows: `%LOCALAPPDATA%\jo1gi\grawlix\grawlix.toml`

### Cookies
Some sources can be authenticated with Netscape cookie files. I use
[this extension](https://github.com/rotemdan/ExportCookies) to export my
cookies from my browser.

Cookies can be placed in current dir as `cookies.txt` or be given with the
`--cookies` argument.

## Configuration

### Global Settings

The following settings can be added to your config file (before any `[sources.*]` sections):

| Setting | Type | Description | Example |
|---------|------|-------------|---------|
| `write_metadata_to_epub` | boolean | Automatically write metadata to EPUB files (currently supports Storytel) | `true` or `false` |
| `output` | string | Default output path template (supports `~`, environment variables, and template variables) | `"~/ebooks/{title}.{ext}"` |

### Output Templates

The `output` setting supports template variables that are replaced with book metadata:

| Variable | Description | Example |
|----------|-------------|---------|
| `{title}` | Book title | "The Witcher" |
| `{series}` | Series name | "The Witcher Saga" |
| `{index}` | Series index/number | "1" |
| `{authors}` | Authors (semicolon-separated) | "Andrzej Sapkowski" |
| `{publisher}` | Publisher name | "Orbit" |
| `{language}` | Language code | "en" |
| `{release_date}` | Release date | "2020-01-15" |
| `{ext}` | File extension | "epub" |

**Example templates:**
```toml
# Simple
output = "~/books/{title}.{ext}"

# Organized by series
output = "~/books/{series}/{index} - {title}.{ext}"

# With author
output = "~/books/{authors}/{series}/{title}.{ext}"
```

**Path expansion:**
- `~` expands to home directory
- Environment variables work: `$HOME` (Unix) or `%USERPROFILE%` (Windows)
- Absolute paths: `/path/to/books` or `C:\Books`
- Relative paths: `downloads/{title}.{ext}` (relative to current directory)

## Download books

To download a book run:
```shell
grawlix [options] <book url>
```

### Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--version` | `-v` | Show version number |
| `--file <path>` | `-f` | File with URLs (one per line) |
| `--username <email>` | `-u` | Username for authentication |
| `--password <password>` | `-p` | Password for authentication |
| `--library <name>` | | Library name (for sources that require it) |
| `--cookies <path>` | `-c` | Path to Netscape cookie file |
| `--output <template>` | `-o` | Output path template (overrides config) |
| `--write-metadata-to-epub` | | Write metadata to EPUB files (overrides config) |
| `--debug` | | Enable debug messages |

**Examples:**
```shell
# Download to specific location
grawlix -o "~/downloads/{title}.{ext}" <url>

# Download with metadata writing
grawlix --write-metadata-to-epub <url>

# Batch download from file
grawlix -f urls.txt

# With authentication
grawlix -u user@example.com -p password <url>

# Debug mode
grawlix --debug <url>
```

## Metadata Writing

For supported sources (currently Storytel), grawlix can write rich metadata to EPUB files including:

- Title and original title
- Authors and translators
- Series information (Calibre-compatible)
- Publisher, ISBN, language
- Description and categories
- Release date

Enable globally in config:
```toml
write_metadata_to_epub = true
```

Or use the CLI flag for one-time use:
```shell
grawlix --write-metadata-to-epub <url>
```
