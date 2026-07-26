"""Browser module."""

from __future__ import annotations

import time
import traceback
from contextlib import contextmanager
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Union

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from easeplaywright.mouse import Mouse
from easeplaywright.utils import get_random_value

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from loguru import Logger
    from playwright.sync_api import Browser as PlaywrightBrowser
    from playwright.sync_api import BrowserContext, BrowserType, Frame, Page, Playwright

TypeElement = Union[str, Locator]


class NoSuchElementException(Exception):  # noqa: N818
    """Raised when no element matches a selector."""


class TimeoutException(Exception):  # noqa: N818
    """Raised when a wait condition is not met in time."""


def browser_decorator(  # noqa: PLR0913
    browser_name: str | None = None,
    timeout: float = 5,
    logger: Logger | None = None,
    *,
    headless: bool = False,
    maximize: bool = True,
    launch_kwargs: dict[str, Any] | None = None,
    context_kwargs: dict[str, Any] | None = None,
) -> Any:  # noqa: ANN401
    """Wrap a function with browser setup and teardown."""

    def func_decorator(func: Callable[..., Any]) -> Any:  # noqa: ANN401
        def wrapper(*args: object, **kwargs: object) -> Any:  # noqa: ANN401
            browser = None
            return_value = None
            try:
                browser = Browser(
                    browser_name=browser_name,
                    logger=logger,
                    timeout=timeout,
                    headless=headless,
                    maximize=maximize,
                    launch_kwargs=launch_kwargs,
                    context_kwargs=context_kwargs,
                )

                kwargs["browser"] = browser
                value = func(*args, **kwargs)
                return_value = value
            except Exception:  # noqa: BLE001
                traceback.print_exc()
            finally:
                if browser:
                    browser.quit()

            return return_value

        return wrapper

    return func_decorator


@contextmanager
def browser_context(  # noqa: PLR0913
    browser_name: str | None = None,
    timeout: float = 5,
    logger: Logger | None = None,
    *,
    headless: bool = False,
    maximize: bool = True,
    launch_kwargs: dict[str, Any] | None = None,
    context_kwargs: dict[str, Any] | None = None,
) -> Generator[Browser]:
    """Context manager that yields a Browser and quits it on exit."""
    browser = Browser(
        browser_name=browser_name,
        logger=logger,
        timeout=timeout,
        headless=headless,
        maximize=maximize,
        launch_kwargs=launch_kwargs,
        context_kwargs=context_kwargs,
    )
    try:
        yield browser
    except Exception:  # noqa: BLE001
        traceback.print_exc()
    finally:
        browser.quit()


class Browser:
    """Browser class."""

    FF: Final = "ff"
    FF_HEADLESS: Final = "ff_headless"
    GC: Final = "gc"
    GC_HEADLESS: Final = "gc_headless"
    EDGE: Final = "edge"
    EDGE_HEADLESS: Final = "edge_headless"
    DEFAULT_BROWSER: str | None = None

    DEFAULT_VIEWPORT: Final = {"width": 1920, "height": 1080}

    __BROWSERS: Final = [
        FF,
        FF_HEADLESS,
        GC,
        GC_HEADLESS,
        EDGE,
        EDGE_HEADLESS,
    ]

    __BROWSER_TYPE_MAPPING: Final = {
        FF: "firefox",
        FF_HEADLESS: "firefox",
        GC: "chromium",
        GC_HEADLESS: "chromium",
        EDGE: "chromium",
        EDGE_HEADLESS: "chromium",
    }

    __LOCATOR_MAPPINGS: Final = {
        "by_id": lambda v: f'[id="{v}"]',
        "by_xpath": lambda v: f"xpath={v}",
        "by_tag": lambda v: v,
        "by_name": lambda v: f'[name="{v}"]',
        "by_css": lambda v: v,
        "by_class": lambda v: f'[class~="{v}"]',
        "by_link": lambda v: f'a:text-is("{v}")',
        "by_partial_link": lambda v: f'a:text("{v}")',
    }

    def __init__(  # noqa: PLR0913
        self,
        browser_name: str | None = None,
        logger: Logger | None = None,
        timeout: float = 5,
        *,
        headless: bool = False,
        maximize: bool = True,
        launch_kwargs: dict[str, Any] | None = None,
        context_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Launch a browser, open a context/page and start a Playwright session."""
        launch_kwargs = dict(launch_kwargs) if launch_kwargs else {}
        context_kwargs = dict(context_kwargs) if context_kwargs else {}

        self.__browser_name = self.DEFAULT_BROWSER or browser_name or self.FF

        self.logger = logger
        self.__timeout = timeout
        self.__headless = headless or "headless" in self.__browser_name

        launch_kwargs.setdefault("headless", self.__headless)
        if self.is_edge():
            launch_kwargs.setdefault("channel", "msedge")

        if maximize:
            context_kwargs.setdefault("viewport", dict(self.DEFAULT_VIEWPORT))
        else:
            context_kwargs.setdefault("no_viewport", True)

        self.__playwright: Playwright = sync_playwright().start()
        browser_type: BrowserType = getattr(
            self.__playwright,
            self.__BROWSER_TYPE_MAPPING[self.__browser_name],
        )
        self._browser: PlaywrightBrowser = browser_type.launch(**launch_kwargs)
        self._context: BrowserContext = self._browser.new_context(**context_kwargs)
        self._context.set_default_timeout(timeout * 1000)
        self._page: Page = self._context.new_page()
        self._frame: Frame | Page = self._page

        self.__pending_dialog_action: str | None = None
        self._context.on("page", self.__attach_dialog_handler)
        self.__attach_dialog_handler(self._page)

        self.mouse = Mouse(self)

    def __attach_dialog_handler(self, page: Page) -> None:
        page.on("dialog", self.__handle_dialog)

    def __handle_dialog(self, dialog: Any) -> None:  # noqa: ANN401
        action = self.__pending_dialog_action or "accept"
        self.__pending_dialog_action = None
        if action == "accept":
            dialog.accept()
        else:
            dialog.dismiss()

    @classmethod
    def supports(cls: type[Browser], browser_name: str) -> bool:
        """Return True if browser is supported and its binary is installed, False otherwise."""
        return cls._is_installed(browser_name)

    @classmethod
    @cache
    def _is_installed(cls: type[Browser], browser_name: str) -> bool:
        if browser_name not in cls.__BROWSERS:
            return False

        browser_type_name = cls.__BROWSER_TYPE_MAPPING[browser_name]
        try:
            with sync_playwright() as playwright:
                browser_type = getattr(playwright, browser_type_name)
                return Path(browser_type.executable_path).exists()
        except Exception:  # noqa: BLE001
            return False

    @classmethod
    def get_supported_browsers(cls: type[Browser]) -> list[str]:
        """Return supported browsers."""
        return cls.__BROWSERS

    def get_browser_initials(self) -> str | None:
        """Return browser initials."""
        return self.__browser_name

    def is_ff(self) -> bool:
        """Return True if browser is Firefox."""
        return self.__browser_name.startswith(Browser.FF)

    def is_gc(self) -> bool:
        """Return True if browser is Google Chrome."""
        return self.__browser_name.startswith(Browser.GC)

    def is_edge(self) -> bool:
        """Return True if browser is Edge."""
        return self.__browser_name.startswith(Browser.EDGE)

    def is_headless(self) -> bool:
        """Return True if browser was launched headless."""
        return self.__headless

    def get_by_query(  # noqa: PLR0913, PLR0917
        self,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> str:
        """Return element as a Playwright selector string built from a by_* query."""
        for locator, value in (
            ("by_id", by_id),
            ("by_xpath", by_xpath),
            ("by_tag", by_tag),
            ("by_name", by_name),
            ("by_css", by_css),
            ("by_class", by_class),
            ("by_link", by_link),
            ("by_partial_link", by_partial_link),
        ):
            if value is not None:
                return self.__LOCATOR_MAPPINGS[locator](value)

        msg = "Failed to find element"
        raise ValueError(msg)

    def _get_selector(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> TypeElement:
        assert (  # noqa: S101
            element is not None
            or by_id is not None
            or by_xpath is not None
            or by_link is not None
            or by_partial_link is not None
            or by_name is not None
            or by_tag is not None
            or by_css is not None
            or by_class is not None
        ), "'element' or 'by_*' not specified"

        if element is not None:
            return element

        return self.get_by_query(
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )

    def __resolve_root(self, parent: TypeElement | None) -> Frame | Page | Locator:
        if parent is None:
            return self._frame
        if isinstance(parent, str):
            return self._frame.locator(parent)
        return parent

    def _get_locator(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> Locator:
        selector = self._get_selector(
            element=element,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        if isinstance(selector, str):
            root = self.__resolve_root(parent)
            return root.locator(selector)

        return selector

    def to_string(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> str:
        """Return element as string."""
        selector = self._get_selector(
            element=element,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        if isinstance(selector, str):
            return f"Element {{selector: '{selector}'}}"

        try:
            info = selector.first.evaluate(
                "el => ({"
                "tag: el.tagName.toLowerCase(), "
                "id: el.id || null, "
                "cls: el.className || null, "
                "text: (el.textContent || '').trim() || null, "
                "value: el.value ?? null, "
                "name: (el.tagName === 'FRAME' || el.tagName === 'IFRAME') ? el.name : null"
                "})",
            )
        except (PlaywrightError, PlaywrightTimeoutError):
            return "Element {}"

        parts = [f"tag_name: '{info['tag']}'"]
        if info.get("id"):
            parts.append(f"id: '{info['id']}'")
        if info.get("cls"):
            parts.append(f"class: '{info['cls']}'")
        if info.get("text"):
            parts.append(f"text: '{info['text']}'")
        if info.get("value") not in (None, ""):
            parts.append(f"value: '{info['value']}'")
        if info.get("name"):
            parts.append(f"name: '{info['name']}'")

        return f"Element {{{', '.join(parts)}}}"

    def _safe_log(self, *args: object) -> None:
        if not self.logger:
            return
        converted = [self.to_string(arg) if isinstance(arg, Locator) else str(arg) for arg in args]
        self.logger.info(*converted)

    def type(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        text: str | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Type text at element."""
        locator = self._get_locator(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        self.wait_for_visible(element=locator)
        locator = locator.first

        assert text is not None, "text not specified"  # noqa: S101
        self._safe_log("Typing '{}' at '{}'", text, locator)

        locator.fill(text)

    def click(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Click on element."""
        locator = self._get_locator(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        self.wait_for_visible(element=locator)
        locator = locator.first

        self._safe_log("Clicking at '{}'", locator)

        locator.click()

    def get_parent(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> Locator:
        """Return parent element."""
        locator = self.find_element(
            element=element,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        return locator.locator("xpath=..")

    def get_text(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
        *,
        visible: bool = True,
    ) -> str:
        """Return text of the element."""
        locator = self._get_locator(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        if visible:
            self.wait_for_visible(element=locator)
        text = locator.first.inner_text()

        self._safe_log("Getting text from '{}' -> '{}'", locator, text)

        return text

    def get_attribute(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        attr: str | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
        *,
        visible: bool = False,
    ) -> str | None:
        """Return attribute of the element."""
        assert attr is not None, "attr is not specified"  # noqa: S101
        locator = self._get_locator(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        if visible:
            self.wait_for_visible(element=locator)
        value = locator.first.get_attribute(attr)

        self._safe_log(f"Getting attribute {attr} from {locator} -> {value}")

        return value

    def get_tag_name(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> str:
        """Return tag name of the element."""
        locator = self.find_element(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        return locator.evaluate("el => el.tagName.toLowerCase()")

    def get_id(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
        *,
        visible: bool = False,
    ) -> str | None:
        """Return id of the element."""
        return self.get_attribute(
            element=element,
            attr="id",
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
            visible=visible,
        )

    def get_class(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
        *,
        visible: bool = False,
    ) -> str | None:
        """Return class of the element."""
        return self.get_attribute(
            element=element,
            attr="class",
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
            visible=visible,
        )

    def get_value(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
        *,
        visible: bool = True,
    ) -> str | None:
        """Return value of the element."""
        return self.get_attribute(
            element=element,
            attr="value",
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
            visible=visible,
        )

    def get_location(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> tuple[int, int]:
        """Return tuple like (x, y)."""
        locator = self.find_element(
            element=element,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        box = locator.bounding_box()
        if box is None:
            msg = f"Failed to get location for selector - {element}"
            raise NoSuchElementException(msg)

        self._safe_log(f"Getting location from {locator} -> {box}")

        return int(box["x"]), int(box["y"])

    def get_dimensions(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> tuple[int | float, int | float]:
        """Return tuple like (width, height)."""
        locator = self.find_element(
            element=element,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        box = locator.bounding_box()
        if box is None:
            msg = f"Failed to get dimensions for selector - {element}"
            raise NoSuchElementException(msg)

        self._safe_log(f"Getting dimensions from {locator} -> {box}")

        return box["width"], box["height"]

    def get_selected_value_from_dropdown(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> str | None:
        """Return value of the selected option."""
        locator = self._get_locator(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        self.wait_for_visible(element=locator)

        value = locator.first.input_value()

        self._safe_log("Getting selected value from '{}' -> '{}'", locator, value)

        return value

    def get_selected_text_from_dropdown(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> str:
        """Return text of the selected option."""
        locator = self._get_locator(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        self.wait_for_visible(element=locator)

        text = locator.first.evaluate(
            "el => el.options[el.selectedIndex] ? el.options[el.selectedIndex].text : ''",
        )

        self._safe_log("Getting selected text from '{}' -> '{}'", locator, text)

        return text

    def select_option_by_value_from_dropdown(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        value: str | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Select option by value."""
        locator = self._get_locator(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        self.wait_for_visible(element=locator)

        assert value is not None, "value not specified"  # noqa: S101

        self._safe_log(f"Selecting by value {value} from {locator}")

        locator.first.select_option(value=value)

    def select_option_by_text_from_dropdown(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        text: str | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Select option by text."""
        locator = self._get_locator(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        self.wait_for_visible(element=locator)

        assert text is not None, "text not specified"  # noqa: S101
        self._safe_log(f"Selecting by text {text} from {locator}")

        locator.first.select_option(label=text)

    def select_option_by_index_from_dropdown(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        index: int = 0,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Select option by index."""
        locator = self._get_locator(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        self.wait_for_visible(element=locator)

        self._safe_log(f"Selecting by index {index} from {locator}")

        locator.first.select_option(index=index)

    def select_random_option_from_dropdown(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        texts_to_skip: set[str] | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Select random option from dropdown."""
        locator = self._get_locator(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        self.wait_for_visible(element=locator)
        skip = list(texts_to_skip) if texts_to_skip else []

        options = self.get_texts_from_dropdown(element=locator)
        option_to_select = get_random_value(options, *skip)

        self.select_option_by_text_from_dropdown(
            element=locator,
            text=option_to_select,
        )

    def get_texts_from_dropdown(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> list[str]:
        """Return list of texts from dropdown."""
        locator = self._get_locator(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        self.wait_for_visible(element=locator)

        texts = locator.first.locator("option").all_inner_texts()

        self._safe_log("Getting texts from '{}' -> '{}'", locator, str(texts))

        return texts

    def get_values_from_dropdown(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> list[str | None]:
        """Return list of values from dropdown."""
        locator = self._get_locator(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        self.wait_for_visible(element=locator)

        values = locator.first.locator("option").evaluate_all(
            "options => options.map(o => o.value)",
        )

        self._safe_log("Getting values from '{}' -> '{}'", locator, str(values))

        return values

    def open(self, url: str) -> None:
        """Alias for get()."""
        self.get(url)

    def get(self, url: str) -> None:
        """Open url."""
        self._page.goto(url)

    def execute_js(self, js_script: str, *args: Any) -> Any:  # noqa: ANN401
        """Execute javascript. Script body may use 'return' and 'arguments', Selenium-style."""
        resolved_args = [arg.element_handle() if isinstance(arg, Locator) else arg for arg in args]
        wrapped = f"(arguments) => {{ {js_script} }}"
        return self._frame.evaluate(wrapped, resolved_args)

    def find_element(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> Locator:
        """Return the first matching element, raise if none found."""
        locator = self._get_locator(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        if locator.count() == 0:
            msg = f"Didn't find any elements for selector - {element}"
            raise NoSuchElementException(msg)

        return locator.first

    def find_elements(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
        parent: TypeElement | None = None,
    ) -> list[Locator]:
        """Return all elements matching the locator."""
        locator = self._get_locator(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        return locator.all()

    def wait_for_text_is_changed(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        old_text: str | None = None,
        parent: TypeElement | None = None,
        msg: str | None = None,
        timeout: float | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Wait for text is changed."""
        if not timeout:
            timeout = self.__timeout
        if not msg:
            msg = f"{element} text was not changed for {timeout} seconds"

        self.wait_until(
            lambda _browser: (
                old_text
                != self.get_text(
                    element,
                    parent=parent,
                    by_id=by_id,
                    by_xpath=by_xpath,
                    by_link=by_link,
                    by_partial_link=by_partial_link,
                    by_name=by_name,
                    by_tag=by_tag,
                    by_css=by_css,
                    by_class=by_class,
                )
            ),
            msg,
            timeout,
        )

    def wait_for_attribute_is_changed(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        attr: str | None = None,
        old_value: str | None = None,
        parent: TypeElement | None = None,
        msg: str | None = None,
        timeout: float | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Wait for attribute is changed."""
        selector = self._get_selector(
            element=element,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        if not timeout:
            timeout = self.__timeout
        if not msg:
            msg = f"{self.to_string(selector)} attribute was not changed for {timeout} seconds"

        self.wait_until(
            lambda _browser: (
                old_value
                != self.get_attribute(
                    element=selector,
                    attr=attr,
                    parent=parent,
                    visible=False,
                )
            ),
            msg,
            timeout,
        )

    def wait_for_visible(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        msg: str | None = None,
        timeout: float | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Wait until element is visible."""
        selector = self._get_selector(
            element=element,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        locator = self._get_locator(element=selector, parent=parent)
        if not timeout:
            timeout = self.__timeout
        if not msg:
            msg = f"{selector} is not visible for {timeout} seconds"

        try:
            locator.first.wait_for(state="visible", timeout=timeout * 1000)
        except PlaywrightTimeoutError as exc:
            raise TimeoutException(msg) from exc

    def wait_for_not_visible(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        msg: str | None = None,
        timeout: float | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Wait until element not is visible."""
        selector = self._get_selector(
            element=element,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        locator = self._get_locator(element=selector, parent=parent)
        if not timeout:
            timeout = self.__timeout
        if not msg:
            msg = f"{selector} is visible for {timeout} seconds"

        try:
            locator.first.wait_for(state="hidden", timeout=timeout * 1000)
        except PlaywrightTimeoutError as exc:
            raise TimeoutException(msg) from exc

    def wait_for_present(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        msg: str | None = None,
        timeout: float | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Wait until element is present."""
        selector = self._get_selector(
            element=element,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        locator = self._get_locator(element=selector, parent=parent)
        if not timeout:
            timeout = self.__timeout
        if not msg:
            msg = f"{selector} is not present for {timeout} seconds"

        try:
            locator.first.wait_for(state="attached", timeout=timeout * 1000)
        except PlaywrightTimeoutError as exc:
            raise TimeoutException(msg) from exc

    def wait_for_not_present(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        msg: str | None = None,
        timeout: float | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Wait until element is not present."""
        selector = self._get_selector(
            element=element,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        locator = self._get_locator(element=selector, parent=parent)
        if not timeout:
            timeout = self.__timeout
        if not msg:
            msg = f"{selector} is present for {timeout} seconds"

        try:
            locator.first.wait_for(state="detached", timeout=timeout * 1000)
        except PlaywrightTimeoutError as exc:
            raise TimeoutException(msg) from exc

    def is_visible(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        parent: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> bool:
        """Return True if element is visible."""
        locator = self._get_locator(
            element=element,
            parent=parent,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        return locator.count() > 0 and locator.first.is_visible()

    def is_present(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> bool:
        """Return True if element is present."""
        locator = self._get_locator(
            element=element,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        return locator.count() > 0

    def get_elements_count(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> int:
        """Return number of elements."""
        locator = self._get_locator(
            element=element,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )
        return locator.count()

    def switch_to_frame(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Switch context to new frame."""
        locator = self.find_element(
            element=element,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )

        self._safe_log("Switching to '{}' frame", locator)

        handle = locator.element_handle()
        frame = handle.content_frame() if handle else None
        if frame is None:
            msg = f"Failed to switch to frame for selector - {element}"
            raise NoSuchElementException(msg)

        self._frame = frame

    def switch_to_new_window(  # noqa: PLR0913, PLR0917
        self,
        function: Callable[..., Any],
        element: TypeElement | None = None,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Switch context to new window."""
        with self._context.expect_page() as new_page_info:
            function(
                element=element,
                by_id=by_id,
                by_xpath=by_xpath,
                by_link=by_link,
                by_partial_link=by_partial_link,
                by_name=by_name,
                by_tag=by_tag,
                by_css=by_css,
                by_class=by_class,
            )

        new_page = new_page_info.value
        new_page.wait_for_load_state()

        self._page = new_page
        self._frame = new_page

        self._safe_log("Switching to '{}' window", new_page.title())

    def switch_to_default_content(self) -> None:
        """Switch to default content."""
        self._safe_log("Switching to default content")

        self._frame = self._page

    def close_current_window_and_focus_to_previous_one(self) -> None:
        """Close current window and switch to previous one."""
        pages = self._context.pages
        self.close()
        self._page = pages[-2]
        self._frame = self._page

    def get_page_source(self) -> str:
        """Return page source."""
        return self._frame.content()

    def get_title(self) -> str:
        """Return page title."""
        return self._page.title()

    def get_current_url(self) -> str:
        """Return current url."""
        return self._page.url

    def get_current_frame_url(self) -> str:
        """Return current frame url."""
        return self._frame.url

    def go_back(self) -> None:
        """Go back."""
        self._page.go_back()

    def delete_all_cookies(self) -> None:
        """Delete all cookies."""
        self._context.clear_cookies()

    def alert_accept(self) -> None:
        """Arm the next alert/confirm/prompt dialog to be accepted.

        Must be called before the action that triggers the dialog: Playwright
        resolves dialogs from a background dispatcher thread while the
        triggering call (e.g. execute_js/click) blocks the calling thread, so
        there is no opportunity to call this after the dialog is already open.
        """
        self._safe_log("Next dialog will be accepted")

        self.__pending_dialog_action = "accept"

    def alert_dismiss(self) -> None:
        """Arm the next alert/confirm/prompt dialog to be dismissed. See alert_accept()."""
        self._safe_log("Next dialog will be dismissed")

        self.__pending_dialog_action = "dismiss"

    def refresh_page(self) -> None:
        """Refresh page."""
        self._page.reload()

    def wait_until(
        self,
        function: Callable[[Browser], bool],
        msg: str | None = None,
        timeout: float | None = None,
    ) -> None:
        """Poll function until it returns a truthy value or timeout is reached."""
        if not timeout:
            timeout = self.__timeout

        deadline = time.monotonic() + timeout
        last_exc: Exception | None = None
        while time.monotonic() < deadline:
            try:
                if function(self):
                    return
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
            time.sleep(0.1)

        raise TimeoutException(msg or f"Condition was not met for {timeout} seconds") from last_exc

    def close(self) -> None:
        """Close the current window."""
        self._page.close()

    def quit(self) -> None:
        """Quit the browser and end the session."""
        self._context.close()
        self._browser.close()
        self.__playwright.stop()
