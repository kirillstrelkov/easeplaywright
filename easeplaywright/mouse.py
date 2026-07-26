"""Mouse."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Position

    from easeplaywright.browser import Browser, TypeElement


class Mouse:
    """Mouse."""

    def __init__(self, browser: Browser) -> None:
        """Initialize."""
        self.browser = browser

    def __center_offset(self, locator: Locator, xoffset: int, yoffset: int) -> Position:
        box = locator.bounding_box()
        if box is None:
            msg = f"Failed to get bounding box for {locator}"
            raise ValueError(msg)
        return {"x": box["width"] / 2 + xoffset, "y": box["height"] / 2 + yoffset}

    def left_click(  # noqa: PLR0913, PLR0917
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
        """Mouse left click."""
        self.left_click_by_offset(
            element,
            0,
            0,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )

    def left_click_by_offset(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        xoffset: int = 0,
        yoffset: int = 0,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Mouse left click with offset."""
        locator = self.browser._get_locator(  # noqa: SLF001
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
        self.browser.wait_for_visible(element=locator)
        locator = locator.first

        self.browser._safe_log(  # noqa: SLF001
            "Click at '{}' by offset({},{})",
            locator,
            xoffset,
            yoffset,
        )

        locator.click(position=self.__center_offset(locator, xoffset, yoffset))

    def hover(  # noqa: PLR0913, PLR0917
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
        *,
        force: bool = False,
    ) -> None:
        """Mouse hover."""
        self.hover_by_offset(
            element,
            0,
            0,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
            force=force,
        )

    def hover_by_offset(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        xoffset: int = 0,
        yoffset: int = 0,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
        *,
        force: bool = False,
    ) -> None:
        """Mouse hover with offset."""
        locator = self.browser._get_locator(  # noqa: SLF001
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
        self.browser.wait_for_visible(element=locator)
        locator = locator.first

        self.browser._safe_log(  # noqa: SLF001
            "Mouse over '{}' by offset({},{})",
            locator,
            xoffset,
            yoffset,
        )

        locator.hover(
            position=self.__center_offset(locator, xoffset, yoffset),
            force=force,
        )

    def right_click(  # noqa: PLR0913, PLR0917
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
        """Mouse right click."""
        self.right_click_by_offset(
            element,
            0,
            0,
            by_id=by_id,
            by_xpath=by_xpath,
            by_link=by_link,
            by_partial_link=by_partial_link,
            by_name=by_name,
            by_tag=by_tag,
            by_css=by_css,
            by_class=by_class,
        )

    def right_click_by_offset(  # noqa: PLR0913, PLR0917
        self,
        element: TypeElement | None = None,
        xoffset: int = 0,
        yoffset: int = 0,
        by_id: str | None = None,
        by_xpath: str | None = None,
        by_link: str | None = None,
        by_partial_link: str | None = None,
        by_name: str | None = None,
        by_tag: str | None = None,
        by_css: str | None = None,
        by_class: str | None = None,
    ) -> None:
        """Mouse right click with offset."""
        locator = self.browser._get_locator(  # noqa: SLF001
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
        self.browser.wait_for_visible(element=locator)
        locator = locator.first

        self.browser._safe_log(  # noqa: SLF001
            "Right click at '{}' by offset({},{})",
            locator,
            xoffset,
            yoffset,
        )

        locator.click(
            button="right",
            position=self.__center_offset(locator, xoffset, yoffset),
        )
