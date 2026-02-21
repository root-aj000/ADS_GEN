"""Custom exception hierarchy."""


class AdGenError(Exception):
    """Base for every project exception."""


class SearchExhaustedError(AdGenError):
    """All engines returned zero usable results."""


class ImageDownloadError(AdGenError):
    """Image could not be downloaded or failed validation."""


class BackgroundRemovalError(AdGenError):
    """rembg processing failed in a non-recoverable way."""


class ConfigurationError(AdGenError):
    """Invalid or missing configuration."""