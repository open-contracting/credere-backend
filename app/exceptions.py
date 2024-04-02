class CredereError(Exception):
    """Base class for exceptions from within this application"""


class SkippedAwardError(CredereError):
    """Raised if an award needs to be skipped due to a data quality issue"""

    def __init__(self, message, url="", data=None):
        self.category = "SKIPPED_AWARD"
        self.message = message
        self.url = url
        if data is None:
            self.data = {}
        else:
            self.data = data
