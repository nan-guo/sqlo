"""Exceptions raised by sqlo."""


class UnsupportedFeatureError(ValueError):
    """The query uses a feature the dialect it is built for does not support.

    It is a ``ValueError`` like the other "this call is not valid" errors, and
    it is raised instead of generating SQL that would fail, or silently mean
    something else, on that database.
    """

    def __init__(self, dialect: str, feature: str, hint: str = "") -> None:
        message = f"{feature} is not supported by the {dialect} dialect."
        if hint:
            message = f"{message} {hint}"
        super().__init__(message)
        self.dialect = dialect
        self.feature = feature
