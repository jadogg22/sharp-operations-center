class ReportServiceError(Exception):
    """Base class for failures intentionally exposed by the report API."""


class DataSourceQueryError(ReportServiceError):
    """Raised when SQLite demo data cannot satisfy a report query."""


class ReportNotFoundError(ReportServiceError):
    """Raised when a valid report request has no source rows."""


class InvalidReportError(ReportServiceError):
    """Raised when source rows cannot produce a valid report artifact."""
