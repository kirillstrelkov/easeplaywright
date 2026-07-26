"""Base page object."""

from easeplaywright.browser import Browser
from easeplaywright.utils import Logger


class BasePageObject:
    """Base page object."""

    def __init__(self, browser: Browser, logger: Logger) -> None:
        """Initiliaze."""
        self.browser = browser
        self.logger = logger
