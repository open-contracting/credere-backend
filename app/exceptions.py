class CredereError(Exception):
    """Base class for exceptions from within this application"""


class SkippedAwardError(CredereError):
    """Raised if an award needs to be skipped due to a data quality issue"""

    def __init__(self, message, data=None, url=None):
        self.message = (message,)
        self.data = data
        self.url = (url,)
        self.category = "SKIPPED_AWARD"
