class CredereError(Exception):
    """Base class for exceptions from within this application"""


class SkippedAwardError(CredereError):
    """Raised if an award needs to be skipped due to a data quality issue"""
