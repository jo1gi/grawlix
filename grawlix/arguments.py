from grawlix import __version__

import argparse

def parse_arguments() -> argparse.Namespace:
    # Help
    parser = argparse.ArgumentParser(
        prog = "grawlix",
        description = "Download ebooks"
    )
    parser.add_argument(
        '-v',
        '--version',
        action = "version",
        version = f"grawlix {__version__}"
    )
    # Basics
    input_group = parser.add_argument_group("Inputs")
    input_group.add_argument(
        'urls',
        help = "Links to ebooks",
        nargs = "*"
    )
    input_group.add_argument(
        '-f',
        '--file',
        help = "File with links (One link per line)",
        dest = "file"
    )
    # Authentication
    authentication_group = parser.add_argument_group("Authentication")
    authentication_group.add_argument(
        '-u',
        '--username',
        help = "Username for login",
        dest = "username",
    )
    authentication_group.add_argument(
        '-p',
        '--password',
        help = "Password for login",
        dest = "password",
    )
    authentication_group.add_argument(
        '-c',
        '--cookies',
        help = "Path to netscape cookie file",
        dest = "cookie_file"
    )
    # Outputs
    output_group = parser.add_argument_group("Outputs")
    output_group.add_argument(
        '-o',
        '--output',
        help = "Output destination",
        dest = "output"
    )
    output_group.add_argument(
        '-m',
        '--export-metadata',
        help = "Export metadata",
        dest = "export_metadata",
        action="store_true"
    )
    # Logging
    logging_group = parser.add_argument_group("Logging")
    logging_group.add_argument(
        '--debug',
        help = "Enable debug messages",
        dest = "debug",
        action="store_true",
    )
    logging_group.add_argument(
        '--trace',
        help = "Enable trace messages",
        dest = "trace",
        action="store_true",
    )
    return parser.parse_args()
