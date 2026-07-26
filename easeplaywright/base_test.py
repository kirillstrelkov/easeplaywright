"""Base test."""

from __future__ import annotations

from typing import Any
from unittest.case import TestCase

from easeplaywright.browser import Browser
from easeplaywright.utils import Logger


class BaseTest(TestCase):
    """Base test."""

    TC_NAME_WIDTH = 100
    BROWSER_NAME = None
    LOGGER = Logger(name="easeplaywright.base_test.BaseTest")

    @classmethod
    def setUpClass(cls: type[BaseTest], **kwargs: Any) -> None:  # noqa: ANN401
        """Set up class."""
        super().setUpClass()

        kwargs["browser_name"] = kwargs.get("browser_name") or cls.BROWSER_NAME
        kwargs["logger"] = kwargs.get("logger") or cls.LOGGER

        cls.logger = kwargs["logger"]
        cls.browser = Browser(**kwargs)

    @classmethod
    def tearDownClass(cls: type[BaseTest]) -> None:
        """Tear down class."""
        super().tearDownClass()
        cls.browser.quit()

    def setUp(self) -> None:
        """Set up."""
        TestCase.setUp(self)
        if self.browser.logger:
            name = self.id()
            symbols_before = "-" * int((self.TC_NAME_WIDTH - len(name) - 2) / 2)
            self.browser.logger.info(  # noqa: PLE1205
                "{} {} {}",
                symbols_before,
                name,
                symbols_before,
            )

    def tearDown(self) -> None:
        """Tear down."""
        TestCase.tearDown(self)

        if self.browser.logger:
            self.browser.logger.info("-" * self.TC_NAME_WIDTH)
