"""Errors whose messages are safe to display in the administrative CLI."""


class ConfigurationError(ValueError):
    """An actionable configuration message that contains no supplied values."""
