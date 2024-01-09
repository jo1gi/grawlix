from grawlix.logging import print_error_file

ISSUE_URL = "https://github.com/jo1gi/grawlix/issues"
REPO_URL = "https://github.com/jo1gi/grawlix"

class GrawlixError(Exception):
    error_file: str

    def print_error(self) -> None:
        print_error_file(
            self.error_file,
            repo = REPO_URL,
            issue = ISSUE_URL,
        )


class DataNotFound(GrawlixError):
    error_file = "data_not_found"

class InvalidUrl(GrawlixError):
    error_file = "invalid_url"

class UnsupportedOutputFormat(GrawlixError):
    error_file = "unsupported_output_format"

class SourceNotAuthenticated(GrawlixError):
    error_file = "source_not_authenticated"

class ThrottleError(GrawlixError):
    error_file = "throttle"

class AccessDenied(GrawlixError):
    error_file = "access_denied"
