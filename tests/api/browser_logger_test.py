"""Browser logger tests."""

from __future__ import annotations

import pytest

from easeplaywright.base_test import BaseTest
from easeplaywright.browser import Browser
from easeplaywright.utils import Logger
from tests import EASEPLAYWRIGHT_TEST_URL


@pytest.mark.skipif(not Browser.supports("gc"), reason="Browser not supported")
class BrowserLoggerTest(BaseTest):
    """Check that browser actions produce log messages."""

    BROWSER_NAME = "gc"
    _captured: list[str] = []  # noqa: RUF012

    @classmethod
    def setUpClass(cls, **kwargs: object) -> None:  # noqa: D102
        cls._captured = []
        cls.LOGGER = Logger(
            log_to_console=False,
            handler=lambda msg: cls._captured.append(msg.record["message"]),
        )
        super().setUpClass(**kwargs)

    def setUp(self) -> None:  # noqa: D102
        super().setUp()
        self._captured.clear()

    def test_get_selected_text_from_dropdown_logs(self) -> None:
        """Check that get_selected_text_from_dropdown logs the action."""
        self.browser.get(EASEPLAYWRIGHT_TEST_URL)

        select_element = "select[name]"
        text = self.browser.get_selected_text_from_dropdown(by_css=select_element)

        assert text
        assert "Getting selected text from 'Element " in self._captured[0]
        assert f"-> '{text}'" in self._captured[0]
