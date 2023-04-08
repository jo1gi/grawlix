class GrawlixError(Exception):
    pass

class DataNotFound(GrawlixError):
    pass

class InvalidUrl(GrawlixError):
    pass

class UnsupportedOutputFormat(GrawlixError):
    pass

class NoSourceFound(GrawlixError):
    pass

class SourceNotAuthenticated(GrawlixError):
    pass

class MissingArgument(GrawlixError):
    pass

class ThrottleError(GrawlixError):
    pass
