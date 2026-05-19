"""Exception types raised by the ETSI 014 client."""


class KMEError(Exception):
    """Base class for all KME client errors."""


class KMEHTTPError(KMEError):
    """Raised when the KME returns a non-2xx HTTP response.

    Attributes
    ----------
    status_code : int
    message : str
        The KME's error message (or response body), if available.
    """

    def __init__(self, status_code: int, message: str):
        super().__init__(f"KME returned HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class KMENotFoundError(KMEHTTPError):
    """Raised on HTTP 404 (e.g., key_ID not found or already retrieved)."""

    def __init__(self, message: str):
        super().__init__(404, message)
