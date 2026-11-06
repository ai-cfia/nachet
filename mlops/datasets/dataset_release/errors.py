"""Errors whose messages are safe to display in the administrative CLI."""


class ConfigurationError(ValueError):
    """An actionable configuration message that contains no supplied values."""


class ReleaseConflict(ValueError):
    """An existing version or object contains different content."""


class ReleaseNotReady(ValueError):
    """A release has not completed publication."""
