"""Browser API tests."""

from unittest.case import TestCase

import pytest

from easeplaywright.browser import Browser
from tests.api import is_headless


# add test skip if browser is not supported
class BrowserConstrutorTest(TestCase):
    """Browser constructor tests."""

    def setUp(self) -> None:
        """Set up."""
        self.browser = None

    def tearDown(self) -> None:
        """Tear down."""
        if self.browser:
            self.browser.quit()


@pytest.mark.skipif(not Browser.supports("ff"), reason="Browser not supported")
class FirefoxTest(BrowserConstrutorTest):
    """Firefox tests."""

    def test_constructor_no_args(self) -> None:
        """Test default constructor."""
        self.browser = Browser()
        assert self.browser.is_ff()
        assert not is_headless(self.browser)

    def test_constructor(self) -> None:
        """Test constructor with arguments."""
        self.browser = Browser("ff", headless=False)
        assert self.browser.is_ff()
        assert not is_headless(self.browser)

    def test_constructor_by_name(self) -> None:
        """Test constructor with arguments."""
        self.browser = Browser(browser_name="ff", headless=False)
        assert self.browser.is_ff()
        assert not is_headless(self.browser)

    def test_constructor_headless(self) -> None:
        """Test constructor with headless True."""
        self.browser = Browser("ff", headless=True)
        assert self.browser.is_ff()
        assert is_headless(self.browser)


@pytest.mark.skipif(not Browser.supports("gc"), reason="Browser not supported")
class ChromeTest(BrowserConstrutorTest):
    """Chrome tests."""

    def test_constructor(self) -> None:
        """Test default constructor."""
        self.browser = Browser("gc", headless=False)
        assert self.browser.is_gc()
        assert not is_headless(self.browser)

    def test_constructor_by_name(self) -> None:
        """Test constructor with arguments."""
        self.browser = Browser(browser_name="gc", headless=False)
        assert self.browser.is_gc()
        assert not is_headless(self.browser)

    def test_constructor_headless(self) -> None:
        """Test constructor with headless True."""
        self.browser = Browser(browser_name="gc", headless=True)
        assert self.browser.is_gc()
        assert is_headless(self.browser)

    def test_constructor_special_options(self) -> None:
        """Test constructor with custom viewport, maximize disabled."""
        self.browser = Browser(
            browser_name="gc",
            headless=False,
            maximize=False,
            context_kwargs={"viewport": {"width": 1366, "height": 768}},
        )
        assert self.browser.is_gc()
        assert (
            1300  # noqa: PLR2004
            < self.browser.execute_js("return window.innerWidth")
            < 1400  # noqa: PLR2004
        )

    def test_constructor_headless_and_special_options(self) -> None:
        """Test constructor with headless and custom viewport."""
        self.browser = Browser(
            browser_name="gc",
            headless=True,
            maximize=False,
            context_kwargs={"viewport": {"width": 1366, "height": 768}},
        )
        assert self.browser.is_gc()
        assert is_headless(self.browser)
        assert (
            1350  # noqa: PLR2004
            < self.browser.execute_js("return window.innerWidth")
            < 1400  # noqa: PLR2004
        )
